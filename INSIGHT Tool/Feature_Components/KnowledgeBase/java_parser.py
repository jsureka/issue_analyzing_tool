"""
Java code parser using tree-sitter
Extracts methods, classes, interfaces, enums, imports, and call relationships from Java code
"""

import logging
from typing import List, Optional, Dict

try:
    from tree_sitter import Language, Parser
    import tree_sitter_java as tsjava
except ImportError:
    raise ImportError(
        "tree-sitter and tree-sitter-java are required. "
        "Install with: pip install tree-sitter tree-sitter-java"
    )

from .language_parser import LanguageParser, FunctionInfo, ClassInfo

logger = logging.getLogger(__name__)


class JavaParser(LanguageParser):
    """Parser for Java code using tree-sitter"""
    
    def __init__(self):
        """Initialize the Java parser with tree-sitter"""
        try:
            # tree-sitter-java 0.21.0 uses same API as tree-sitter-python
            self.language = Language(tsjava.language(), "java")
            self.parser = Parser()
            self.parser.set_language(self.language)
            logger.info("Java parser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Java parser: {e}")
            raise
    
    def get_language_name(self) -> str:
        """Return the language name"""
        return "java"
    
    def parse_file(self, file_path: str) -> Optional[object]:
        """
        Parse a Java file and return its AST
        
        Args:
            file_path: Path to the Java file
            
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
    
    def _extract_javadoc(self, node, source_code: bytes) -> Optional[str]:
        """
        Extract Javadoc comment preceding a method or class
        
        Args:
            node: Tree-sitter node (method_declaration or class_declaration)
            source_code: Source code as bytes
            
        Returns:
            Cleaned Javadoc string or None
        """
        # Look for block_comment before the node
        # In tree-sitter, we need to check siblings or parent context
        parent = node.parent
        if parent is None:
            return None
        
        # Find the index of current node in parent's children
        node_index = None
        for i, child in enumerate(parent.children):
            if child == node:
                node_index = i
                break
        
        if node_index is None or node_index == 0:
            return None
        
        # Check previous sibling for block_comment
        prev_node = parent.children[node_index - 1]
        if prev_node.type == 'block_comment':
            comment_text = self._get_node_text(prev_node, source_code)
            # Clean up Javadoc: remove /** and */ and leading * on each line
            lines = comment_text.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if line.startswith('/**'):
                    line = line[3:].strip()
                elif line.startswith('*/'):
                    continue
                elif line.startswith('*'):
                    line = line[1:].strip()
                if line:
                    cleaned_lines.append(line)
            return ' '.join(cleaned_lines) if cleaned_lines else None
        
        return None
    
    def _get_method_signature(self, node, source_code: bytes) -> str:
        """
        Extract full method signature including modifiers, return type, name, and parameters
        
        Args:
            node: method_declaration node
            source_code: Source code as bytes
            
        Returns:
            Full method signature as string
        """
        signature_parts = []
        
        for child in node.children:
            # Collect modifiers (public, private, static, etc.)
            if child.type == 'modifiers':
                modifiers = self._get_node_text(child, source_code).strip()
                if modifiers:
                    signature_parts.append(modifiers)
            
            # Collect return type
            elif child.type in ['type_identifier', 'void_type', 'generic_type', 'array_type', 
                               'integral_type', 'floating_point_type', 'boolean_type']:
                return_type = self._get_node_text(child, source_code).strip()
                signature_parts.append(return_type)
            
            # Collect method name
            elif child.type == 'identifier':
                method_name = self._get_node_text(child, source_code).strip()
                signature_parts.append(method_name)
            
            # Collect parameters
            elif child.type == 'formal_parameters':
                params = self._get_node_text(child, source_code).strip()
                signature_parts.append(params)
                break  # Stop after parameters
        
        return ' '.join(signature_parts)

    
    def extract_functions(self, tree, source_code: bytes, file_path: str = "") -> List[FunctionInfo]:
        """
        Extract all methods from the AST (from classes, interfaces, and enums)
        
        Args:
            tree: Tree-sitter tree object
            source_code: Source code as bytes
            file_path: Path to the file (for logging)
            
        Returns:
            List of FunctionInfo objects
        """
        functions = []
        
        def traverse(node, class_name: Optional[str] = None):
            """Recursively traverse the AST to find method declarations"""
            if node.type == 'method_declaration':
                try:
                    # Extract method name
                    name = None
                    for child in node.children:
                        if child.type == 'identifier':
                            name = self._get_node_text(child, source_code)
                            break
                    
                    if not name:
                        logger.warning(f"Method without name in {file_path}")
                        return
                    
                    # Extract signature
                    signature = self._get_method_signature(node, source_code)
                    
                    # Extract Javadoc
                    docstring = self._extract_javadoc(node, source_code)
                    
                    # Get line numbers (tree-sitter uses 0-based, convert to 1-based)
                    start_line = node.start_point[0] + 1
                    end_line = node.end_point[0] + 1
                    
                    # Extract method body
                    body = self._get_node_text(node, source_code)
                    
                    func_info = FunctionInfo(
                        name=name,
                        signature=signature,
                        start_line=start_line,
                        end_line=end_line,
                        docstring=docstring,
                        class_name=class_name,
                        body=body,
                        language="java"
                    )
                    functions.append(func_info)
                    
                except Exception as e:
                    logger.error(f"Error extracting method in {file_path}: {e}")
            
            elif node.type in ['class_declaration', 'interface_declaration', 'enum_declaration']:
                # Extract class/interface/enum name for nested methods
                class_name_node = None
                for child in node.children:
                    if child.type == 'identifier':
                        class_name_node = self._get_node_text(child, source_code)
                        break
                
                # Traverse class body with class context
                for child in node.children:
                    if child.type == 'class_body' or child.type == 'interface_body' or child.type == 'enum_body':
                        for body_child in child.children:
                            traverse(body_child, class_name_node)
            
            # Recursively traverse children
            for child in node.children:
                if child.type not in ['class_body', 'interface_body', 'enum_body']:
                    traverse(child, class_name)
        
        traverse(tree.root_node)
        logger.info(f"Extracted {len(functions)} methods from {file_path}")
        return functions

    
    def extract_classes(self, tree, source_code: bytes, file_path: str = "") -> List[ClassInfo]:
        """
        Extract all classes, interfaces, and enums from the AST
        
        Args:
            tree: Tree-sitter tree object
            source_code: Source code as bytes
            file_path: Path to the file (for logging)
            
        Returns:
            List of ClassInfo objects
        """
        classes = []
        
        def traverse(node):
            """Recursively traverse the AST to find class/interface/enum declarations"""
            if node.type in ['class_declaration', 'interface_declaration', 'enum_declaration']:
                try:
                    # Extract class/interface/enum name
                    name = None
                    for child in node.children:
                        if child.type == 'identifier':
                            name = self._get_node_text(child, source_code)
                            break
                    
                    if not name:
                        logger.warning(f"Class/Interface/Enum without name in {file_path}")
                        return
                    
                    # Get line numbers
                    start_line = node.start_point[0] + 1
                    end_line = node.end_point[0] + 1
                    
                    # Determine class type
                    class_type = "class"
                    if node.type == 'interface_declaration':
                        class_type = "interface"
                    elif node.type == 'enum_declaration':
                        class_type = "enum"
                    
                    # Extract method names within this class/interface/enum
                    function_names = []
                    for child in node.children:
                        if child.type in ['class_body', 'interface_body', 'enum_body']:
                            for body_child in child.children:
                                if body_child.type == 'method_declaration':
                                    for method_child in body_child.children:
                                        if method_child.type == 'identifier':
                                            func_name = self._get_node_text(method_child, source_code)
                                            function_names.append(func_name)
                                            break
                    
                    class_info = ClassInfo(
                        name=name,
                        start_line=start_line,
                        end_line=end_line,
                        functions=function_names,
                        language="java",
                        class_type=class_type
                    )
                    classes.append(class_info)
                    
                except Exception as e:
                    logger.error(f"Error extracting class in {file_path}: {e}")
            
            # Recursively traverse children
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        logger.info(f"Extracted {len(classes)} classes/interfaces/enums from {file_path}")
        return classes

    
    def extract_imports(self, tree, source_code: bytes) -> List[str]:
        """
        Extract all import statements from the AST
        
        Args:
            tree: Tree-sitter tree object
            source_code: Source code as bytes
            
        Returns:
            List of import statements as strings
        """
        imports = []
        
        def traverse(node):
            """Recursively traverse to find import declarations"""
            if node.type == 'import_declaration':
                import_text = self._get_node_text(node, source_code)
                imports.append(import_text)
            
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        return imports
    
    def extract_calls(self, tree, source_code: bytes) -> Dict[str, List[str]]:
        """
        Extract method call relationships within each method
        
        Args:
            tree: Tree-sitter tree object
            source_code: Source code as bytes
            
        Returns:
            Dictionary mapping method names to lists of called method names
        """
        calls_map = {}
        
        def traverse(node, in_method: Optional[str] = None):
            """Recursively traverse to find method invocations"""
            if node.type == 'method_declaration':
                # Extract method name
                method_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        method_name = self._get_node_text(child, source_code)
                        break
                
                if method_name:
                    calls_map[method_name] = []
                    # Traverse method body with context
                    for child in node.children:
                        traverse(child, method_name)
                return  # Don't traverse children again
            
            elif node.type == 'method_invocation':
                # This is a method call
                if in_method:
                    # Extract the called method name
                    for child in node.children:
                        if child.type == 'identifier':
                            called_name = self._get_node_text(child, source_code)
                            if called_name not in calls_map.get(in_method, []):
                                calls_map[in_method].append(called_name)
                            break
            
            # Recursively traverse children
            for child in node.children:
                traverse(child, in_method)
        
        traverse(tree.root_node)
        return calls_map
