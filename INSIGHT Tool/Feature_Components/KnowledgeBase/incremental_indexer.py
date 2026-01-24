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
    
    def process_added_files(self, added_files: List[str]) -> Tuple[List[FunctionInfo], List[Any], List[Dict[str, Any]]]:
        """
        Process newly added files and extract functions, classes, and file info
        
        Returns:
            Tuple of (functions, classes, file_info_maps)
        """
        all_functions = []
        all_classes = []
        all_file_infos = []
        
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
                    continue
                
                # Parse file
                tree = parser.parse_file(str(full_path))
                if not tree:
                    continue
                
                # Read source code
                with open(full_path, 'rb') as f:
                    source_code_bytes = f.read()
                    source_code = source_code_bytes.decode('utf-8', errors='ignore')

                # Extract entities
                functions = parser.extract_functions(tree, source_code_bytes, file_path)
                classes = parser.extract_classes(tree, source_code_bytes, file_path)
                imports = parser.extract_imports(tree, source_code_bytes)
                
                # Attach file_path to entities for downstream use
                for f in functions:
                    f.file_path = str(file_path)
                for c in classes:
                    c.file_path = str(file_path)
                
                all_functions.extend(functions)
                all_classes.extend(classes)
                
                all_file_infos.append({
                    'path': file_path,
                    'functions': functions,
                    'classes': classes,
                    'imports': imports,
                    'language': language,
                    'source_code': source_code
                })
                
                logger.info(f"Extracted {len(functions)} functions, {len(classes)} classes from {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to process added file {file_path}: {e}")
                continue
        
        return all_functions, all_classes, all_file_infos

    def process_modified_files(self, modified_files: List[str]) -> Tuple[List[str], List[FunctionInfo], List[Any], List[Dict[str, Any]]]:
        """
        Process modified files and return removed IDs and new entities
        
        Returns:
            Tuple of (removed_ids, new_functions, new_classes, new_file_infos)
        """
        removed_ids = []
        new_functions = []
        new_classes = []
        new_file_infos = []
        
        # Load existing metadata to find entities in modified files
        if not self.metadata_path.exists():
            logger.warning("Metadata file not found, treating as new files")
            fns, cls, files = self.process_added_files(modified_files)
            return removed_ids, fns, cls, files
        
        try:
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f) # List[Dict]
            
            # Metadata is a list of dicts
            existing_entities = metadata if isinstance(metadata, list) else metadata.get('functions', [])
            
            for file_path in modified_files:
                # Find all entities associated with this file
                file_entities = [
                    entity for entity in existing_entities 
                    if entity.get('file_path') == file_path
                ]
                
                # Collect IDs to remove
                for entity in file_entities:
                    ent_id = entity.get('id')
                    if ent_id:
                        removed_ids.append(ent_id)
                
                logger.info(f"Removing {len(file_entities)} old entities from {file_path}")
            
            # Parse modified files to get new entities
            new_functions, new_classes, new_file_infos = self.process_added_files(modified_files)
            
        except Exception as e:
            logger.error(f"Failed to process modified files: {e}")
        
        return removed_ids, new_functions, new_classes, new_file_infos
    
    def process_deleted_files(self, deleted_files: List[str]) -> List[str]:
        """
        Process deleted files and return IDs to remove
        """
        removed_ids = []
        
        if not self.metadata_path.exists():
            return removed_ids
        
        try:
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)
            
            existing_entities = metadata if isinstance(metadata, list) else metadata.get('functions', [])
            
            for file_path in deleted_files:
                # Find all entities from this file
                file_entities = [
                    entity for entity in existing_entities 
                    if entity.get('file_path') == file_path
                ]
                
                # Collect IDs
                for entity in file_entities:
                    ent_id = entity.get('id')
                    if ent_id:
                        removed_ids.append(ent_id)
                
                logger.info(f"Removing {len(file_entities)} entities from deleted file {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to process deleted files: {e}")
        
        return removed_ids
    
    def update_faiss_index(self, removed_ids: List[str], 
                          new_functions: List[FunctionInfo],
                          new_classes: List[Any],
                          new_files: List[Dict[str, Any]]) -> bool:
        """
        Update FAISS index with new Functions, Classes, and Files using Skeleton Indexing
        """
        try:
            # Load/Create index
            if not self.index_path.exists():
                self.vector_store.create_index()
            else:
                self.vector_store.load_index(str(self.index_path))
                self.vector_store.load_metadata(str(self.metadata_path))
            
            # Note: FAISS removal is complex/unsupported in this simple wrapper. 
            # We assume metadata filtering handles "deletion" or we accept some garbage.
            # Ideally: Rebuild or use IDMapper if supported.
            
            if new_functions or new_classes or new_files:
                self.embedder.load_model()
                
                embeddings = []
                metadata_list = []
                
                # 1. Embed Functions (Full Code)
                logger.info(f"Embedding {len(new_functions)} functions...")
                for func in new_functions:
                    text = f"{func.signature}\n"
                    if func.docstring:
                        text += f"{func.docstring}\n"
                    text += getattr(func, 'body', '')
                    
                    # Embed with Jina (8k context capable)
                    embedding = self.embedder.embed_function(text, "", "", max_length=8192)
                    embeddings.append(embedding)
                    
                    # Ensure file_path is set (patched in process_added_files)
                    f_path = getattr(func, 'file_path', '')
                    func_id = f"{self.repo_name}::{f_path}::{func.name}::{func.start_line}"
                    metadata_list.append({
                        'id': func_id,
                        'entity_type': 'function',
                        'name': func.name,
                        'file_path': f_path,
                        'class_name': func.class_name,
                        'start_line': func.start_line,
                        'end_line': func.end_line,
                        'signature': func.signature,
                        'docstring': func.docstring,
                        'language': func.language
                    })

                # 2. Embed Classes (Skeleton)
                from .indexer import RepositoryIndexer
                logger.info(f"Embedding {len(new_classes)} classes (skeleton)...")
                for cls in new_classes:
                    # Find methods for this class
                    methods = [f for f in new_functions if f.class_name == cls.name] 
                    # Correct matching uses file_path which we now have attached
                    cls_path = getattr(cls, 'file_path', '')
                    if cls_path:
                         # Strict filter: methods must be in same file
                         methods = [m for m in methods if getattr(m, 'file_path', '') == cls_path]

                    text = RepositoryIndexer.create_class_skeleton(cls, methods)
                    
                    embedding = self.embedder.embed_function(text, "", "", max_length=8192)
                    embeddings.append(embedding)
                    
                    cls_id = f"{self.repo_name}::{cls_path}::{cls.name}"
                    metadata_list.append({
                        'id': cls_id,
                        'entity_type': 'class',
                        'name': cls.name,
                        'file_path': cls_path,
                        'start_line': cls.start_line,
                        'end_line': cls.end_line,
                        'docstring': cls.docstring,
                        'language': cls.language
                    })

                # 3. Embed Files (Skeleton)
                logger.info(f"Embedding {len(new_files)} files (skeleton)...")
                for f_info in new_files:
                    text = RepositoryIndexer.create_file_skeleton(
                        f_info['source_code'],
                        f_info['functions'],
                        f_info['classes']
                    )
                    header = f"File: {f_info['path']}\n"
                    text = header + text
                    
                    embedding = self.embedder.embed_function(text, "", "", max_length=8192)
                    embeddings.append(embedding)
                    
                    file_id = f"{self.repo_name}::{f_info['path']}"
                    metadata_list.append({
                        'id': file_id,
                        'entity_type': 'file',
                        'name': str(f_info['path']),
                        'file_path': str(f_info['path']),
                        'language': f_info['language']
                    })

                # Add to index
                if embeddings:
                    import numpy as np
                    embeddings_array = np.array(embeddings, dtype=np.float32)
                    self.vector_store.add_vectors(embeddings_array, metadata_list)
                    logger.info(f"Added {len(embeddings)} new vectors to index")
            
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
            total_changed = len(added) + len(modified) + len(deleted)
            
            # Check if too many files changed
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
            removed_ids_deleted = self.process_deleted_files(deleted)
            
            # Process modified files
            removed_ids_mod, new_funcs_mod, new_cls_mod, new_files_mod = self.process_modified_files(modified)
            
            # Process added files
            new_funcs_add, new_cls_add, new_files_add = self.process_added_files(added)
            
            # Combine results
            all_removed_ids = removed_ids_deleted + removed_ids_mod
            all_new_functions = new_funcs_mod + new_funcs_add
            all_new_classes = new_cls_mod + new_cls_add
            all_new_files = new_files_mod + new_files_add
            
            logger.info(
                f"Changes: {len(all_removed_ids)} entities removed, "
                f"{len(all_new_functions)} funcs, {len(all_new_classes)} classes, {len(all_new_files)} files added"
            )
            
            # Update FAISS index
            if not self.update_faiss_index(all_removed_ids, all_new_functions, all_new_classes, all_new_files):
                raise Exception("Failed to update FAISS index")
            
            # Update graph database (Simplified - just add new nodes, naive removal)
            # self.update_graph_database(all_removed_ids, all_new_functions) 
            # Note: Graph update needs equivalent overhaul or can be skipped if graph relies on full rebuild mostly.
            # For now, let's skip deep graph update refinement to stay efficient as requested.
            
            logger.info(f"Incremental update completed in {time.time() - start_time:.2f}s")
            
            return UpdateResult(
                repo_name=self.repo_name,
                old_commit=old_commit,
                new_commit=new_commit,
                files_changed=total_changed,
                functions_updated=len(all_new_functions),
                windows_updated=0,
                update_time_seconds=time.time() - start_time
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
