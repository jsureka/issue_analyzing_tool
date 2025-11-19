"""
Incremental Indexer - Efficiently updates indices when code changes
"""

import logging
import subprocess
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional
from dataclasses import dataclass

from .parser_factory import ParserFactory, LanguageDetector
from .embedder import CodeEmbedder
from .vector_store import VectorStore
from .graph_store import GraphStore
from .language_parser import FunctionInfo

logger = logging.getLogger(__name__)


@dataclass
class UpdateResult:
    """Result of incremental index update"""
    repo_name: str
    old_commit: str
    new_commit: str
    files_changed: int
    functions_updated: int
    windows_updated: int
    update_time_seconds: float
    success: bool = True
    error_msg: str = ""


class IncrementalIndexer:
    """Handles incremental repository indexing based on git diffs"""
    
    def __init__(self, repo_path: str, repo_name: str = None, 
                 model_name: str = "microsoft/unixcoder-base",
                 neo4j_uri: str = "bolt://localhost:7687",
                 neo4j_user: str = "neo4j",
                 neo4j_password: str = "password"):
        """
        Initialize incremental indexer
        
        Args:
            repo_path: Path to git repository
            repo_name: Repository name (e.g., "owner/repo")
            model_name: Embedding model name
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.repo_path = Path(repo_path)
        self.repo_name = repo_name or self.repo_path.name
        
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        # Initialize components
        self.parser_factory = ParserFactory()
        self.language_detector = LanguageDetector(self.parser_factory)
        self.embedder = CodeEmbedder(model_name)
        self.vector_store = VectorStore()
        self.graph_store = GraphStore(neo4j_uri, neo4j_user, neo4j_password)
        
        # Index paths
        self.index_dir = Path("indices")
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        safe_repo_name = self.repo_name.replace('/', '_')
        self.index_path = self.index_dir / f"{safe_repo_name}.index"
        self.metadata_path = self.index_dir / f"{safe_repo_name}_metadata.json"
        
        logger.info(f"IncrementalIndexer initialized for {repo_path}")
    
    def get_changed_files(self, old_commit: str, new_commit: str) -> Tuple[List[str], List[str], List[str]]:
        """
        Get files changed between two commits using git diff
        
        Args:
            old_commit: Old commit SHA
            new_commit: New commit SHA
            
        Returns:
            Tuple of (added_files, modified_files, deleted_files)
        """
        try:
            # Run git diff to get changed files
            result = subprocess.run(
                ['git', 'diff', '--name-status', old_commit, new_commit],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Git diff failed: {result.stderr}")
                return [], [], []
            
            # Parse output
            added_files = []
            modified_files = []
            deleted_files = []
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split('\t')
                if len(parts) < 2:
                    continue
                
                status = parts[0]
                file_path = parts[1]
                
                # Only track Python files
                if not file_path.endswith('.py'):
                    continue
                
                if status == 'A':
                    added_files.append(file_path)
                elif status == 'M':
                    modified_files.append(file_path)
                elif status == 'D':
                    deleted_files.append(file_path)
                elif status.startswith('R'):  # Renamed
                    # Treat as modified
                    if len(parts) >= 3:
                        modified_files.append(parts[2])
            
            logger.info(f"Changed files: {len(added_files)} added, {len(modified_files)} modified, {len(deleted_files)} deleted")
            return added_files, modified_files, deleted_files
            
        except subprocess.TimeoutExpired:
            logger.error("Git diff timed out")
            return [], [], []
        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            return [], [], []
    
    def process_added_files(self, added_files: List[str]) -> List[FunctionInfo]:
        """
        Process newly added files and extract functions
        
        Args:
            added_files: List of added file paths
            
        Returns:
            List of FunctionInfo objects
        """
        all_functions = []
        
        for file_path in added_files:
            try:
                full_path = self.repo_path / file_path
                
                if not full_path.exists():
                    logger.warning(f"Added file not found: {file_path}")
                    continue
                
                # Detect language
                language = self.language_detector.detect_language(str(full_path))
                if not language:
                    logger.debug(f"Unsupported file type: {file_path}")
                    continue
                
                # Get parser
                parser = self.parser_factory.get_parser(str(full_path))
                if not parser:
                    logger.warning(f"No parser available for: {file_path}")
                    continue
                
                # Parse file
                tree = parser.parse_file(str(full_path))
                if not tree:
                    logger.warning(f"Failed to parse: {file_path}")
                    continue
                
                # Extract functions
                with open(full_path, 'rb') as f:
                    source_code = f.read()
                
                functions = parser.extract_functions(tree, source_code, file_path)
                
                logger.info(f"Extracted {len(functions)} functions from {file_path}")
                all_functions.extend(functions)
                
            except Exception as e:
                logger.error(f"Failed to process added file {file_path}: {e}")
                continue
        
        return all_functions
    
    def process_modified_files(self, modified_files: List[str]) -> Tuple[List[str], List[FunctionInfo]]:
        """
        Process modified files and return removed function IDs and new functions
        
        Args:
            modified_files: List of modified file paths
            
        Returns:
            Tuple of (removed_function_ids, new_functions)
        """
        removed_function_ids = []
        new_functions = []
        
        # Load existing metadata to find functions in modified files
        if not self.metadata_path.exists():
            logger.warning("Metadata file not found, treating as new files")
            new_functions = self.process_added_files(modified_files)
            return removed_function_ids, new_functions
        
        try:
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)
            
            existing_functions = metadata.get('functions', [])
            
            for file_path in modified_files:
                # Find all functions from this file in existing metadata
                file_functions = [
                    func for func in existing_functions 
                    if func.get('file_path') == file_path
                ]
                
                # Collect function IDs to remove
                for func in file_functions:
                    func_id = func.get('id')
                    if func_id:
                        removed_function_ids.append(func_id)
                
                logger.info(f"Removing {len(file_functions)} old functions from {file_path}")
            
            # Parse modified files to get new functions
            new_functions = self.process_added_files(modified_files)
            
        except Exception as e:
            logger.error(f"Failed to process modified files: {e}")
        
        return removed_function_ids, new_functions
    
    def process_deleted_files(self, deleted_files: List[str]) -> List[str]:
        """
        Process deleted files and return function IDs to remove
        
        Args:
            deleted_files: List of deleted file paths
            
        Returns:
            List of function IDs to remove
        """
        removed_function_ids = []
        
        # Load existing metadata
        if not self.metadata_path.exists():
            logger.warning("Metadata file not found")
            return removed_function_ids
        
        try:
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)
            
            existing_functions = metadata.get('functions', [])
            
            for file_path in deleted_files:
                # Find all functions from this file
                file_functions = [
                    func for func in existing_functions 
                    if func.get('file_path') == file_path
                ]
                
                # Collect all function IDs
                for func in file_functions:
                    func_id = func.get('id')
                    if func_id:
                        removed_function_ids.append(func_id)
                
                logger.info(f"Removing {len(file_functions)} functions from deleted file {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to process deleted files: {e}")
        
        return removed_function_ids
    
    def get_dependent_files(self, changed_files: List[str], graph_store=None) -> Set[str]:
        """
        Get files that depend on changed files (via imports)
        
        Args:
            changed_files: List of changed file paths
            graph_store: GraphStore instance for querying dependencies
            
        Returns:
            Set of dependent file paths
        """
        if not graph_store:
            logger.debug("No graph store provided, skipping dependency analysis")
            return set()
        
        try:
            dependent_files = set()
            
            for file_path in changed_files:
                # Query graph for files that import this file
                # This would require implementing a query in GraphStore
                # For now, return empty set
                pass
            
            logger.info(f"Found {len(dependent_files)} dependent files")
            return dependent_files
            
        except Exception as e:
            logger.error(f"Failed to get dependent files: {e}")
            return set()
    
    def classify_changes(self, added_files: List[str], modified_files: List[str], 
                        deleted_files: List[str]) -> Dict[str, List[str]]:
        """
        Classify file changes for processing
        
        Args:
            added_files: List of added files
            modified_files: List of modified files
            deleted_files: List of deleted files
            
        Returns:
            Dictionary with classified changes
        """
        return {
            'added': added_files,
            'modified': modified_files,
            'deleted': deleted_files,
            'to_reindex': added_files + modified_files,  # Files that need reindexing
            'to_remove': deleted_files  # Files to remove from index
        }
    
    def update_faiss_index(self, removed_function_ids: List[str], 
                          new_functions: List[FunctionInfo]) -> bool:
        """
        Update FAISS index by removing old vectors and adding new ones
        
        Args:
            removed_function_ids: List of function IDs to remove
            new_functions: List of new FunctionInfo objects to add
            
        Returns:
            True if successful
        """
        try:
            # Load existing index
            if not self.index_path.exists():
                logger.warning("Index file not found, creating new index")
                self.vector_store.create_index()
            else:
                self.vector_store.load_index(str(self.index_path))
                self.vector_store.load_metadata(str(self.metadata_path))
            
            # Note: FAISS doesn't support direct deletion, so we need to rebuild
            # For now, we'll mark removed functions in metadata and filter during search
            # A full rebuild would be needed for true deletion
            
            if new_functions:
                # Load embedder model
                self.embedder.load_model()
                
                # Generate embeddings for new functions
                logger.info(f"Generating embeddings for {len(new_functions)} functions")
                embeddings = []
                metadata_list = []
                
                for func in new_functions:
                    # Prepare embedding text
                    embedding_text = f"{func.signature}\n"
                    if func.docstring:
                        embedding_text += f"{func.docstring}\n"
                    
                    # Generate embedding
                    embedding = self.embedder.embed_function(
                        func.signature,
                        func.docstring,
                        "",  # We don't have full body in FunctionInfo
                        max_length=512
                    )
                    embeddings.append(embedding)
                    
                    # Create metadata
                    func_id = f"{self.repo_name}::{func.file_path}::{func.name}::{func.start_line}"
                    metadata_list.append({
                        'id': func_id,
                        'name': func.name,
                        'file_path': func.file_path,
                        'class_name': func.class_name,
                        'start_line': func.start_line,
                        'end_line': func.end_line,
                        'signature': func.signature,
                        'docstring': func.docstring,
                        'language': func.language
                    })
                
                # Add to index
                import numpy as np
                embeddings_array = np.array(embeddings, dtype=np.float32)
                self.vector_store.add_vectors(embeddings_array, metadata_list)
                
                logger.info(f"Added {len(new_functions)} new vectors to index")
            
            # Save updated index
            self.vector_store.save_index(str(self.index_path))
            self.vector_store.save_metadata(str(self.metadata_path))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update FAISS index: {e}", exc_info=True)
            return False
    
    def update_graph_database(self, removed_function_ids: List[str], 
                             new_functions: List[FunctionInfo]) -> bool:
        """
        Update Neo4j graph database
        
        Args:
            removed_function_ids: List of function IDs to remove
            new_functions: List of new FunctionInfo objects to add
            
        Returns:
            True if successful
        """
        try:
            # Connect to graph database
            if not self.graph_store.connect():
                logger.warning("Failed to connect to Neo4j, skipping graph update")
                return False
            
            # Remove old function nodes
            # Note: This is a simplified implementation
            # A full implementation would need proper node deletion queries
            logger.info(f"Would remove {len(removed_function_ids)} function nodes from graph")
            
            # Add new function nodes
            for func in new_functions:
                func_id = f"{self.repo_name}::{func.file_path}::{func.name}::{func.start_line}"
                file_id = f"{self.repo_name}::{func.file_path}"
                
                self.graph_store.create_function_node(
                    function_id=func_id,
                    name=func.name,
                    file_id=file_id,
                    class_id=None,  # Simplified - would need class tracking
                    start_line=func.start_line,
                    end_line=func.end_line,
                    signature=func.signature,
                    docstring=func.docstring,
                    repo=self.repo_name,
                    language=func.language
                )
            
            logger.info(f"Added {len(new_functions)} function nodes to graph")
            
            self.graph_store.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update graph database: {e}", exc_info=True)
            return False
    
    def update_metadata(self, new_commit: str, removed_function_ids: List[str],
                       new_functions: List[FunctionInfo], update_time: float) -> bool:
        """
        Update metadata file with new commit and statistics
        
        Args:
            new_commit: New commit SHA
            removed_function_ids: List of removed function IDs
            new_functions: List of new functions
            update_time: Time taken for update
            
        Returns:
            True if successful
        """
        try:
            # Load existing metadata
            if self.metadata_path.exists():
                with open(self.metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {
                    'repo_name': self.repo_name,
                    'functions': [],
                    'language_stats': {}
                }
            
            # Remove old functions
            metadata['functions'] = [
                func for func in metadata.get('functions', [])
                if func.get('id') not in removed_function_ids
            ]
            
            # Add new functions
            for func in new_functions:
                func_id = f"{self.repo_name}::{func.file_path}::{func.name}::{func.start_line}"
                metadata['functions'].append({
                    'id': func_id,
                    'name': func.name,
                    'file_path': func.file_path,
                    'class_name': func.class_name,
                    'start_line': func.start_line,
                    'end_line': func.end_line,
                    'signature': func.signature,
                    'docstring': func.docstring,
                    'language': func.language
                })
            
            # Update metadata fields
            metadata['commit_sha'] = new_commit
            metadata['last_updated'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            metadata['total_functions'] = len(metadata['functions'])
            
            # Update language statistics
            lang_stats = {}
            for func in metadata['functions']:
                lang = func.get('language', 'unknown')
                lang_stats[lang] = lang_stats.get(lang, 0) + 1
            metadata['language_stats'] = lang_stats
            
            # Add update history entry
            if 'update_history' not in metadata:
                metadata['update_history'] = []
            
            metadata['update_history'].append({
                'commit_sha': new_commit,
                'timestamp': metadata['last_updated'],
                'update_type': 'incremental',
                'functions_removed': len(removed_function_ids),
                'functions_added': len(new_functions),
                'update_time_seconds': update_time
            })
            
            # Keep only last 10 history entries
            metadata['update_history'] = metadata['update_history'][-10:]
            
            # Save metadata
            with open(self.metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Updated metadata: {metadata['total_functions']} total functions")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}", exc_info=True)
            return False
    
    def update_index(self, old_commit: str, new_commit: str) -> UpdateResult:
        """
        Incrementally update index from old to new commit
        
        Args:
            old_commit: Old commit SHA
            new_commit: New commit SHA
            
        Returns:
            UpdateResult with statistics
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting incremental update: {old_commit[:7]} → {new_commit[:7]}")
            
            # Get changed files
            added, modified, deleted = self.get_changed_files(old_commit, new_commit)
            
            if not added and not modified and not deleted:
                logger.info("No supported files changed")
                return UpdateResult(
                    repo_name=self.repo_name,
                    old_commit=old_commit,
                    new_commit=new_commit,
                    files_changed=0,
                    functions_updated=0,
                    windows_updated=0,
                    update_time_seconds=time.time() - start_time
                )
            
            # Classify changes
            changes = self.classify_changes(added, modified, deleted)
            total_changed = len(changes['to_reindex']) + len(changes['to_remove'])
            
            # Check if too many files changed (signal for full reindex)
            if total_changed > 50:
                logger.warning(f"Too many files changed ({total_changed}), signaling full reindex needed")
                return UpdateResult(
                    repo_name=self.repo_name,
                    old_commit=old_commit,
                    new_commit=new_commit,
                    files_changed=total_changed,
                    functions_updated=0,
                    windows_updated=0,
                    update_time_seconds=time.time() - start_time,
                    success=False,
                    error_msg=f"Too many files changed ({total_changed} > 50), full reindex recommended"
                )
            
            # Process deleted files
            removed_ids_from_deleted = self.process_deleted_files(deleted)
            
            # Process modified files
            removed_ids_from_modified, new_from_modified = self.process_modified_files(modified)
            
            # Process added files
            new_from_added = self.process_added_files(added)
            
            # Combine results
            all_removed_ids = removed_ids_from_deleted + removed_ids_from_modified
            all_new_functions = new_from_modified + new_from_added
            
            logger.info(
                f"Changes: {len(all_removed_ids)} functions removed, "
                f"{len(all_new_functions)} functions added"
            )
            
            # Update FAISS index
            if not self.update_faiss_index(all_removed_ids, all_new_functions):
                raise Exception("Failed to update FAISS index")
            
            # Update graph database
            self.update_graph_database(all_removed_ids, all_new_functions)
            
            # Update metadata
            update_time = time.time() - start_time
            if not self.update_metadata(new_commit, all_removed_ids, all_new_functions, update_time):
                raise Exception("Failed to update metadata")
            
            logger.info(f"Incremental update completed in {update_time:.2f}s")
            
            return UpdateResult(
                repo_name=self.repo_name,
                old_commit=old_commit,
                new_commit=new_commit,
                files_changed=total_changed,
                functions_updated=len(all_new_functions),
                windows_updated=0,  # Window updates not implemented yet
                update_time_seconds=update_time
            )
            
        except Exception as e:
            logger.error(f"Incremental update failed: {e}", exc_info=True)
            return UpdateResult(
                repo_name=self.repo_name,
                old_commit=old_commit,
                new_commit=new_commit,
                files_changed=0,
                functions_updated=0,
                windows_updated=0,
                update_time_seconds=time.time() - start_time,
                success=False,
                error_msg=str(e)
            )
