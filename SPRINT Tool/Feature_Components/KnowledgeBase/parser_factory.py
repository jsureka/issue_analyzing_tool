"""
Parser Factory and Language Detector for multi-language support
Selects appropriate parser based on file extension
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Type

from .language_parser import LanguageParser
from .parser import PythonParser
from .java_parser import JavaParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """Factory for creating language-specific parsers"""
    
    def __init__(self):
        """Initialize parser factory with registry"""
        self._parsers: Dict[str, Type[LanguageParser]] = {}
        self._extension_map: Dict[str, str] = {}
        self._register_default_parsers()
    
    def _register_default_parsers(self):
        """Register built-in parsers for Python and Java"""
        self.register_parser("python", PythonParser, [".py"])
        self.register_parser("java", JavaParser, [".java"])
        logger.info("Registered default parsers: python, java")
    
    def register_parser(self, language: str, parser_class: Type[LanguageParser], extensions: List[str]):
        """
        Register a new parser for a language
        
        Args:
            language: Language name (e.g., "python", "java")
            parser_class: Parser class that implements LanguageParser
            extensions: List of file extensions (e.g., [".py", ".pyw"])
        """
        self._parsers[language] = parser_class
        for ext in extensions:
            ext_lower = ext.lower()
            self._extension_map[ext_lower] = language
        logger.debug(f"Registered parser for {language} with extensions {extensions}")
    
    def get_parser(self, file_path: str) -> Optional[LanguageParser]:
        """
        Get parser instance for a file based on extension
        
        Args:
            file_path: Path to the source file
            
        Returns:
            Parser instance or None if extension not supported
        """
        ext = Path(file_path).suffix.lower()
        language = self._extension_map.get(ext)
        
        if language is None:
            return None
        
        parser_class = self._parsers.get(language)
        if parser_class is None:
            logger.warning(f"Parser class not found for language: {language}")
            return None
        
        try:
            return parser_class()
        except Exception as e:
            logger.error(f"Failed to instantiate parser for {language}: {e}")
            return None
    
    def get_supported_extensions(self) -> List[str]:
        """
        Return list of all supported file extensions
        
        Returns:
            List of file extensions (e.g., [".py", ".java"])
        """
        return list(self._extension_map.keys())
    
    def get_supported_languages(self) -> List[str]:
        """
        Return list of all supported languages
        
        Returns:
            List of language names (e.g., ["python", "java"])
        """
        return list(self._parsers.keys())


class LanguageDetector:
    """Detect programming language from file extension"""
    
    def __init__(self, parser_factory: ParserFactory):
        """
        Initialize language detector
        
        Args:
            parser_factory: ParserFactory instance to use for detection
        """
        self.parser_factory = parser_factory
    
    def detect_language(self, file_path: str) -> Optional[str]:
        """
        Detect language from file extension
        
        Args:
            file_path: Path to the source file
            
        Returns:
            Language name (e.g., "python", "java") or None if not supported
        """
        parser = self.parser_factory.get_parser(file_path)
        if parser is not None:
            return parser.get_language_name()
        return None
    
    def is_supported(self, file_path: str) -> bool:
        """
        Check if file extension is supported
        
        Args:
            file_path: Path to the source file
            
        Returns:
            True if file extension is supported, False otherwise
        """
        return self.detect_language(file_path) is not None
