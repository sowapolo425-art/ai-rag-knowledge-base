import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    max_upload_mb: int = 15
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    chat_model: str = ""
    embedding_model: str = ""
    local_embedding_model: str = ""
    demo_readonly: bool = False
    max_documents: int = 20
    ask_rate_per_minute: int = 6

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("DATA_DIR", "data")),
            max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "15")),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            chat_model=os.getenv("OPENAI_CHAT_MODEL", ""),
            embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", ""),
            local_embedding_model=os.getenv("LOCAL_EMBEDDING_MODEL", ""),
            demo_readonly=os.getenv("DEMO_READONLY", "0") == "1",
            max_documents=int(os.getenv("MAX_DOCUMENTS", "20")),
            ask_rate_per_minute=int(os.getenv("ASK_RATE_PER_MINUTE", "6")),
        )
