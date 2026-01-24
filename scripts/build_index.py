import os
import json
import hashlib
import logging
import shutil
from datetime import datetime
from dotenv import load_dotenv

# LlamaIndex Imports
from llama_index.core import VectorStoreIndex, Settings, StorageContext
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.llms.gemini import Gemini
from llama_index.core.base.embeddings.base import BaseEmbedding
import httpx
from typing import Any, List

# Load configuration
try:
    from rag_config import RagConfig
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from rag_config import RagConfig

# Load Env
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Reusing GeminiRawEmbedding to avoid dependency duplication ---
# (Ideally this class would be in a shared lib, but for now reproducing it here to keep script standalone)
class GeminiRawEmbedding(BaseEmbedding):
    api_key: str
    model_name: str = "models/embedding-001"

    def __init__(self, api_key: str, model_name: str = "models/embedding-001", **kwargs: Any):
        super().__init__(model_name=model_name, api_key=api_key, **kwargs)

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._embed(query)

    def _get_text_embedding(self, text: str) -> List[float]:
        return self._embed(text)

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._embed(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._embed(text)

    def _embed(self, text: str) -> List[float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/{self.model_name}:embedContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model_name,
            "content": {"parts": [{"text": text}]}
        }
        try:
            with httpx.Client() as client:
                response = client.post(url, json=payload, headers=headers, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                return data["embedding"]["values"]
        except Exception as e:
            logger.error(f"Gemini API Embedding failed: {e}")
            raise

def calculate_file_hash(file_path: str) -> str:
    """Calculates SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def build_index(force_rebuild: bool = False):
    """
    Builds the vector index if source data has changed.
    Scheme C: Checks index_meta.json for versioning.
    """
    RagConfig.validate()
    
    source_path = os.path.join(RagConfig.LOCAL_DATA_DIR, RagConfig.SOURCE_FILENAME)
    if not os.path.exists(source_path):
        logger.error(f"Source file not found: {source_path}")
        return

    # 1. Check Version (Manifest)
    current_hash = calculate_file_hash(source_path)
    manifest_path = os.path.join(RagConfig.STORAGE_DIR, RagConfig.MANIFEST_FILE)
    
    should_build = force_rebuild
    
    if not should_build and os.path.exists(manifest_path) and os.path.exists(RagConfig.STORAGE_DIR):
        try:
            with open(manifest_path, 'r') as f:
                meta = json.load(f)
                cached_hash = meta.get("file_hash")
                if cached_hash == current_hash:
                    logger.info("✅ Index is up-to-date (Hash match). Skipping rebuild.")
                    return
                else:
                    logger.info(f"🔄 Source changed (Hash mismatch). Rebuilding...")
                    should_build = True
        except Exception as e:
            logger.warning(f"Failed to read manifest, performing rebuild: {e}")
            should_build = True
    elif not os.path.exists(RagConfig.STORAGE_DIR):
        logger.info("🆕 No index found. Building fresh index...")
        should_build = True

    if not should_build:
         logger.info("Index check passed.")
         return

    # 2. Build Pipeline
    logger.info("=== Starting Index Build ===")
    
    # Clean previous storage to avoid corruption/ghost files
    if os.path.exists(RagConfig.STORAGE_DIR):
        logger.info(f"Cleaning old storage: {RagConfig.STORAGE_DIR}")
        shutil.rmtree(RagConfig.STORAGE_DIR)
    os.makedirs(RagConfig.STORAGE_DIR, exist_ok=True)

    # Setup Settings (Embedding & LLM)
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")

    Settings.llm = Gemini(model="models/gemini-2.0-flash-exp", api_key=api_key)
    Settings.embed_model = GeminiRawEmbedding(api_key=api_key)

    # Load Data
    logger.info(f"Loading data from: {source_path}")
    documents = SimpleDirectoryReader(input_files=[source_path]).load_data()
    logger.info(f"Loaded {len(documents)} documents.")

    # Vectorize & Index
    logger.info("Vectorizing content...")
    index = VectorStoreIndex.from_documents(documents)

    # Persist
    logger.info(f"Persisting index to: {RagConfig.STORAGE_DIR}")
    index.storage_context.persist(persist_dir=RagConfig.STORAGE_DIR)

    # Write Manifest
    manifest = {
        "source_file": RagConfig.SOURCE_FILENAME,
        "file_hash": current_hash,
        "build_time": datetime.now().isoformat(),
        "embedding_model": RagConfig.EMBEDDING_MODEL
    }
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    logger.info("✅ Build Complete. Manifest updated.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build/Update RAG Index")
    parser.add_argument("--force", "-f", action="store_true", help="Force rebuild ignoring version check")
    args = parser.parse_args()
    
    build_index(force_rebuild=args.force)
