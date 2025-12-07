"""
Python code parser using tree-sitter
Extracts functions, classes, imports, and call relationships from Python code
"""

import logging
from typing import List, Optional, Dict
from pathlib import Path

try:
    from tree_sitter import Language, Parser
    import tree_sitter_python as tspython
except ImportError:
    raise ImportError(
        "tree-sitter and tree-sitter-python are required. "
        "Install with: pip install tree-sitter tree-sitter-python"
    )

from .language_parser import LanguageParser, FunctionInfo, ClassInfo

logger = logging.getLogger(__name__)


class PythonParser(LanguageParser):
    """Parser for Python code using tree-sitter"""
    
    def __init__(self):
        """Initialize the Python parser with tree-sitter"""
        try:
            self.language = Language(tspython.language(), "python")
            self.parser = Parser()
            self.parser.set_language(self.language)
            logger.info("Python parser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Python parser: {e}")
            raise
    
    def get_language_name(self) -> str:
        """Return the language name"""
        return "python"
    
    def parse_file(self, file_path: str) -> Optional[object]:
        """
        Parse a Python file and return its AST
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Tree-sitter tree object or None if parsing fails
        """
        try:
            with open(file_path, 'rb') as f:
                source_code = f.read()
            
            tree = self.parser.parse(source_code)
            
            if tree.root_node.has_error:
                logger.warning(f"Parse errors in file: {file_path}")
            
            return tree
        except Exception as e:
            logger.error(f"Failed to parse file {file_path}: {e}")
            return None
    
    def _get_node_text(self, node, source_code: bytes) -> str:
        """Extract text content from a tree-sitter node"""
        return source_code[node.start_byte:node.end_byte].decode('utf-8')
    
    def _extract_docstring(self, node, source_code: bytes) -> Optional[str]:
        """Extract docstring from a function or class node"""
        # Look for the first expression_statement that contains a string
        for child in node.children:
            if child.type == 'block':
                for stmt in child.children:
                    if stmt.type == 'expression_statement':
                        for expr_child in stmt.children:
                            if expr_child.type == 'string':
                                docstring = self._get_node_text(expr_child, source_code)
                                # Remove quotes and clean up
                                docstring = docstring.strip('"""').strip("'''").strip('"').strip("'")
                                return docstring.strip()
        return None
    
    def _get_function_signature(self, node, source_code: bytes) -> str:
        """Extract function signature (def line)"""
        # Find the line containing 'def' up to the colon
        for child in node.children:
            if child.type == 'identifier':
                # Get from 'def' to ':'
                start = node.start_byte
                # Find the colon
                for c in node.children:
                    if c.type == ':':
                        end = c.start_byte
                        signature = source_code[start:end].decode('utf-8').strip()
                        return signature
        
        # Fallback: get first line
        text = self._get_node_text(node, source_code)
        first_line = text.split('\n')[0].strip()
        if first_line.endswith(':'):
            first_line = first_line[:-1]
        return first_line

    def extract_functions(self, tree, source_code: bytes, file_path: str = "") -> List[FunctionInfo]:
        """
        Extract all functions from the AST
        
        Args:
            tree: Tree-sitter tree object
            source_code: Source code as bytes
            file_path: Path to the file (for logging)
            
        Returns:
            List of FunctionInfo objects
        """
        functions = []
        
        def traverse(node, class_name: Optional[str] = None):
            """Recursively traverse the AST to find function definitions"""
            if node.type == 'function_definition':
                try:
                    # Extract function name
                    name = None
                    for child in node.children:
                        if child.type == 'identifier':
                            name = self._get_node_text(child, source_code)
                            break
                    
                    if not name:
                        logger.warning(f"Function without name in {file_path}")
                        return
                    
                    # Extract signature
                    signature = self._get_function_signature(node, source_code)
                    
                    # Extract docstring
                    docstring = self._extract_docstring(node, source_code)
                    
                    # Get line numbers (tree-sitter uses 0-based, convert to 1-based)
                    start_line = node.start_point[0] + 1
                    end_line = node.end_point[0] + 1
                    
                    # Extract function body
                    body = self._get_node_text(node, source_code)
                    
                    func_info = FunctionInfo(
                        name=name,
                        signature=signature,
                        start_line=start_line,
                        end_line=end_line,
                        docstring=docstring,
                        class_name=class_name,
                        body=body,
                        language="python"
                    )
                    functions.append(func_info)
                    
                except Exception as e:
                    logger.error(f"Error extracting function in {file_path}: {e}")
            
            elif node.type == 'class_definition':
                # Extract class name for nested functions
                class_name_node = None
                for child in node.children:
                    if child.type == 'identifier':
                        class_name_node = self._get_node_text(child, source_code)
                        break
                
                # Traverse class body with class context
                for child in node.children:
                    traverse(child, class_name_node)
                return  # Don't traverse children again
            
            # Recursively traverse children
            for child in node.children:
                traverse(child, class_name)
        
        traverse(tree.root_node)
        logger.info(f"Extracted {len(functions)} functions from {file_path}")
        return functions

    def extract_classes(self, tree, source_code: bytes, file_path: str = "") -> List[ClassInfo]:
        """
        Extract all classes from the AST
        
        Args:
            tree: Tree-sitter tree object
            source_code: Source code as bytes
            file_path: Path to the file (for logging)
            
        Returns:
            List of ClassInfo objects
        """
        classes = []
        
        def traverse(node):
            """Recursively traverse the AST to find class definitions"""
            if node.type == 'class_definition':
                try:
                    # Extract class name
                    name = None
                    for child in node.children:
                        if child.type == 'identifier':
                            name = self._get_node_text(child, source_code)
                            break
                    
                    if not name:
                        logger.warning(f"Class without name in {file_path}")
                        return
                    
                    # Get line numbers
                    start_line = node.start_point[0] + 1
                    end_line = node.end_point[0] + 1
                    
                    # Extract function names within this class
                    function_names = []
                    for child in node.children:
                        if child.type == 'block':
                            for stmt in child.children:
                                if stmt.type == 'function_definition':
                                    for func_child in stmt.children:
                                        if func_child.type == 'identifier':
                                            func_name = self._get_node_text(func_child, source_code)
                                            function_names.append(func_name)
                                            break
                    
                    # Extract docstring
                    docstring = self._extract_docstring(node, source_code)

                    class_info = ClassInfo(
                        name=name,
                        start_line=start_line,
                        end_line=end_line,
                        functions=function_names,
                        language="python",
                        class_type="class",
                        docstring=docstring
                    )
                    classes.append(class_info)
                    
                except Exception as e:
                    logger.error(f"Error extracting class in {file_path}: {e}")
            
            # Recursively traverse children
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        logger.info(f"Extracted {len(classes)} classes from {file_path}")
        return classes

    def extract_imports(self, tree, source_code: bytes) -> List[str]:
        """
        Extract all import statements from the AST
        
        Args:
            tree: Tree-sitter tree object
            source_code: Source code as bytes
            
        Returns:
            List of imported module names
        """
        imports = []
        
        def traverse(node):
            """Recursively traverse to find import statements"""
            if node.type == 'import_statement':
                # import module
                import_text = self._get_node_text(node, source_code)
                imports.append(import_text)
            
            elif node.type == 'import_from_statement':
                # from module import something
                import_text = self._get_node_text(node, source_code)
                imports.append(import_text)
            
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        return imports
    
    def extract_calls(self, tree, source_code: bytes) -> Dict[str, List[str]]:
        """
        Extract function calls and references within each function
        
        Args:
            tree: Tree-sitter tree object
            source_code: Source code as bytes
            
        Returns:
            Dictionary mapping function names to lists of called/referenced function names
        """
        calls_map = {}
        
        def traverse(node, in_function: Optional[str] = None):
            """Recursively traverse to find function calls and references"""
            
            if node.type == 'function_definition':
                # Extract function name
                func_name = None
                body_node = None
                
                for child in node.children:
                    if child.type == 'identifier':
                        func_name = self._get_node_text(child, source_code)
                    elif child.type == 'block':
                        body_node = child
                
                if func_name and body_node:
                    calls_map[func_name] = []
                    # Traverse ONLY the function body to avoid capturing params
                    traverse(body_node, func_name)
                return  # Don't traverse children again (we handled body manually)
            
            elif node.type == 'call':
                # This is a function call
                if in_function:
                    # Extract the called function name
                    for child in node.children:
                        if child.type == 'identifier':
                            called_name = self._get_node_text(child, source_code)
                            if called_name not in calls_map.get(in_function, []):
                                calls_map[in_function].append(called_name)
                            break
                        elif child.type == 'attribute':
                            # Handle method calls like obj.method()
                            called_name = self._get_node_text(child, source_code)
                            if called_name not in calls_map.get(in_function, []):
                                calls_map[in_function].append(called_name)
                            break
            
            elif node.type == 'identifier':
                # This is a potential function reference (e.g. passed as argument)
                if in_function:
                    name = self._get_node_text(node, source_code)
                    if name not in calls_map.get(in_function, []):
                        calls_map[in_function].append(name)

            # Recursively traverse children
            for child in node.children:
                traverse(child, in_function)
        
        traverse(tree.root_node)
        return calls_map
