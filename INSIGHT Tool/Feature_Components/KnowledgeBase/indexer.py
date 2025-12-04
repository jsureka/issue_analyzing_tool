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
    
    def __init__(self, model_name: str = "microsoft/unixcoder-base",
                 neo4j_uri: str = "bolt://localhost:7687",
                 neo4j_user: str = "neo4j",
                 neo4j_password: str = "password",
                 index_dir: str = "Data_Storage/KnowledgeBase"):
        """
        Initialize repository indexer
        
        Args:
            model_name: Embedding model name
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            index_dir: Directory to store indices
        """
        self.parser_factory = ParserFactory()
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
                'name': func.name,
                'file_path': func_file_path or "",
                'class_name': func.class_name,
                'start_line': func.start_line,
                'end_line': func.end_line,
                'signature': func.signature,
                'docstring': func.docstring,
                'language': func.language
            })
        
        # Generate embeddings in batches
        if function_texts:
            embeddings = self.embedder.embed_batch(function_texts, batch_size=32)
            self.vector_store.add_vectors(embeddings, function_metadata)
        
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
            
            # Create helper map for function start lines
            func_start_lines = {f.name: str(f.start_line) for f in file_info['functions']}

            # Create CALLS relationships
            calls_map = file_info['calls']
            for caller_name, callees in calls_map.items():
                if caller_name in func_start_lines:
                    start_line = func_start_lines[caller_name]
                    caller_id = self._generate_id(repo_name, file_path, caller_name, start_line)
                    for callee_name in callees:
                        self.graph_store.create_calls_relationship(caller_id, callee_name)


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
