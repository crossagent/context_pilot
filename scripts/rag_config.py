import os
from dataclasses import dataclass

@dataclass
class RagConfig:
    # Google Cloud Project Config
    PROJECT_ID = os.getenv("GCP_PROJECT_ID", "your-project-id")
    LOCATION = os.getenv("GCP_REGION", "us-central1")
    
    # GCS Config
    GCS_BUCKET_NAME = os.getenv("RAG_GCS_BUCKET", "your-rag-bucket")
    GCS_BLOB_PATH = "rag_data/knowledge_base.jsonl"
    
    # Secret Manager
    PINECONE_API_KEY_SECRET_ID = "pinecone-api-key"
    
    # Pinecone Config
    PINECONE_ENV = os.getenv("PINECONE_ENV", "gcp-starter")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX", "rag-index")
    PINECONE_DIMENSION = 768
    
    # Vertex AI RAG Config
    # If using an existing Corpus
    RAG_CORPUS_NAME = os.getenv("RAG_CORPUS_NAME", "projects/{project}/locations/{location}/ragCorpora/{corpus_id}")
    
    # Chunking Config (Critical)
    CHUNK_SIZE = 10240000  # Avoid physical chunking
    CHUNK_OVERLAP = 0
    USE_DEFAULT_PARSER = True
    
    # Local Data Config
    LOCAL_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../adk_data"))
    OUTPUT_JSONL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../temp/knowledge_base.jsonl"))

    @staticmethod
    def validate():
        if RagConfig.PROJECT_ID == "your-project-id":
            print("Warning: GCP_PROJECT_ID is not set.")
