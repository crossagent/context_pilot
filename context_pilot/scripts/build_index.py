import os
import json
import logging
import shutil
from datetime import datetime
from dotenv import load_dotenv

# LlamaIndex Imports
from llama_index.core import VectorStoreIndex, Settings, StorageContext, Document, load_index_from_storage
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.gemini import GeminiEmbedding

# Load configuration
try:
    from .rag_config import RagConfig
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from rag_config import RagConfig

# Import DB Manager
try:
    from context_pilot.utils.db_manager import default_db_manager
except ImportError:
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
    from context_pilot.utils.db_manager import default_db_manager

# Load Env
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reconstruct_markdown(row) -> str:
    """Reconstructs the markdown content from DB columns."""
    return f"""# Intent
{row['intent']}

# 1. Problem Context
{row['problem_context']}

# 2. Root Cause Analysis
{row['root_cause']}

# 3. Solution / SOP
{row['solution_steps']}

# 4. Evidence
{row['evidence']}
"""

def load_documents_from_db() -> list[Document]:
    """Loads all entries from SQLite and converts them to LlamaIndex Documents."""
    documents = []
    
    # Ensure DB exists/is initialized before reading
    default_db_manager.init_db()
    
    try:
        with default_db_manager.get_connection() as conn:
            rows = conn.execute("SELECT * FROM knowledge_entries").fetchall()
            
            for row in rows:
                text = reconstruct_markdown(row)
                
                # Construct metadata
                tags = [t.strip() for t in (row['tags'] or "").split(",") if t.strip()]
                metadata = {
                    "tags": tags,
                    "contributor": row['contributor'],
                    "timestamp": row['created_at'],
                    "type": "cookbook_record",
                    "intent": row['intent']
                }
                
                # Create Document with explicit ID from DB
                doc = Document(
                    text=text, 
                    id_=row['id'], 
                    metadata=metadata
                )
                documents.append(doc)
    except Exception as e:
        logger.error(f"Failed to load documents from DB: {e}")
        
    return documents

def build_index(mode: str = "auto", force: bool = False):
    """
    Builds/Updates the vector index from SQLite DB.
    """
    RagConfig.validate()
    
    # DB path check is handled by db_manager or implicit in load
    
    manifest_path = os.path.join(RagConfig.STORAGE_DIR, RagConfig.MANIFEST_FILE)
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

    cached_model = meta.get("embedding_model")
    
    # Logic Decision
    if force:
        logger.info("⚠️ Force flag set. Triggering FULL rebuild.")
        strategy = "full"
    elif mode == "full":
        strategy = "full"
    else:
        # Incremental Mode (Default)
        if not storage_exists:
            logger.info("No existing index found. Switching to FULL build.")
            strategy = "full"
        elif cached_model != current_model:
            logger.warning(f"Embedding model changed ({cached_model} -> {current_model}). Triggering FULL rebuild.")
            strategy = "full"
        else:
            strategy = "incremental"

    logger.info(f"=== Starting Build (Strategy: {strategy.upper()}) ===")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")
    
    Settings.llm = Gemini(model="models/gemini-3-flash-preview", api_key=api_key)
    Settings.embed_model = GeminiEmbedding(
        model_name=current_model, 
        api_key=api_key
    )

    logger.info(f"Loading data from SQLite DB: {RagConfig.DB_PATH}")
    documents = load_documents_from_db()
    logger.info(f"Loaded {len(documents)} documents.")
    
    if not documents and strategy == "full":
        logger.warning("No documents found in DB. Nothing to build.")
        return

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
            # refresh() updates docs with matching IDs if hash is different, and adds new docs
            result = index.refresh(documents) 
            changes = sum(result)
            logger.info(f"Incremental update applied. {changes} documents updated/added.")
            
        except Exception as e:
            logger.error(f"Incremental update failed ({e}). Falling back to FULL rebuild.")
            if os.path.exists(RagConfig.STORAGE_DIR):
                shutil.rmtree(RagConfig.STORAGE_DIR)
            os.makedirs(RagConfig.STORAGE_DIR, exist_ok=True)
            index = VectorStoreIndex.from_documents(documents)

    if index:
        logger.info(f"Persisting index to: {RagConfig.STORAGE_DIR}")
        index.storage_context.persist(persist_dir=RagConfig.STORAGE_DIR)

        manifest = {
            "source": "sqlite",
            "build_time": datetime.now().isoformat(),
            "embedding_model": current_model,
            "strategy": strategy,
            "doc_count": len(documents)
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
    
    logger.info("✅ Build Complete.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build/Update RAG Index form SQLite")
    parser.add_argument("--mode", choices=["incremental", "full"], default="incremental", 
                      help="Build mode: incremental (default), full (wipe & rebuild)")
    parser.add_argument("--force", "-f", action="store_true", help="Force rebuild")
    args = parser.parse_args()
    
    build_index(mode=args.mode, force=args.force)
