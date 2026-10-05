from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .answering import answer
from .config import Settings
from .parsing import ParseError, extract_sections, split_sections
from .store import Store


class HistoryMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=1000)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=6)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = Store(settings)
    app = FastAPI(title="企业知识库 A", version="1.0.0")
    app.state.store = store

    @app.get("/")
    def home():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    @app.get("/api/status")
    def status():
        return {"embedding_mode": store.embedder.mode, "answer_mode": "llm" if settings.api_key and settings.chat_model else "offline", "document_count": len(store.list_documents())}

    @app.get("/api/documents")
    def documents():
        return store.list_documents()

    @app.post("/api/documents", status_code=201)
    async def upload(file: UploadFile = File(...)):
        filename = Path(file.filename or "").name
        suffix = Path(filename).suffix.lower()
        if suffix not in {".pdf", ".docx", ".txt"}:
            raise HTTPException(415, "仅支持 PDF、DOCX 和 TXT 文件。")
        content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
        if len(content) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"文件不得超过 {settings.max_upload_mb} MB。")
        try:
            chunks = split_sections(extract_sections(filename, content))
            if not chunks:
                raise ParseError("文档没有可提取的文字。扫描版 PDF 请先做 OCR。")
            return store.add_document(filename, content, chunks)
        except ParseError as exc:
            raise HTTPException(422, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.delete("/api/documents/{doc_id}")
    def delete(doc_id: str):
        if not store.delete_document(doc_id):
            raise HTTPException(404, "文档不存在。")
        return {"deleted": True}

    @app.post("/api/ask")
    def ask(request: AskRequest):
        recent_questions = [item.content for item in request.history if item.role == "user"][-2:]
        hits = store.search(" ".join([*recent_questions, request.question]))
        try:
            response = answer(request.question, hits, settings, request.history)
        except Exception as exc:
            raise HTTPException(502, "模型服务暂时不可用，请检查 API 配置。") from exc
        sources = [{"number": i, "document_id": hit["doc_id"], "filename": hit["filename"], "locator": hit["locator"], "excerpt": hit["text"], "score": hit["score"]} for i, hit in enumerate(hits, 1)]
        return {"answer": response, "sources": sources, "mode": "llm" if settings.api_key and settings.chat_model else "offline"}

    return app
