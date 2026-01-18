"""
Code embedding generation using pre-trained models
Supports UniXcoder and GraphCodeBERT for code and text embeddings
"""

import logging
import torch
import numpy as np
from typing import List, Optional
from transformers import AutoTokenizer, AutoModel

logger = logging.getLogger(__name__)


class CodeEmbedder:
    """Wrapper for code embedding models"""
    
    # Model cache to avoid reloading
    _model_cache = {}
    _tokenizer_cache = {}
    
    def __init__(self, model_name: str = "jinaai/jina-embeddings-v2-base-code"):
        """
        Initialize the code embedder
        
        Args:
            model_name: HuggingFace model name (default: jina-embeddings-v2-base-code)
        """
        self.model_name = model_name
        self.device = self._get_device()
        self.model = None
        self.tokenizer = None
        
        logger.info(f"CodeEmbedder initialized with model: {model_name}")
        logger.info(f"Using device: {self.device}")
    
    def _get_device(self) -> str:
        """Detect and return the best available device"""
        if torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"
    
    def load_model(self) -> None:
        """
        Load the embedding model and tokenizer
        Uses caching to avoid reloading the same model
        """
        # Check cache first
        if self.model_name in self._model_cache:
            logger.info(f"Loading model from cache: {self.model_name}")
            self.model = self._model_cache[self.model_name]
            self.tokenizer = self._tokenizer_cache[self.model_name]
            return
        
        try:
            logger.info(f"Loading model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
            self.model = AutoModel.from_pretrained(self.model_name, trust_remote_code=True)
            
            # Move model to device
            self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode
            
            # Cache the model
            self._model_cache[self.model_name] = self.model
            self._tokenizer_cache[self.model_name] = self.tokenizer
            
            logger.info(f"Model loaded successfully: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise
    
    def _ensure_model_loaded(self):
        """Ensure model is loaded before use"""
        if self.model is None or self.tokenizer is None:
            self.load_model()

    def embed_function(self, signature: str, docstring: Optional[str], body: str, 
                      max_length: int = 1024) -> np.ndarray:
        """
        Generate embedding for a single function
        
        Args:
            signature: Function signature (def line)
            docstring: Function docstring (optional)
            body: Full function body
            max_length: Maximum token length (default 8192)
            
        Returns:
            Normalized embedding vector (768-dim)
        """
        self._ensure_model_loaded()
        
        # Concatenate signature, docstring, and body
        parts = [signature]
        if docstring:
            parts.append(docstring)
        
        # Jina has 8k context, we can usually include the whole body
        parts.append(body)
        
        text = "\n".join(parts)
        
        try:
            # Tokenize
            inputs = self.tokenizer(
                text,
                max_length=max_length,
                padding=True,
                truncation=True,
                return_tensors='pt'
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate embedding
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Jina V2 uses mean pooling over non-padded tokens for optimal performance, 
                # but [CLS] (index 0) is also supported and often sufficient.
                # However, for Jina V2 specifically, the recommendation is mean pooling.
                # Let's check if the model has a pooler or we do it manually.
                # Standard AutoModel output usually has last_hidden_state.
                
                # Manual Mean Pooling for better quality on long docs
                last_hidden_state = outputs.last_hidden_state
                attention_mask = inputs['attention_mask']
                
                # Mask padding
                input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
                sum_embeddings = torch.sum(last_hidden_state * input_mask_expanded, 1)
                sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                embedding = (sum_embeddings / sum_mask).cpu().numpy()
            
            # Normalize
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding.flatten()
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return zero vector as fallback
            return np.zeros(768, dtype=np.float32)

    def embed_batch(self, texts: List[str], batch_size: int = 32, 
                   max_length: int = 1024) -> np.ndarray:
        """
        Generate embeddings for a batch of texts
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process at once
            max_length: Maximum token length
            
        Returns:
            Numpy array of embeddings (n_texts x embedding_dim)
        """
        self._ensure_model_loaded()
        
        if not texts:
            return np.array([])
        
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            try:
                # Tokenize batch
                inputs = self.tokenizer(
                    batch_texts,
                    max_length=max_length,
                    padding=True,
                    truncation=True,
                    return_tensors='pt'
                )
                
                # Move to device
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                # Generate embeddings
                with torch.no_grad():
                    # SANITY CHECK: Ensure input dimensions match before passing to model
                    if 'input_ids' in inputs and 'attention_mask' in inputs:
                        ids_shape = inputs['input_ids'].shape
                        mask_shape = inputs['attention_mask'].shape
                        
                        if ids_shape[0] != mask_shape[0] or ids_shape[1] != mask_shape[1]:
                            logger.warning(f"Tensor mismatch detected! IDs: {ids_shape}, Mask: {mask_shape}. Fixing...")
                            
                            # Fix Batch Dimension
                            if mask_shape[0] == 1 and ids_shape[0] > 1:
                                inputs['attention_mask'] = inputs['attention_mask'].expand(ids_shape[0], -1)
                            
                            # Fix Sequence Dimension
                            current_mask = inputs['attention_mask']
                            if current_mask.size(1) > ids_shape[1]:
                                inputs['attention_mask'] = current_mask[:, :ids_shape[1]]
                            elif current_mask.size(1) < ids_shape[1]:
                                padding = torch.zeros((current_mask.size(0), ids_shape[1] - current_mask.size(1)), 
                                                      device=current_mask.device, dtype=current_mask.dtype)
                                inputs['attention_mask'] = torch.cat([current_mask, padding], dim=1)

                    outputs = self.model(**inputs)
                    # Use mean pooling
                    last_hidden_state = outputs.last_hidden_state
                    attention_mask = inputs['attention_mask']
                    
                    # Force alignment
                    min_seq_len = min(attention_mask.size(1), last_hidden_state.size(1))
                    attention_mask = attention_mask[:, :min_seq_len]
                    last_hidden_state = last_hidden_state[:, :min_seq_len, :]

                    if attention_mask.size(0) != last_hidden_state.size(0):
                         if attention_mask.size(0) == 1:
                             attention_mask = attention_mask.expand(last_hidden_state.size(0), -1)

                    try:
                        input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
                    except Exception as e:
                        logger.error(f"CRASH DEBUG: Mask: {attention_mask.shape}, State: {last_hidden_state.shape}")
                        raise e

                    sum_embeddings = torch.sum(last_hidden_state * input_mask_expanded, 1)
                    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                    embeddings = (sum_embeddings / sum_mask).cpu().numpy()
                
                # Normalize each embedding
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                embeddings = embeddings / norms
                
                all_embeddings.append(embeddings)
                
                logger.debug(f"Processed batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
                
            except Exception as e:
                logger.error(f"Failed to process batch {i//batch_size + 1}: {e}")
                # Add zero vectors for failed batch
                zero_batch = np.zeros((len(batch_texts), 768), dtype=np.float32)
                all_embeddings.append(zero_batch)
        
        # Concatenate all batches
        result = np.vstack(all_embeddings)
        logger.info(f"Generated {len(result)} embeddings")
        
        return result
    
    def embed_issue(self, issue_title: str, issue_body: str, 
                   max_length: int = 1024) -> np.ndarray:
        """
        Generate embedding for an issue (title + body)
        
        Args:
            issue_title: Issue title
            issue_body: Issue body text
            max_length: Maximum token length
            
        Returns:
            Normalized embedding vector
        """
        # Concatenate title and body
        text = f"{issue_title}\n{issue_body}"
        
        # Use single embedding method
        return self.embed_function(text, None, "", max_length)


