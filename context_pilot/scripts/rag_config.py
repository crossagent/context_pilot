import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class RagConfig:
    # Local Data Config
    LOCAL_DATA_DIR = os.getenv("RAG_DATA_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data")))
    
    # Storage Config (Persistent Index)
    # Using adk_data/rag_storage to keep it separate from raw data
    STORAGE_DIR = os.getenv("RAG_STORAGE_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../adk_data/rag_storage")))
    
    # Manifest File (scheme C versioning)
    MANIFEST_FILE = "index_meta.json"
    SOURCE_FILENAME = os.getenv("RAG_SOURCE_FILENAME", "knowledge_base.jsonl")
    DB_FILENAME = "knowledge_base.sqlite"
    
    @property
    def DB_PATH(self):
        return os.path.join(self.LOCAL_DATA_DIR, self.DB_FILENAME)
    
    # Model Config
    EMBEDDING_MODEL = "models/gemini-embedding-001"
    
    @staticmethod
    def validate():
        if not os.path.exists(RagConfig.LOCAL_DATA_DIR):
            print(f"Warning: Data directory not found: {RagConfig.LOCAL_DATA_DIR}")
