"""
Abstract base class for language-specific code parsers
Defines common interface for parsing different programming languages
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class FunctionInfo:
    """Language-agnostic function information"""
    name: str
    signature: str
    start_line: int
    end_line: int
    docstring: Optional[str]
    class_name: Optional[str]  # None if module-level function
    body: str
    language: str  # "python", "java", etc.


@dataclass
class ClassInfo:
    """Language-agnostic class information"""
    name: str
    start_line: int
    end_line: int
    functions: List[str]  # List of function names in this class
    language: str  # "python", "java", etc.
    docstring: Optional[str] = None
    class_type: str = "class"  # "class", "interface", "enum"


class LanguageParser(ABC):
    """Abstract base class for language-specific parsers"""
    
    @abstractmethod
    def parse_file(self, file_path: str) -> Optional[object]:
        """
        Parse a source file and return its AST
        
        Args:
            file_path: Path to the source file
            
        Returns:
            Tree-sitter tree object or None if parsing fails
        """
        pass
    
    @abstractmethod
    def extract_functions(self, tree, source_code: bytes, file_path: str = "") -> List[FunctionInfo]:
        """
        Extract all functions/methods from the AST
        
        Args:
            tree: Tree-sitter tree object
            source_code: Source code as bytes
            file_path: Path to the file (for logging)
            
        Returns:
            List of FunctionInfo objects
        """
        pass
    
    @abstractmethod
    def extract_classes(self, tree, source_code: bytes, file_path: str = "") -> List[ClassInfo]:
        """
        Extract all classes/interfaces from the AST
        
        Args:
            tree: Tree-sitter tree object
            source_code: Source code as bytes
            file_path: Path to the file (for logging)
            
        Returns:
            List of ClassInfo objects
        """
        pass
    
    @abstractmethod
    def extract_imports(self, tree, source_code: bytes) -> List[str]:
        """
        Extract all import statements from the AST
        
        Args:
            tree: Tree-sitter tree object
            source_code: Source code as bytes
            
        Returns:
            List of import statements as strings
        """
        pass
    
    @abstractmethod
    def extract_calls(self, tree, source_code: bytes) -> Dict[str, List[str]]:
        """
        Extract function call relationships
        
        Args:
            tree: Tree-sitter tree object
            source_code: Source code as bytes
            
        Returns:
            Dictionary mapping function names to lists of called function names
        """
        pass
    
    @abstractmethod
    def get_language_name(self) -> str:
        """
        Return the language name
        
        Returns:
            Language name (e.g., 'python', 'java')
        """
        pass
