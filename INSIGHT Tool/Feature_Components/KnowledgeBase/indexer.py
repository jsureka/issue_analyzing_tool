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
from .vector_store import VectorStore, WindowVectorStore
from .window_generator import WindowGenerator
from .llm_service import LLMService

logger = logging.getLogger(__name__)


@dataclass
class IndexResult:
    """Result of repository indexing"""
    repo_name: str
    commit_sha: str
    total_files: int
    total_functions: int
    total_windows: int  # Added for Phase 3
    index_path: str
    metadata_path: str
    window_index_path: str  # Added for Phase 3
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
                total_windows=0,
                index_path="",
                metadata_path="",
                window_index_path="",
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
        
        # Create new vector index
        self.vector_store.create_index()
        
        # Load embedding model
        self.embedder.load_model()
        
        # Parse all files and extract functions
        all_functions = []
        all_classes = []
        file_map = {}  # file_path -> file_id
        failed_files = []
        
        repo_path_obj = Path(repo_path)
        
        # Track language statistics
        language_stats = {}
        
        for source_file in python_files:
            try:
                # Detect language
                language = self.language_detector.detect_language(str(source_file))
                if language is None:
                    logger.debug(f"Skipping unsupported file: {source_file}")
                    continue
                
                # Track statistics
                language_stats[language] = language_stats.get(language, 0) + 1
                
                # Get appropriate parser
                parser = self.parser_factory.get_parser(str(source_file))
                if parser is None:
                    logger.warning(f"No parser available for {source_file}")
                    failed_files.append(str(source_file))
                    continue
                
                # Parse file
                tree = parser.parse_file(str(source_file))
                if tree is None:
                    failed_files.append(str(source_file))
                    continue
                
                # Read source code
                with open(source_file, 'rb') as f:
                    source_code = f.read()
                
                # Get relative path
                rel_path = source_file.relative_to(repo_path_obj)
                
                # Create file node
                file_id = self._generate_id(repo_name, str(rel_path))
                file_map[str(rel_path)] = file_id
                
                # Count lines
                lines_of_code = len(source_code.decode('utf-8', errors='ignore').split('\n'))
                
                self.graph_store.create_file_node(
                    file_id=file_id,
                    repo=repo_name,
                    path=str(rel_path),
                    language=language,
                    lines_of_code=lines_of_code,
                    commit_sha=commit_sha
                )
                
                # Extract classes
                classes = parser.extract_classes(tree, source_code, str(source_file))
                for cls in classes:
                    class_id = self._generate_id(repo_name, str(rel_path), cls.name)
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
                    all_classes.append((cls, class_id, file_id, str(rel_path)))
                
                # Extract functions
                functions = parser.extract_functions(tree, source_code, str(source_file))
                for func in functions:
                    func_id = self._generate_id(repo_name, str(rel_path), func.name, str(func.start_line))
                    
                    # Find class_id if function is in a class
                    class_id = None
                    if func.class_name:
                        for cls, cid, _, _ in all_classes:
                            if cls.name == func.class_name:
                                class_id = cid
                                break
                    
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
                    
                    all_functions.append((func, func_id, file_id, str(rel_path)))
                
                # Extract calls and create relationships
                calls_map = parser.extract_calls(tree, source_code)
                for func_name, called_names in calls_map.items():
                    # Find function ID
                    caller_id = None
                    for func, fid, _, _ in all_functions:
                        if func.name == func_name:
                            caller_id = fid
                            break
                    
                    if caller_id:
                        for called_name in called_names:
                            self.graph_store.create_calls_relationship(caller_id, called_name)
                
            except Exception as e:
                logger.error(f"Failed to process file {source_file}: {e}")
                failed_files.append(str(source_file))
        
        logger.info(f"Indexed files by language: {language_stats}")
        
        logger.info(f"Parsed {len(python_files) - len(failed_files)} files successfully")
        logger.info(f"Extracted {len(all_functions)} functions")
        
        # Generate embeddings in batches
        logger.info("Generating embeddings...")
        function_texts = []
        function_metadata = []
        
        for func, func_id, file_id, rel_path in all_functions:
            # Prepare text for embedding
            text = f"{func.signature}\n"
            if func.docstring:
                text += f"{func.docstring}\n"
            text += func.body
            
            function_texts.append(text)
            function_metadata.append({
                'id': func_id,
                'name': func.name,
                'file_path': rel_path,
                'class_name': func.class_name,
                'start_line': func.start_line,
                'end_line': func.end_line,
                'signature': func.signature,
                'docstring': func.docstring,
                'language': func.language
            })
        
        if function_texts:
            embeddings = self.embedder.embed_batch(function_texts, batch_size=32)
            self.vector_store.add_vectors(embeddings, function_metadata)
        
        # Phase 3: Generate line windows and embeddings
        logger.info("Generating line windows for functions...")
        window_generator = WindowGenerator(
            tokenizer=self.embedder.tokenizer if hasattr(self.embedder, 'tokenizer') else None,
            window_size=48,
            stride=24
        )
        
        # Read file contents for window extraction
        file_contents = {}
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    relative_path = str(file_path.relative_to(repo_path))
                    file_contents[relative_path] = f.read()
            except Exception as e:
                logger.warning(f"Could not read file for windows: {file_path}: {e}")
        
        # Generate windows from all functions
        all_windows = window_generator.extract_windows_from_functions(function_metadata, file_contents)
        
        # Generate window embeddings
        window_vector_store = WindowVectorStore(dimension=768)
        window_vector_store.create_index()
        
        if all_windows:
            logger.info(f"Generating embeddings for {len(all_windows)} windows...")
            window_embeddings = self.embedder.embed_windows(all_windows, batch_size=64)
            window_vector_store.add_window_vectors(window_embeddings, all_windows)
        
        # Save vector stores
        self.index_dir.mkdir(parents=True, exist_ok=True)
        index_path = self.index_dir / f"{repo_name.replace('/', '_')}.index"
        metadata_path = self.index_dir / f"{repo_name.replace('/', '_')}_metadata.json"
        window_index_path = self.index_dir / f"{repo_name.replace('/', '_')}_windows.index"
        window_metadata_path = self.index_dir / f"{repo_name.replace('/', '_')}_windows_metadata.json"
        
        self.vector_store.save_index(str(index_path))
        self.vector_store.save_metadata(str(metadata_path))
        window_vector_store.save_index(str(window_index_path))
        window_vector_store.save_window_metadata(str(window_metadata_path))
        
        # Get graph stats
        graph_stats = self.graph_store.get_stats(repo_name)
        
        # Close graph connection
        self.graph_store.close()
        
        indexing_time = time.time() - start_time
        logger.info(f"Indexing completed in {indexing_time:.2f} seconds")
        
        return IndexResult(
            repo_name=repo_name,
            commit_sha=commit_sha,
            total_files=len(python_files) - len(failed_files),
            total_functions=len(all_functions),
            total_windows=len(all_windows),
            index_path=str(index_path),
            metadata_path=str(metadata_path),
            window_index_path=str(window_index_path),
            graph_nodes=graph_stats['files'] + graph_stats['classes'] + graph_stats['functions'],
            graph_edges=graph_stats['relationships'],
            indexing_time_seconds=indexing_time,
            failed_files=failed_files
        )

    def get_index_status(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """
        Check if repository is indexed and get metadata
        
        Args:
            repo_name: Repository name
            
        Returns:
            Dictionary with index status or None if not indexed
        """
        index_path = self.index_dir / f"{repo_name.replace('/', '_')}.index"
        metadata_path = self.index_dir / f"{repo_name.replace('/', '_')}_metadata.json"
        
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
                'index_size_mb': index_path.stat().st_size / (1024 * 1024)
            }
        except Exception as e:
            logger.error(f"Failed to get index status: {e}")
            return None

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
                total_windows=0,
                index_path="",
                metadata_path="",
                window_index_path="",
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
                'docstring': func.docstring
            })
        
        # Generate embeddings in batches
        if function_texts:
            embeddings = self.embedder.embed_batch(function_texts, batch_size=32)
            self.vector_store.add_vectors(embeddings, function_metadata)
        
        # Build graph
        logger.info("Building code knowledge graph...")
        self._build_graph(repo_name, commit_sha, file_info_map)
        
        # Save indices
        logger.info("Saving indices...")
        index_path = self.index_dir / repo_name.replace('/', '_') / "index.faiss"
        metadata_path = self.index_dir / repo_name.replace('/', '_') / "metadata.json"
        
        self.vector_store.save_index(str(index_path))
        self.vector_store.save_metadata(str(metadata_path))
        
        # Get graph stats
        graph_stats = self.graph_store.get_stats(repo_name)
        
        # Close connections
        self.graph_store.close()
        
        # Generate directory summaries (GraphRAG)
        logger.info("Generating directory summaries...")
        self._generate_directory_summaries(repo_name, file_info_map)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Indexing completed in {elapsed_time:.2f} seconds")
        
        return IndexResult(
            repo_name=repo_name,
            commit_sha=commit_sha,
            total_files=len(python_files) - len(failed_files),
            total_functions=len(all_functions),
            total_windows=0,  # Phase 3 not implemented in this path yet
            index_path=str(index_path),
            metadata_path=str(metadata_path),
            window_index_path="",  # Phase 3 not implemented in this path yet
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
            
            # Create CALLS relationships
            calls_map = file_info['calls']
            for caller_name, callees in calls_map.items():
                caller_id = self._generate_id(repo_name, file_path, caller_name, "")
                for callee_name in callees:
                    self.graph_store.create_calls_relationship(caller_id, callee_name)

    def _generate_directory_summaries(self, repo_name: str, file_info_map: Dict[str, Any]):
        """
        Generate summaries for directories (GraphRAG)
        """
        if not self.llm_service.is_available():
            logger.warning("LLM service unavailable, skipping directory summarization")
            return

        # Group files by directory
        dirs = {}
        for file_path, info in file_info_map.items():
            dir_path = str(Path(file_path).parent).replace('\\', '/')
            if dir_path == '.':
                dir_path = 'root'
            
            if dir_path not in dirs:
                dirs[dir_path] = []
            dirs[dir_path].append(info)
        
        # Generate summary for each directory
        for dir_path, files in dirs.items():
            try:
                # Create context for LLM
                context = f"Directory: {dir_path}\n\nFiles:\n"
                for f in files:
                    context += f"- {Path(f['path']).name}: "
                    # Add function signatures
                    funcs = [func.name for func in f['functions']]
                    if funcs:
                        context += f"Contains functions: {', '.join(funcs[:5])}..."
                    context += "\n"
                
                # Generate summary
                summary = self.llm_service.summarize_code(context, dir_path)
                
                # Create directory node
                dir_id = self._generate_id(repo_name, dir_path)
                self.graph_store.create_directory_node(dir_id, repo_name, dir_path, summary)
                
                # Link directory to files
                for f in files:
                    file_id = f['id']
                    # We reuse CONTAINS for Directory -> File
                    self.graph_store.create_contains_relationship(dir_id, file_id)
                    
                logger.info(f"Generated summary for directory: {dir_path}")
                
            except Exception as e:
                logger.error(f"Failed to summarize directory {dir_path}: {e}")

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
