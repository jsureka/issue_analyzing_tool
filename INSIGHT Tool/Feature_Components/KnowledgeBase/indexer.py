"""
Repository indexer - orchestrates parsing, embedding, and storage
"""

import logging
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .language_parser import FunctionInfo, ClassInfo
from .parser_factory import ParserFactory, LanguageDetector
from .embedder import CodeEmbedder
from .graph_store import GraphStore
from .vector_store import VectorStore
from .llm_service import LLMService

logger = logging.getLogger(__name__)


@dataclass
class IndexResult:
    """Result of repository indexing"""
    repo_name: str
    commit_sha: str
    total_files: int
    total_functions: int
    index_path: str
    metadata_path: str
    graph_nodes: int
    graph_edges: int
    indexing_time_seconds: float
    failed_files: List[str]


class RepositoryIndexer:
    """Orchestrates repository indexing process"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str, 
                 model_name: str = "jinaai/jina-embeddings-v2-base-code",
                 index_dir: str = "Data_Storage/KnowledgeBase"):
        """
        Initialize repository indexer
        
        Args:
            neo4j_uri: URI for Neo4j database
            neo4j_user: Username for Neo4j
            neo4j_password: Password for Neo4j
            model_name: Name of the embedding model
            index_dir: Directory to store indices
        """
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.model_name = model_name
        self.index_dir = Path(index_dir)
        
        self.parser_factory = ParserFactory()
        self.language_detector = LanguageDetector(self.parser_factory)
        self.embedder = CodeEmbedder(model_name)
        self.graph_store = GraphStore(neo4j_uri, neo4j_user, neo4j_password)
        self.vector_store = VectorStore(dimension=768)
        
    @staticmethod
    def create_file_skeleton(source_code: str, functions: List[Any], classes: List[Any]) -> str:
        """
        Create a skeleton of the file by masking top-level function and class bodies.
        Preserves imports, globals, and top-level logic.
        """
        lines = source_code.splitlines()
        output = []
        
        # Identify top-level entities (functions and classes)
        # Helper to get start/end lines
        candidates = []
        for f in functions:
            if not f.class_name: # Top level function
                candidates.append(f)
        candidates.extend(classes) # All classes treated as top level candidates
        
        # Sort by start line
        candidates.sort(key=lambda x: x.start_line)
        
        # Merge overlapped entities (e.g. nested classes shouldn't be processed if parent is)
        merged = []
        last_end = -1
        for ent in candidates:
            # 1-based indexing in entities
            start = ent.start_line
            end = ent.end_line
            
            # If this entity starts after the last one ended, it's a new top-level block
            if start > last_end:
                merged.append(ent)
                last_end = end
                
        # Reconstruct file with masking
        current_line_idx = 0 # 0-based
        ent_idx = 0
        
        while current_line_idx < len(lines):
            # Check if we reached the start of a maskable entity
            if ent_idx < len(merged):
                next_ent = merged[ent_idx]
                ent_start_idx = next_ent.start_line - 1 # 0-based
                ent_end_idx = next_ent.end_line - 1     # 0-based
                
                if current_line_idx == ent_start_idx:
                    # Keep the signature/first line
                    output.append(lines[current_line_idx])
                    output.append("    ... # Body masked")
                    
                    # Skip to end of entity
                    current_line_idx = ent_end_idx + 1
                    ent_idx += 1
                    continue
            
            # Keep normal lines (imports, globals, whitespace)
            output.append(lines[current_line_idx])
            current_line_idx += 1
            
        return "\n".join(output)

    @staticmethod
    def create_class_skeleton(class_obj: Any, methods: List[Any]) -> str:
        """
        Create a class skeleton: Class Docstring + __init__ (full) + Others (signature only).
        """
        text = f"class {class_obj.name}:\n"
        if class_obj.docstring:
            text += f'    """{class_obj.docstring}"""\n'
            
        for m in methods:
            if m.name == "__init__":
                # Keep full body for __init__ to capture properties
                # Note: m.body usually includes the signature in tree-sitter extraction
                text += getattr(m, 'body', '') + "\n"
            else:
                # Signature only for others
                text += f"    {m.signature}\n"
                text += "        ... # Body masked\n"
        
        return text

        self.language_detector = LanguageDetector(self.parser_factory)
        self.embedder = CodeEmbedder(model_name)
        self.graph_store = GraphStore(neo4j_uri, neo4j_user, neo4j_password)
        self.vector_store = VectorStore()
        self.index_dir = Path(index_dir)
        self.llm_service = LLMService()
        
        supported_langs = self.parser_factory.get_supported_languages()
        logger.info(f"RepositoryIndexer initialized with support for: {', '.join(supported_langs)}")
    
    def _get_commit_sha(self, repo_path: str) -> str:
        """Get current commit SHA from repository"""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Could not get commit SHA: {e}")
        
        # Fallback: use timestamp
        return f"unknown_{int(time.time())}"
    
    def _collect_source_files(self, repo_path: str) -> List[Path]:
        """Collect all supported source files in repository"""
        import os
        repo_path_obj = Path(repo_path)
        source_files = []
        
        # Exclude common directories
        exclude_dirs = {'.git', '__pycache__', 'venv', 'env', '.venv', 'node_modules', 'build', 'dist', 'target', '.idea', 'out'}
        
        # Get supported extensions
        supported_extensions = self.parser_factory.get_supported_extensions()
        
        # Walk through repository
        for root, dirs, files in os.walk(repo_path_obj):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = Path(root) / file
                # Check if file has supported extension
                if any(file.endswith(ext) for ext in supported_extensions):
                    source_files.append(file_path)
        
        logger.info(f"Found {len(source_files)} source files")
        return source_files
    
    def _generate_id(self, *parts: str) -> str:
        """Generate unique ID from parts"""
        combined = ":".join(str(p) for p in parts)
        return hashlib.md5(combined.encode()).hexdigest()[:16]



    def index_repository(self, repo_path: str, repo_name: str) -> IndexResult:
        """
        Index a complete repository
        
        Args:
            repo_path: Path to repository root
            repo_name: Repository name (e.g., "owner/repo")
            
        Returns:
            IndexResult with statistics
        """
        start_time = time.time()
        logger.info(f"Starting indexing for repository: {repo_name}")
        
        # Get commit SHA
        commit_sha = self._get_commit_sha(repo_path)
        logger.info(f"Commit SHA: {commit_sha}")
        
        # Collect all supported source files
        python_files = self._collect_source_files(repo_path)
        if not python_files:
            logger.warning("No supported source files found")
            return IndexResult(
                repo_name=repo_name,
                commit_sha=commit_sha,
                total_files=0,
                total_functions=0,
                index_path="",
                metadata_path="",
                graph_nodes=0,
                graph_edges=0,
                indexing_time_seconds=time.time() - start_time,
                failed_files=[]
            )
        
        # Connect to graph database
        if not self.graph_store.connect():
            raise ConnectionError("Failed to connect to Neo4j")
        
        # Clear existing data for this repo
        self.graph_store.clear_database(repo_name)
        
        # Load embedding model
        self.embedder.load_model()
        
        # Create vector store
        self.vector_store.create_index()
        
        # Parse all files and extract information
        all_functions = []
        all_classes = []
        file_info_map = {}
        failed_files = []
        
        repo_path_obj = Path(repo_path)
        
        for py_file in python_files:
            try:
                # Detect language
                language = self.language_detector.detect_language(str(py_file))
                if language is None:
                    logger.debug(f"Skipping unsupported file: {py_file}")
                    continue
                
                # Get appropriate parser
                parser = self.parser_factory.get_parser(str(py_file))
                if parser is None:
                    logger.warning(f"No parser available for {py_file}")
                    failed_files.append(str(py_file))
                    continue
                
                # Parse file
                tree = parser.parse_file(str(py_file))
                if tree is None:
                    failed_files.append(str(py_file))
                    continue
                
                # Read source code
                with open(py_file, 'rb') as f:
                    source_code = f.read()
                
                # Extract functions
                functions = parser.extract_functions(tree, source_code, str(py_file))
                
                # Extract classes
                classes = parser.extract_classes(tree, source_code, str(py_file))
                
                # Extract imports and calls
                imports = parser.extract_imports(tree, source_code)
                calls = parser.extract_calls(tree, source_code)
                
                # Get relative path
                rel_path = py_file.relative_to(repo_path_obj).as_posix()
                
                # Store file info
                file_id = self._generate_id(repo_name, rel_path)
                file_info_map[rel_path] = {
                    'id': file_id,
                    'path': rel_path,
                    'functions': functions,
                    'classes': classes,
                    'imports': imports,
                    'calls': calls,
                    'language': language
                }
                
                all_functions.extend(functions)
                all_classes.extend(classes)
                
            except Exception as e:
                logger.error(f"Failed to process {py_file}: {e}")
                failed_files.append(str(py_file))
        
        logger.info(f"Parsed {len(python_files) - len(failed_files)} files successfully")
        logger.info(f"Found {len(all_functions)} functions and {len(all_classes)} classes")
        
        # Generate embeddings for all functions
        logger.info("Generating embeddings...")
        function_texts = []
        function_metadata = []
        
        for func in all_functions:
            # Prepare text for embedding
            text = f"{func.signature}\n"
            if func.docstring:
                text += f"{func.docstring}\n"
            text += func.body
            function_texts.append(text)
            
            # Prepare metadata
            # Find which file this function belongs to
            func_file_path = None
            for file_path, file_info in file_info_map.items():
                if func in file_info['functions']:
                    func_file_path = file_path
                    break
            
            function_metadata.append({
                'id': self._generate_id(repo_name, func_file_path or "", func.name, str(func.start_line)),
                'entity_type': 'function',
                'name': func.name,
                'file_path': func_file_path or "",
                'class_name': func.class_name,
                'start_line': func.start_line,
                'end_line': func.end_line,
                'signature': func.signature,
                'docstring': func.docstring,
                'language': func.language
            })
        
        
        # --- Generate embeddings for Classes ---
        class_texts = []
        class_metadata = []
        
        for cls in all_classes:
            # Prepare text for embedding: Skeleton (Docstring + __init__ + Signatures)
            methods_in_class = [f for f in all_functions if f.class_name == cls.name]
            text = self.create_class_skeleton(cls, methods_in_class)
            
            class_texts.append(text)
            
            # Find file path
            cls_file_path = None
            for file_path, file_info in file_info_map.items():
                if cls in file_info['classes']:
                    cls_file_path = file_path
                    break

            class_metadata.append({
                'id': self._generate_id(repo_name, cls_file_path or "", cls.name),
                'entity_type': 'class',
                'name': cls.name,
                'file_path': cls_file_path or "",
                'start_line': cls.start_line,
                'end_line': cls.end_line,
                'docstring': cls.docstring,
                'language': cls.language
            })
            
        # --- Generate embeddings for Files ---
        file_texts = []
        file_metadata = []
        
        for file_path, file_info in file_info_map.items():
            # Use skeleton for embedding (Imports + Globals + Signatures)
            full_path = repo_path_obj / file_path
            try:
                # We need source code again. Optimization: Store it in file_info?
                # For now read again or pass it if available.
                # In parse loop we read it. Let's read again for simplicity or better, store it.
                # Reading again is safer for memory if repos are huge, but slightly slower.
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()
                
                text = self.create_file_skeleton(
                    source_code, 
                    file_info['functions'], 
                    file_info['classes']
                )
                
                # Prepend basic metadata
                header = f"File: {file_path}\n"
                text = header + text
            except Exception as e:
                logger.warning(f"Failed to read file for embedding {file_path}: {e}")
                # Fallback to simple listing if skeleton fails
                text = f"File: {file_path}\n"
                if file_info['imports']:
                    text += "Imports:\n" + "\n".join(file_info['imports']) + "\n"
                text += "Contents:\n"
                for c in file_info['classes']:
                    text += f"class {c.name}\n"
                for f in file_info['functions']:
                    if not f.class_name:
                        text += f"function {f.name}\n"
            
            file_texts.append(text)
            
            file_metadata.append({
                'id': file_info['id'],
                'entity_type': 'file',
                'name': str(file_path),
                'file_path': str(file_path),
                'language': file_info['language']
            })
        
        # Generate embeddings in batches
        # Generate embeddings in batches
        all_texts = function_texts + class_texts + file_texts
        all_metadata = function_metadata + class_metadata + file_metadata
        
        if all_texts:
            embeddings = self.embedder.embed_batch(all_texts, batch_size=32)
            self.vector_store.add_vectors(embeddings, all_metadata)
        
        # Save indices
        logger.info("Saving indices...")
        index_path = self.index_dir / repo_name.replace('/', '_') / "index.faiss"
        metadata_path = self.index_dir / repo_name.replace('/', '_') / "metadata.json"
        
        self.vector_store.save_index(str(index_path))
        self.vector_store.save_metadata(str(metadata_path))
        
        # Build graph
        logger.info("Building code knowledge graph...")
        self._build_graph(repo_name, commit_sha, file_info_map)
        
        # Get graph stats
        graph_stats = self.graph_store.get_stats(repo_name)
        
        # Close connections
        self.graph_store.close()
        
        elapsed_time = time.time() - start_time
        logger.info(f"Indexing completed in {elapsed_time:.2f} seconds")
        
        return IndexResult(
            repo_name=repo_name,
            commit_sha=commit_sha,
            total_files=len(python_files) - len(failed_files),
            total_functions=len(all_functions),
            index_path=str(index_path),
            metadata_path=str(metadata_path),
            graph_nodes=graph_stats['files'] + graph_stats['classes'] + graph_stats['functions'],
            graph_edges=graph_stats['relationships'],
            indexing_time_seconds=elapsed_time,
            failed_files=failed_files
        )
    
    def _build_graph(self, repo_name: str, commit_sha: str, file_info_map: Dict[str, Any]):
        """Build the code knowledge graph"""
        # Create file nodes
        for file_path, file_info in file_info_map.items():
            file_id = file_info['id']
            self.graph_store.create_file_node(
                file_id=file_id,
                repo=repo_name,
                path=file_path,
                language="python",
                lines_of_code=len(file_info['functions']) * 20,  # Rough estimate
                commit_sha=commit_sha
            )
        
        # Create class and function nodes
        for file_path, file_info in file_info_map.items():
            file_id = file_info['id']
            
            # Create class nodes
            for cls in file_info['classes']:
                class_id = self._generate_id(repo_name, file_path, cls.name)
                self.graph_store.create_class_node(
                    class_id=class_id,
                    name=cls.name,
                    file_id=file_id,
                    start_line=cls.start_line,
                    end_line=cls.end_line,
                    repo=repo_name,
                    language=cls.language,
                    class_type=cls.class_type
                )
                # Create CONTAINS relationship
                self.graph_store.create_contains_relationship(file_id, class_id)
            
            # Create function nodes
            for func in file_info['functions']:
                func_id = self._generate_id(repo_name, file_path, func.name, str(func.start_line))
                
                # Find class_id if function is in a class
                class_id = None
                if func.class_name:
                    class_id = self._generate_id(repo_name, file_path, func.class_name)
                
                self.graph_store.create_function_node(
                    function_id=func_id,
                    name=func.name,
                    file_id=file_id,
                    class_id=class_id,
                    start_line=func.start_line,
                    end_line=func.end_line,
                    signature=func.signature,
                    docstring=func.docstring,
                    repo=repo_name,
                    language=func.language
                )
                
                # Create CONTAINS relationship
                if class_id:
                    self.graph_store.create_contains_relationship(class_id, func_id)
                else:
                    self.graph_store.create_contains_relationship(file_id, func_id)
            
            # Create helper map for function start lines in this file
            # Map: (class_name or None, func_name) -> start_line
            # This allows distinguishing MyClass.method vs global_func
            # Note: func.class_name is None for global functions
            local_func_map = {}
            for func in file_info['functions']:
                key = (func.class_name, func.name)
                local_func_map[key] = str(func.start_line)

            # Create CALLS relationships with Scoped Resolution
            calls_map = file_info['calls'] # Dict[caller_name, List[CallInfo]]
            
            # Find the caller function info to get its scope (class name)
            # We need to map caller_name back to FunctionInfo to know if it's inside a class
            # because 'caller_name' key in calls_map is just the function name (might be ambiguous if same name in class vs global)
            # But the parser traverse logic makes keys unique per definition scope?
            # Actually python_parser traverse: calls_map keyed by simple func_name.
            # If we have class A: def foo... and class B: def foo... 
            # Both populate calls_map['foo']? NO! calls_map is per file.
            # If python_parser uses simple name, and there are duplicates, we have a collision problem in the parser return format.
            # Assuming unique names or handled by parser for now (Parser needs improvement for duplicate names, but let's proceed)
            
            for caller_name, call_infos in calls_map.items():
                
                # Identify the caller(s) with this name in current file
                # There might be multiple (e.g. in different classes)
                # We'll try to link all of them for now as we don't have deeper context in the calls_map key
                potential_callers = [f for f in file_info['functions'] if f.name == caller_name]
                
                for caller_func in potential_callers:
                    caller_id = self._generate_id(repo_name, file_path, caller_func.name, str(caller_func.start_line))
                    
                    for call in call_infos:
                        # Attempt to resolve the target
                        target_id = self._resolve_call_target(
                            repo_name, call, file_path, file_info, file_info_map, caller_func
                        )
                        
                        if target_id:
                            self.graph_store.create_call_by_id(caller_id, target_id)
    
    def _resolve_call_target(self, repo_name: str, call: Any, current_file_path: str, 
                           current_file_info: Dict, all_files_map: Dict, caller_func: Any) -> Optional[str]:
        """
        Resolve a function call to a specific Function ID.
        Returns ID if resolved, None otherwise.
        """
        # Case 1: Method call on 'self' (Internal Class Method)
        if call.scope == 'self' and caller_func.class_name:
            # Look for function 'call.name' in the same class 'caller_func.class_name'
            # In the same file
            for func in current_file_info['functions']:
                if func.name == call.name and func.class_name == caller_func.class_name:
                    return self._generate_id(repo_name, current_file_path, func.name, str(func.start_line))
        
        # Case 2: Local Scope (No scope provided)
        if not call.scope:
            # 2a. Look for function in the same class (implicit self? No, explicit in Python. explicit in Java)
            # Python requires self.foo(), so no scope foo() is usually global or imported global.
            # Java foo() is this.foo().
            
            # If Java and inside class:
            if caller_func.language == 'java' and caller_func.class_name:
                 for func in current_file_info['functions']:
                    if func.name == call.name and func.class_name == caller_func.class_name:
                        return self._generate_id(repo_name, current_file_path, func.name, str(func.start_line))

            # 2b. Look for Global function in current file
            for func in current_file_info['functions']:
                if func.name == call.name and not func.class_name:
                    return self._generate_id(repo_name, current_file_path, func.name, str(func.start_line))
            
            # 2c. Check "From Imports": from module import func
            for imp in current_file_info['imports']:
                # ImportInfo: module_name, alias, imported_elements
                # If we have 'from X import func' (alias handle?)
                if imp.imported_elements and call.name in imp.imported_elements:
                    # Found imported function. Resolve module X.
                    target_file = self._find_file_for_module(imp.module_name, all_files_map)
                    if target_file:
                        # Look for global func 'call.name' in target_file
                        target_info = all_files_map.get(target_file)
                        if target_info:
                            for func in target_info['functions']:
                                if func.name == call.name: # and is global? or class init?
                                    return self._generate_id(repo_name, target_file, func.name, str(func.start_line))

        # Case 3: External Scope (obj.method or alias.func)
        if call.scope:
            # Check if scope matches an import alias or module name
            # import numpy as np -> scope 'np'
            # import utils -> scope 'utils'
            resolved_module = None
            
            for imp in current_file_info['imports']:
                if imp.alias == call.scope:
                    resolved_module = imp.module_name
                    break
                if imp.module_name == call.scope: # and not imp.alias?
                     resolved_module = imp.module_name
                     break
            
            if resolved_module:
                target_file = self._find_file_for_module(resolved_module, all_files_map)
                if target_file and target_file in all_files_map:
                    target_info = all_files_map[target_file]
                    # Look for function 'call.name' in target_file
                    for func in target_info['functions']:
                        if func.name == call.name:
                             return self._generate_id(repo_name, target_file, func.name, str(func.start_line))
        
        return None

    def _find_file_for_module(self, module_name: str, all_files_map: Dict) -> Optional[str]:
        """
        Simple heuristic to map module name to file path.
        'utils' -> ends with 'utils.py'
        'pkg.mod' -> ends with 'pkg/mod.py'
        """
        if not module_name: return None
        
        # Normalize module name to path suffix
        path_suffix = module_name.replace('.', '/') + '.py'
        path_suffix_java = module_name.replace('.', '/') + '.java'
        
        # Search in all files
        # Prioritize exact match or suffix match
        # TODO: optimize this with a pre-built index if slow
        for file_path in all_files_map.keys():
            if file_path.endswith(path_suffix) or file_path.endswith(path_suffix_java):
                return file_path
        
        return None


    def get_index_status(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """
        Check if repository is indexed and get metadata
        
        Args:
            repo_name: Repository name
            
        Returns:
            Dictionary with index status or None if not indexed
        """
        index_path = self.index_dir / repo_name.replace('/', '_') / "index.faiss"
        metadata_path = self.index_dir / repo_name.replace('/', '_') / "metadata.json"
        
        if not index_path.exists() or not metadata_path.exists():
            return None
        
        try:
            # Load metadata to get info
            import json
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            return {
                'indexed': True,
                'index_path': str(index_path),
                'metadata_path': str(metadata_path),
                'total_functions': len(metadata),
                'last_modified': index_path.stat().st_mtime
            }
        except Exception as e:
            logger.error(f"Failed to get index status: {e}")
            return None
