import sys
import os
import logging
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from Feature_Components.KnowledgeBase.embedder import CodeEmbedder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_jina_upgrade():
    print("1. Initializing CodeEmbedder with Jina V2...")
    try:
        embedder = CodeEmbedder(model_name="jinaai/jina-embeddings-v2-base-code")
        print("   Success: Embedder initialized.")
    except Exception as e:
        print(f"   FAILED: {e}")
        return False

    print("\n2. Loading Model (this may take time/download)...")
    try:
        embedder.load_model()
        print(f"   Success: Model loaded on {embedder.device}")
    except Exception as e:
        print(f"   FAILED: {e}")
        return False

    print("\n3. Testing Long Context Embedding (6000 chars)...")
    long_text = "def long_function():\n" + "    print('padding')\n" * 300
    print(f"   Text length: {len(long_text)} characters")
    
    try:
        embedding = embedder.embed_function("def long_function():", None, long_text)
        print(f"   Success: Embedding generated with shape {embedding.shape}")
        
        if embedding.shape != (768,):
             print(f"   FAILED: Expected shape (768,), got {embedding.shape}")
             return False
             
        # Check for zero vector
        if np.all(embedding == 0):
             print("   FAILED: Embedding is all zeros (error fallback triggered)")
             return False
             
    except Exception as e:
        print(f"   FAILED: {e}")
        return False

    print("\n4. Testing Batch Embedding...")
    try:
        batch = [long_text, "def short(): pass"]
        embeddings = embedder.embed_batch(batch)
        print(f"   Success: Batch embeddings shape {embeddings.shape}")
    except Exception as e:
         print(f"   FAILED: {e}")
         return False

    print("\n✅ VERIFICATION PASSED: Jina Embeddings V2 is working correctly.")
    return True

if __name__ == "__main__":
    success = verify_jina_upgrade()
    sys.exit(0 if success else 1)
