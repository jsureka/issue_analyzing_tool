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


@dataclass
class CallInfo:
    """Information about a function/method call"""
    name: str # The function/method name called
    scope: Optional[str] = None # The object or module the function is called on (e.g. 'self', 'np', 'user')
    args: List[str] = None
    start_line: int = 0
    end_line: int = 0

@dataclass
class ImportInfo:
    """Information about an import"""
    module_name: str # The actual module name (e.g. 'numpy', 'utils')
    alias: Optional[str] = None # The alias used in code (e.g. 'np')
    imported_elements: List[str] = None # Specific elements imported (e.g. ['func1', 'ClassA'])
    
    def to_string(self) -> str:
        """Convert to string representation"""
        if self.imported_elements:
            base = f"from {self.module_name} import {', '.join(self.imported_elements)}"
        else:
            base = f"import {self.module_name}"
        if self.alias:
            base += f" as {self.alias}"
        return base


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
    def extract_imports(self, tree, source_code: bytes) -> List[ImportInfo]:
        """
        Extract all import statements from the AST
        
        Args:
            tree: Tree-sitter tree object
            source_code: Source code as bytes
            
        Returns:
            List of ImportInfo objects
        """
        pass
    
    @abstractmethod
    def extract_calls(self, tree, source_code: bytes) -> Dict[str, List[CallInfo]]:
        """
        Extract function call relationships
        
        Args:
            tree: Tree-sitter tree object
            source_code: Source code as bytes
            
        Returns:
            Dictionary mapping function names to lists of CallInfo objects
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
