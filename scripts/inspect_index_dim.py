
import os
import sys
import logging
from llama_index.core import StorageContext, load_index_from_storage

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Add project root to path (for rag_config import if needed)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from scripts.rag_config import RagConfig
except ImportError:
    print("Could not import RagConfig. Make sure you run this from project root.")
    sys.exit(1)

def inspect_index():
    storage_dir = RagConfig.STORAGE_DIR
    logger.info(f"Inspecting Index at: {storage_dir}")
    
    if not os.path.exists(storage_dir):
        logger.error("Storage directory does not exist.")
        return

    try:
        storage_context = StorageContext.from_defaults(persist_dir=storage_dir)
        index = load_index_from_storage(storage_context)
        
        # Access the vector store
        vector_store = index.vector_store
        # VectorStore usually has a mapping or data dict
        # Specific implementation depends on default SimpleVectorStore
        
        # Try to peak at data
        if hasattr(vector_store, "to_dict"):
            data = vector_store.to_dict()
            if "embedding_dict" in data:
                embeddings = data["embedding_dict"]
                count = len(embeddings)
                logger.info(f"Total Vectors: {count}")
                
                if count > 0:
                    first_key = next(iter(embeddings))
                    first_vec = embeddings[first_key]
                    dim = len(first_vec)
                    logger.info(f"Vector Dimension: {dim}")
                    
                    if dim == 768:
                        logger.info("✅ Dimension matches configuration (768).")
                    elif dim == 3072:
                         logger.error("❌ Dimension mismatch! Found 3072 (likely text-embedding-004 or similar).")
                    else:
                         logger.warning(f"⚠️ Unexpected dimension: {dim}")
            else:
                logger.info("Vector store empty or no 'embedding_dict' found.")
        else:
            logger.info("Vector store format unknown (not simple dict).")

    except Exception as e:
        logger.error(f"Failed to load/inspect index: {e}")

if __name__ == "__main__":
    inspect_index()
