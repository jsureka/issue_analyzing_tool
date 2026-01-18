
import logging
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_jina_embedding():
    model_name = "jinaai/jina-embeddings-v2-base-code"
    logger.info(f"Loading model: {model_name}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")
    model.to(device)
    model.eval()
    
    # Create a dummy batch with varying lengths
    texts = [
        "def hello_world():\n    print('Hello')",
        "class MyClass:\n    def __init__(self):\n        pass",
        "x = 1" * 500, # Long text
        "short"
    ]
    
    # Replicate to make a larger batch
    texts = texts * 8 # 32 items
    
    logger.info(f"Batch size: {len(texts)}")
    
    try:
        # Simulate embed_batch logic
        inputs = tokenizer(
            texts,
            max_length=8192,
            padding=True, # Dynamic padding
            truncation=True,
            return_tensors='pt'
        )
        
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        logger.info(f"Input Keys: {inputs.keys()}")
        logger.info(f"Input IDs shape: {inputs['input_ids'].shape}")
        logger.info(f"Attention Mask shape: {inputs['attention_mask'].shape}")
        
        with torch.no_grad():
            outputs = model(**inputs)
            
            logger.info(f"Output type: {type(outputs)}")
            logger.info(f"Output keys: {outputs.keys() if hasattr(outputs, 'keys') else 'No keys'}")
            
            last_hidden_state = outputs.last_hidden_state
            logger.info(f"Last Hidden State shape: {last_hidden_state.shape}")
            
            attention_mask = inputs['attention_mask']
            
            # Check expansion logic
            logger.info("Attempting expansion...")
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
            logger.info(f"Expanded Mask shape: {input_mask_expanded.shape}")
            
            sum_embeddings = torch.sum(last_hidden_state * input_mask_expanded, 1)
            sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
            embeddings = (sum_embeddings / sum_mask).cpu().numpy()
            
            logger.info("Embedding successful")
            logger.info(f"Embeddings shape: {embeddings.shape}")
            
    except Exception as e:
        logger.error(f"Error during embedding: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_jina_embedding()
