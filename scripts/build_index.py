import os
import json
import hashlib
import logging
import shutil
from datetime import datetime
from dotenv import load_dotenv

# LlamaIndex Imports
from llama_index.core import VectorStoreIndex, Settings, StorageContext, Document, load_index_from_storage
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.gemini import GeminiEmbedding
import httpx
from typing import Any, List, Optional

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

def calculate_file_hash(file_path: str) -> str:
    """Calculates SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def granular_load_documents(file_path: str) -> List[Document]:
    """
    Parses JSONL into individual Documents. 
    Uses content hash as doc_id to enable stable incremental updates.
    """
    documents = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            text = line
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    text = data.get("text") or data.get("content") or json.dumps(data, ensure_ascii=False)
            except:
                pass
            
            doc_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
            doc = Document(text=text, id_=doc_hash)
            documents.append(doc)
    return documents

def build_index(mode: str = "auto", force: bool = False):
    """
    Builds/Updates the vector index.
    """
    RagConfig.validate()
    
    source_path = os.path.join(RagConfig.LOCAL_DATA_DIR, RagConfig.SOURCE_FILENAME)
    if not os.path.exists(source_path):
        logger.error(f"Source file not found: {source_path}")
        return

    manifest_path = os.path.join(RagConfig.STORAGE_DIR, RagConfig.MANIFEST_FILE)
    current_hash = calculate_file_hash(source_path)
    current_model = RagConfig.EMBEDDING_MODEL
    
    storage_exists = os.path.exists(RagConfig.STORAGE_DIR)
    manifest_exists = os.path.exists(manifest_path)
    
    meta = {}
    if manifest_exists:
        try:
            with open(manifest_path, 'r') as f:
                meta = json.load(f)
        except: 
            pass

    cached_hash = meta.get("file_hash")
    cached_model = meta.get("embedding_model")
    
    # Logic Decision
    if force:
        logger.info("⚠️ Force flag set. Triggering FULL rebuild.")
        strategy = "full"
    elif mode == "full":
        strategy = "full"
    else:
        # Incremental Mode (Default)
        # Strict Pre-checks
        if not storage_exists or not manifest_exists:
            logger.error("🛑 Incremental update failed: No valid index found. Please run with '--mode full' to initialize.")
            return

        if cached_model != current_model:
            logger.error(f"� Incremental update failed: Embedding model mismatch ({cached_model} != {current_model}). Please run with '--mode full'.")
            return

        if cached_hash == current_hash:
            logger.info("✅ Source content identical (Hash match). No changes needed.")
            return
            
        strategy = "incremental"

    logger.info(f"=== Starting Build (Strategy: {strategy.upper()}) ===")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")
    
    Settings.llm = Gemini(model="models/gemini-2.0-flash-exp", api_key=api_key)
    Settings.embed_model = GeminiEmbedding(
        model_name=current_model, 
        api_key=api_key,
        output_dimensionality=768 # Default for build
    )

    logger.info(f"Loading/Parsing data from: {source_path}")
    documents = granular_load_documents(source_path)
    logger.info(f"Loaded {len(documents)} documents.")

    index = None
    
    if strategy == "full":
        if os.path.exists(RagConfig.STORAGE_DIR):
            shutil.rmtree(RagConfig.STORAGE_DIR)
        os.makedirs(RagConfig.STORAGE_DIR, exist_ok=True)
        
        logger.info("Building fresh VectorStoreIndex...")
        index = VectorStoreIndex.from_documents(documents)
        
    elif strategy == "incremental":
        try:
            logger.info(f"Loading existing index from: {RagConfig.STORAGE_DIR}")
            storage_context = StorageContext.from_defaults(persist_dir=RagConfig.STORAGE_DIR)
            index = load_index_from_storage(storage_context)
            
            logger.info("Refreshing index (Incremental Update)...")
            result = index.refresh(documents) 
            changes = sum(result)
            logger.info(f"Incremental update applied. {changes} documents updated/added.")
            
        except Exception as e:
            logger.error(f"Incremental update failed ({e}). Falling back to FULL rebuild.")
            if os.path.exists(RagConfig.STORAGE_DIR):
                shutil.rmtree(RagConfig.STORAGE_DIR)
            os.makedirs(RagConfig.STORAGE_DIR, exist_ok=True)
            index = VectorStoreIndex.from_documents(documents)

    logger.info(f"Persisting index to: {RagConfig.STORAGE_DIR}")
    index.storage_context.persist(persist_dir=RagConfig.STORAGE_DIR)

    manifest = {
        "source_file": RagConfig.SOURCE_FILENAME,
        "file_hash": current_hash,
        "build_time": datetime.now().isoformat(),
        "embedding_model": current_model,
        "strategy": strategy
    }
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    logger.info("✅ Build Complete.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build/Update RAG Index")
    parser.add_argument("--mode", choices=["incremental", "full"], default="incremental", 
                      help="Build mode: incremental (default, updates only changed docs), full (wipe & rebuild)")
    parser.add_argument("--force", "-f", action="store_true", help="Force rebuild (equivalent to --mode full)")
    args = parser.parse_args()
    
    build_index(mode=args.mode, force=args.force)
