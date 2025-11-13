"""
Issue text processor - cleans and prepares issue text for embedding
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ProcessedIssue:
    """Processed issue with cleaned text and embedding"""
    original_title: str
    original_body: str
    cleaned_text: str
    embedding: np.ndarray
    word_count: int


class IssueProcessor:
    """Processes GitHub issues for retrieval"""
    
    def __init__(self, embedder):
        """
        Initialize issue processor
        
        Args:
            embedder: CodeEmbedder instance for generating embeddings
        """
        self.embedder = embedder
        logger.info("IssueProcessor initialized")
    
    def clean_text(self, text: str) -> str:
        """
        Remove markdown and special characters from text
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove markdown headers
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        
        # Remove markdown links [text](url)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Remove markdown code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`[^`]+`', '', text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://\S+', '', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\-]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text (lowercase, whitespace)
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Convert to lowercase
        text = text.lower()
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text

    def process_issue(self, title: str, body: str) -> Optional[ProcessedIssue]:
        """
        Process issue text and generate embedding
        
        Args:
            title: Issue title
            body: Issue body text
            
        Returns:
            ProcessedIssue or None if validation fails
        """
        # Concatenate title and body
        full_text = f"{title}\n{body}"
        
        # Clean text
        cleaned = self.clean_text(full_text)
        
        # Normalize
        normalized = self.normalize_text(cleaned)
        
        # Validate minimum length (10 words)
        word_count = len(normalized.split())
        if word_count < 10:
            logger.warning(f"Issue text too short: {word_count} words (minimum 10)")
            return None
        
        logger.info(f"Processing issue with {word_count} words")
        
        # Generate embedding
        try:
            embedding = self.embedder.embed_issue(title, body)
            
            return ProcessedIssue(
                original_title=title,
                original_body=body,
                cleaned_text=normalized,
                embedding=embedding,
                word_count=word_count
            )
        except Exception as e:
            logger.error(f"Failed to generate issue embedding: {e}")
            return None
