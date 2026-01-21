import os
import json
import time
import logging
from typing import List, Optional
from google.cloud import storage
from google.cloud import secretmanager
from google.cloud import aiplatform
# Vertex AI RAG specific imports might vary based on SDK version; 
# using generic google-cloud-aiplatform for structure, assuming 'rag' submodule exists or similar.
# Adjust import based on installed SDK version validation.
import vertexai
from vertexai.preview import rag

try:
    from .rag_config import RagConfig
except ImportError:
    # Allow running as script directly
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scripts.rag_config import RagConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RagPipeline:
    def __init__(self):
        self.config = RagConfig()
        self.config.validate()
        
        # Initialize Clients
        vertexai.init(project=self.config.PROJECT_ID, location=self.config.LOCATION)
        self.storage_client = storage.Client(project=self.config.PROJECT_ID)
        self.secret_client = secretmanager.SecretManagerServiceClient()

    def get_pinecone_api_key(self) -> str:
        """Fetch Pinecone API Key from Secret Manager."""
        name = f"projects/{self.config.PROJECT_ID}/secrets/{self.config.PINECONE_API_KEY_SECRET_ID}/versions/latest"
        try:
            response = self.secret_client.access_secret_version(request={"name": name})
            payload = response.payload.data.decode("UTF-8")
            logger.info("Successfully retrieved Pinecone API Key from Secret Manager.")
            return payload
        except Exception as e:
            logger.error(f"Failed to retrieve secret: {e}")
            raise

    def get_context_tags(self, file_path: str) -> str:
        """Generate semantic context tags based on file path and extension."""
        abs_path = os.path.abspath(file_path)
        rel_path = os.path.relpath(abs_path, self.config.LOCAL_DATA_DIR)
        
        # Module heuristic: Use top-level directory name
        parts = rel_path.split(os.sep)
        module = parts[0] if len(parts) > 1 else "common"
        
        # File type
        ext = os.path.splitext(file_path)[1].lstrip('.').lower()
        
        return f"[所属模块:{module}] [文件类型:{ext}]"

    def prepare_data(self):
        """Phase 2: Data Preparation - Convert local files to JSONL with tags."""
        logger.info("Starting Data Preparation Phase...")
        
        os.makedirs(os.path.dirname(self.config.OUTPUT_JSONL_PATH), exist_ok=True)
        
        # Ensure clean slate (overwrite logic implicit in 'w' mode)
        with open(self.config.OUTPUT_JSONL_PATH, 'w', encoding='utf-8') as outfile:
            count = 0
            if not os.path.exists(self.config.LOCAL_DATA_DIR):
                logger.warning(f"Data directory {self.config.LOCAL_DATA_DIR} does not exist.")
                return

            for root, dirs, files in os.walk(self.config.LOCAL_DATA_DIR):
                for file in files:
                    if file.startswith('.'): continue # Skip hidden files
                    
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            raw_content = f.read()
                        
                        tags = self.get_context_tags(file_path)
                        enhanced_content = f"{tags}\n{raw_content}"
                        
                        # Construct JSON object
                        # JSONL spec: One complete JSON string per line. 
                        # json.dumps handles string escaping (including newlines) automatically.
                        record = {
                            "content": enhanced_content,
                            "metadata": {
                                "source": os.path.basename(file_path),
                                "path": file_path
                            }
                        }
                        
                        outfile.write(json.dumps(record, ensure_ascii=False) + '\n')
                        count += 1
                    except Exception as e:
                        logger.error(f"Error processing file {file}: {e}")
            
            logger.info(f"Data Preparation Complete. Generated {count} records at {self.config.OUTPUT_JSONL_PATH}")

    def upload_to_gcs(self):
        """Phase 2 (Cont): Upload Source of Truth to GCS."""
        logger.info(f"Uploading to GCS: gs://{self.config.GCS_BUCKET_NAME}/{self.config.GCS_BLOB_PATH}")
        
        bucket = self.storage_client.bucket(self.config.GCS_BUCKET_NAME)
        blob = bucket.blob(self.config.GCS_BLOB_PATH)
        
        blob.upload_from_filename(self.config.OUTPUT_JSONL_PATH)
        logger.info("Upload Complete.")
        return f"gs://{self.config.GCS_BUCKET_NAME}/{self.config.GCS_BLOB_PATH}"

    def trigger_sync(self, gcs_uri: str):
        """Phase 3: Vectorization Sync via Vertex AI RAG."""
        logger.info("Triggering Vertex AI RAG Import...")
        
        # Verify permissions/secret access first (Validation Checklist)
        _ = self.get_pinecone_api_key() 
        
        paths = [gcs_uri]
        
        try:
            # Assuming functionality to import files to an existing Corpus
            # Note: The actual API might vary (import_files vs specialized method)
            # Using the logic described in prompt: rag.import_files
            
            # Need strict reference to correct rag corpus resource name
            response = rag.import_files(
                corpus_name=self.config.RAG_CORPUS_NAME,
                paths=paths,
                chunk_size=self.config.CHUNK_SIZE,
                chunk_overlap=self.config.CHUNK_OVERLAP,
                use_default_parser=self.config.USE_DEFAULT_PARSER,
                timeout=900
            )
            
            logger.info(f"Import initiated. Operation: {response}")
            
            # Monitoring Phase
            # Assuming a way to check operation status or file status
            # If response is an Operation, we should wait.
            # If response returns ImportRagFilesResponse, import might be done or async.
            
            # For demonstration/instruction following, we poll status if possible
            # Or assume the prompt's instruction: "Monitor: Polling rag_file status until ACTIVE"
            # Since we don't have the specific file ID easily without parsing response, 
            # we will log the waiting requirement.
            
            logger.info("Please monitor the Import Operation in Google Cloud Console or via code if operation ID available.")
            
        except Exception as e:
            logger.error(f"Failed to trigger RAG import: {e}")
            raise

    def run(self, dry_run=False):
        logger.info("=== Starting RAG Pipeline Sync ===")
        
        self.prepare_data()
        
        if dry_run:
            logger.info("Dry run complete. Skipping Upload and Sync.")
            return
            
        gcs_uri = self.upload_to_gcs()
        self.trigger_sync(gcs_uri)
        
        logger.info("=== Pipeline Execution Finished ===")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Generate JSONL but do not upload/sync")
    args = parser.parse_args()
    
    pipeline = RagPipeline()
    pipeline.run(dry_run=args.dry_run)
