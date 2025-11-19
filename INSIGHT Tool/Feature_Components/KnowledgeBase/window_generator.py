"""
Window Generator - Generates overlapping line windows for fine-grained localization
"""

import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Window:
    """Represents a line window within a function"""
    function_id: str
    file_path: str
    function_name: str
    token_start: int
    token_end: int
    line_start: int
    line_end: int
    text: str
    window_index: int


class WindowGenerator:
    """Generates overlapping line windows from function bodies"""
    
    def __init__(self, tokenizer=None, window_size: int = 48, stride: int = 24):
        """
        Initialize window generator
        
        Args:
            tokenizer: Tokenizer for splitting text (if None, uses simple whitespace)
            window_size: Size of each window in tokens
            stride: Stride between windows (overlap = window_size - stride)
        """
        self.tokenizer = tokenizer
        self.window_size = window_size
        self.stride = stride
        logger.info(f"WindowGenerator initialized: window_size={window_size}, stride={stride}")
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into tokens
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        if self.tokenizer:
            # Use provided tokenizer (e.g., from transformers)
            try:
                tokens = self.tokenizer.tokenize(text)
                return tokens
            except Exception as e:
                logger.warning(f"Tokenizer failed, falling back to whitespace: {e}")
        
        # Simple whitespace tokenization as fallback
        tokens = text.split()
        return tokens
    
    def _map_tokens_to_lines(self, text: str, tokens: List[str]) -> List[int]:
        """
        Map token positions to line numbers
        
        Args:
            text: Original text
            tokens: List of tokens
            
        Returns:
            List of line numbers for each token
        """
        lines = text.split('\n')
        token_to_line = []
        
        # Track position in text
        char_pos = 0
        current_line = 0
        line_start_pos = 0
        
        for token in tokens:
            # Find token in text starting from current position
            token_pos = text.find(token, char_pos)
            
            if token_pos == -1:
                # Token not found, use current line
                token_to_line.append(current_line)
                continue
            
            # Count newlines between char_pos and token_pos
            newlines = text[char_pos:token_pos].count('\n')
            current_line += newlines
            
            token_to_line.append(current_line)
            char_pos = token_pos + len(token)
        
        return token_to_line
    
    def generate_windows(self, function_body: str, function_info: Dict[str, Any]) -> List[Window]:
        """
        Generate overlapping windows from function body
        
        Args:
            function_body: Function body text
            function_info: Dictionary with function metadata (id, name, file_path, start_line)
            
        Returns:
            List of Window objects
        """
        try:
            # Tokenize function body
            tokens = self._tokenize(function_body)
            
            # Check if function is too small for windowing
            if len(tokens) < self.window_size // 2:
                logger.debug(f"Function {function_info.get('name')} too small for windowing ({len(tokens)} tokens)")
                # Return single window with entire function
                return [Window(
                    function_id=function_info.get('id', ''),
                    file_path=function_info.get('file_path', ''),
                    function_name=function_info.get('name', ''),
                    token_start=0,
                    token_end=len(tokens),
                    line_start=function_info.get('start_line', 0),
                    line_end=function_info.get('end_line', 0),
                    text=function_body,
                    window_index=0
                )]
            
            # Map tokens to line numbers
            token_to_line = self._map_tokens_to_lines(function_body, tokens)
            
            # Generate windows with stride
            windows = []
            window_idx = 0
            
            for start_token in range(0, len(tokens), self.stride):
                end_token = min(start_token + self.window_size, len(tokens))
                
                # Get window tokens
                window_tokens = tokens[start_token:end_token]
                
                # Get line range for this window
                line_start = token_to_line[start_token] if start_token < len(token_to_line) else 0
                line_end = token_to_line[end_token - 1] if end_token - 1 < len(token_to_line) else 0
                
                # Reconstruct text from tokens (approximate)
                window_text = ' '.join(window_tokens)
                
                # Create window
                window = Window(
                    function_id=function_info.get('id', ''),
                    file_path=function_info.get('file_path', ''),
                    function_name=function_info.get('name', ''),
                    token_start=start_token,
                    token_end=end_token,
                    line_start=function_info.get('start_line', 0) + line_start,
                    line_end=function_info.get('start_line', 0) + line_end,
                    text=window_text,
                    window_index=window_idx
                )
                
                windows.append(window)
                window_idx += 1
                
                # Stop if we've reached the end
                if end_token >= len(tokens):
                    break
            
            logger.debug(f"Generated {len(windows)} windows for function {function_info.get('name')}")
            return windows
            
        except Exception as e:
            logger.error(f"Failed to generate windows for function {function_info.get('name')}: {e}")
            return []
    
    def extract_windows_from_functions(self, functions: List[Dict[str, Any]], 
                                      file_contents: Dict[str, str]) -> List[Window]:
        """
        Extract windows from multiple functions
        
        Args:
            functions: List of function dictionaries with metadata
            file_contents: Dictionary mapping file paths to their contents
            
        Returns:
            List of all windows from all functions
        """
        all_windows = []
        
        for func in functions:
            try:
                file_path = func.get('file_path', '')
                start_line = func.get('start_line', 0)
                end_line = func.get('end_line', 0)
                
                # Get file content
                if file_path not in file_contents:
                    logger.warning(f"File content not found for {file_path}")
                    continue
                
                file_content = file_contents[file_path]
                lines = file_content.split('\n')
                
                # Extract function body (convert to 0-based indexing)
                if start_line > 0 and end_line <= len(lines):
                    function_lines = lines[start_line - 1:end_line]
                    function_body = '\n'.join(function_lines)
                else:
                    logger.warning(f"Invalid line range for function {func.get('name')}")
                    continue
                
                # Generate windows
                windows = self.generate_windows(function_body, func)
                all_windows.extend(windows)
                
            except Exception as e:
                logger.error(f"Failed to extract windows from function {func.get('name')}: {e}")
                continue
        
        logger.info(f"Generated {len(all_windows)} total windows from {len(functions)} functions")
        return all_windows
