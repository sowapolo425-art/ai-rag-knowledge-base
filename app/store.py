import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from qdrant_client import QdrantClient, models

from .config import Settings
from .embeddings import Embedder


class Store:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.data_dir = settings.data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "uploads").mkdir(exist_ok=True)
        self.db_path = self.data_dir / "documents.sqlite3"
        self.qdrant = QdrantClient(path=str(self.data_dir / "qdrant"))
        self.embedder = Embedder(settings)
        identity = f"{self.embedder.mode}:{settings.embedding_model if self.embedder.mode == 'api' else 'char-ngram-v1'}:{settings.base_url if self.embedder.mode == 'api' else ''}"
        self.collection = "chunks_" + hashlib.sha256(identity.encode()).hexdigest()[:16]
        self._init_db()

    def _connect(self):
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        return db

    def _init_db(self):
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, filename TEXT NOT NULL, file_type TEXT NOT NULL,
                sha256 TEXT NOT NULL, chunk_count INTEGER NOT NULL,
                collection_name TEXT NOT NULL, created_at TEXT NOT NULL
            )""")

    def list_documents(self):
        with self._connect() as db:
            rows = db.execute("SELECT id, filename, file_type, sha256, chunk_count, created_at FROM documents WHERE collection_name=? ORDER BY created_at DESC", (self.collection,)).fetchall()
        return [dict(row) for row in rows]

    def add_document(self, filename: str, content: bytes, chunks: list[tuple[str, str]]):
        doc_id = str(uuid4())
        vectors = self.embedder.encode([text for _, text in chunks])
        size = len(vectors[0])
        if not self.qdrant.collection_exists(self.collection):
            self.qdrant.create_collection(self.collection, vectors_config=models.VectorParams(size=size, distance=models.Distance.COSINE))
        elif self.qdrant.get_collection(self.collection).config.params.vectors.size != size:
            raise ValueError("向量维度与现有索引不一致，请使用相同的 Embedding 模型。")
        suffix = "." + filename.rsplit(".", 1)[-1].lower()
        saved = self.data_dir / "uploads" / f"{doc_id}{suffix}"
        saved.write_bytes(content)
        points = [models.PointStruct(id=str(uuid4()), vector=vector, payload={"doc_id": doc_id, "filename": filename, "locator": locator, "text": text}) for (locator, text), vector in zip(chunks, vectors)]
        try:
            self.qdrant.upsert(self.collection, points=points, wait=True)
            with self._connect() as db:
                db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)", (
                    doc_id, filename, suffix[1:], hashlib.sha256(content).hexdigest(), len(chunks), self.collection,
                    datetime.now(timezone.utc).isoformat(),
                ))
        except Exception:
            self.qdrant.delete(self.collection, points_selector=models.FilterSelector(filter=models.Filter(must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))])))
            saved.unlink(missing_ok=True)
            raise
        return {"id": doc_id, "filename": filename, "file_type": suffix[1:], "chunk_count": len(chunks)}

    def delete_document(self, doc_id: str) -> bool:
        with self._connect() as db:
            row = db.execute("SELECT file_type FROM documents WHERE id=? AND collection_name=?", (doc_id, self.collection)).fetchone()
            if not row:
                return False
            self.qdrant.delete(self.collection, points_selector=models.FilterSelector(filter=models.Filter(must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))])), wait=True)
            db.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        (self.data_dir / "uploads" / f"{doc_id}.{row['file_type']}").unlink(missing_ok=True)
        return True

    def search(self, question: str, limit: int = 5):
        if not self.qdrant.collection_exists(self.collection):
            return []
        vector = self.embedder.encode([question])[0]
        hits = self.qdrant.query_points(self.collection, query=vector, limit=limit, with_payload=True).points
        return [{"score": round(hit.score, 4), **hit.payload} for hit in hits if hit.score >= 0.08]
