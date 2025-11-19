"""
Error hierarchy for Knowledge Base update operations
"""


class KnowledgeBaseUpdateError(Exception):
    """Base exception for knowledge base update errors"""
    pass


class GitOperationError(KnowledgeBaseUpdateError):
    """Raised when git operations fail"""
    pass


class RepositorySyncError(KnowledgeBaseUpdateError):
    """Raised when repository synchronization fails"""
    pass


class IndexUpdateError(KnowledgeBaseUpdateError):
    """Raised when index update operations fail"""
    pass


class ParsingError(KnowledgeBaseUpdateError):
    """Raised when file parsing fails"""
    pass


class EmbeddingError(KnowledgeBaseUpdateError):
    """Raised when embedding generation fails"""
    pass


class GraphUpdateError(KnowledgeBaseUpdateError):
    """Raised when graph database update fails"""
    pass
