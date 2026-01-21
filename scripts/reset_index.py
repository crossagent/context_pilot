import os
import time
from pinecone import Pinecone
from dotenv import load_dotenv
from google.cloud import secretmanager

# Load Env
load_dotenv()
from rag_config import RagConfig  # Local import

def get_pinecone_api_key(project_id, secret_id):
    """Retrieves Pinecone API Key from Google Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

import argparse

def reset_index():
    parser = argparse.ArgumentParser(description="Reset Pinecone Index")
    parser.add_argument("-y", "--force", action="store_true", help="Skip confirmation")
    args = parser.parse_args()

    config = RagConfig()
    
    print(f"=== Pinecone Index Reset Tool ===")
    print(f"Target Index: {config.PINECONE_INDEX_NAME}")
    print(f"Environment:  {config.PINECONE_ENV}")
    
    if not args.force:
        confirm = input("⚠️  WARNING: This will DELETE ALL VECTORS in the index. Are you sure? (y/n): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return

    try:
        # Get Key
        if os.getenv("PINECONE_API_KEY"):
            api_key = os.getenv("PINECONE_API_KEY")
        else:
            print("Fetching API Key from Secret Manager...")
            api_key = get_pinecone_api_key(config.PROJECT_ID, config.PINECONE_API_KEY_SECRET_ID)
        
        # Init
        pc = Pinecone(api_key=api_key)
        index = pc.Index(config.PINECONE_INDEX_NAME)
        
        # Delete
        print("Deleting all vectors...")
        index.delete(delete_all=True)
        print("✅ Index cleared successfully.")
        
        # Verify
        time.sleep(2) # Give it a moment
        stats = index.describe_index_stats()
        print(f"Current Vector Count: {stats.total_vector_count}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    reset_index()
