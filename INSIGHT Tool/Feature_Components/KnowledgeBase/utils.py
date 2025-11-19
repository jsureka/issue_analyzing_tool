"""
Utility functions for Knowledge Base System
"""

import hashlib
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_commit_sha(repo_path: str) -> str:
    """
    Get current commit SHA from repository
    
    Args:
        repo_path: Path to repository root
        
    Returns:
        Commit SHA or 'unknown' if not available
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.warning(f"Could not get commit SHA: {e}")
    
    return "unknown"


def validate_repo_path(repo_path: str) -> bool:
    """
    Validate that repository path exists and is accessible
    
    Args:
        repo_path: Path to repository root
        
    Returns:
        True if valid, False otherwise
    """
    path = Path(repo_path)
    
    if not path.exists():
        logger.error(f"Repository path does not exist: {repo_path}")
        return False
    
    if not path.is_dir():
        logger.error(f"Repository path is not a directory: {repo_path}")
        return False
    
    # Check if it's a git repository
    git_dir = path / ".git"
    if not git_dir.exists():
        logger.warning(f"Path is not a git repository: {repo_path}")
        # Still return True as it might be a valid code directory
    
    return True


def generate_function_id(file_path: str, function_name: str, start_line: int) -> str:
    """
    Generate unique ID for a function
    
    Args:
        file_path: File path
        function_name: Function name
        start_line: Starting line number
        
    Returns:
        Unique function ID (16-char hash)
    """
    combined = f"{file_path}:{function_name}:{start_line}"
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def generate_file_id(repo_name: str, file_path: str) -> str:
    """
    Generate unique ID for a file
    
    Args:
        repo_name: Repository name
        file_path: File path
        
    Returns:
        Unique file ID (16-char hash)
    """
    combined = f"{repo_name}:{file_path}"
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def generate_class_id(repo_name: str, file_path: str, class_name: str) -> str:
    """
    Generate unique ID for a class
    
    Args:
        repo_name: Repository name
        file_path: File path
        class_name: Class name
        
    Returns:
        Unique class ID (16-char hash)
    """
    combined = f"{repo_name}:{file_path}:{class_name}"
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def sanitize_repo_name(repo_name: str) -> str:
    """
    Sanitize repository name for use in file paths
    
    Args:
        repo_name: Repository name (e.g., "owner/repo")
        
    Returns:
        Sanitized name safe for file paths
    """
    return repo_name.replace('/', '_').replace('\\', '_')


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
