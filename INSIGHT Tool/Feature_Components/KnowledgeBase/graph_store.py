"""
Neo4j graph storage for code knowledge graph
Stores files, classes, functions and their relationships
"""

import logging
from typing import Dict, List, Optional, Any
from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable, AuthError

logger = logging.getLogger(__name__)


class GraphStore:
    """Neo4j graph database manager for code knowledge graph"""
    
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 user: str = "neo4j", password: str = "password"):
        """
        Initialize Neo4j connection
        
        Args:
            uri: Neo4j connection URI
            user: Database username
            password: Database password
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Optional[Driver] = None
        
        logger.info(f"GraphStore initialized with URI: {uri}")
    
    def connect(self) -> bool:
        """
        Establish connection to Neo4j database
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Successfully connected to Neo4j")
            return True
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Neo4j: {e}")
            return False
    
    def close(self):
        """Close the Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def clear_database(self, repo_name: str):
        """
        Clear all nodes and relationships for a specific repository
        
        Args:
            repo_name: Repository name to clear
        """
        if not self.driver:
            logger.error("Not connected to Neo4j")
            return
        
        try:
            with self.driver.session() as session:
                # Delete all nodes and relationships for this repo
                query = """
                MATCH (n {repo: $repo_name})
                DETACH DELETE n
                """
                session.run(query, repo_name=repo_name)
                logger.info(f"Cleared database for repository: {repo_name}")
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
    
    def _ensure_connected(self):
        """Ensure database connection exists"""
        if not self.driver:
            if not self.connect():
                raise ConnectionError("Failed to connect to Neo4j database")

    def create_directory_node(self, dir_id: str, repo: str, path: str, summary: str = "") -> bool:
        """
        Create a directory node in the graph (GraphRAG Community)
        
        Args:
            dir_id: Unique directory identifier
            repo: Repository name
            path: Directory path relative to repo root
            summary: LLM-generated summary of the directory
            
        Returns:
            True if successful
        """
        self._ensure_connected()
        
        try:
            with self.driver.session() as session:
                query = """
                CREATE (d:Directory {
                    id: $dir_id,
                    repo: $repo,
                    path: $path,
                    summary: $summary
                })
                """
                session.run(query, dir_id=dir_id, repo=repo, path=path, summary=summary)
                return True
        except Exception as e:
            logger.error(f"Failed to create directory node: {e}")
            return False

    def create_file_node(self, file_id: str, repo: str, path: str, 
                        language: str, lines_of_code: int, commit_sha: str) -> bool:
        """
        Create a file node in the graph
        
        Args:
            file_id: Unique file identifier
            repo: Repository name
            path: File path relative to repo root
            language: Programming language
            lines_of_code: Number of lines in file
            commit_sha: Git commit SHA
            
        Returns:
            True if successful
        """
        self._ensure_connected()
        
        try:
            with self.driver.session() as session:
                query = """
                CREATE (f:File {
                    id: $file_id,
                    repo: $repo,
                    path: $path,
                    language: $language,
                    lines_of_code: $lines_of_code,
                    commit_sha: $commit_sha
                })
                """
                session.run(query, 
                           file_id=file_id, repo=repo, path=path,
                           language=language, lines_of_code=lines_of_code,
                           commit_sha=commit_sha)
                return True
        except Exception as e:
            logger.error(f"Failed to create file node: {e}")
            return False
    
    def create_class_node(self, class_id: str, name: str, file_id: str,
                         start_line: int, end_line: int, repo: str,
                         language: str = "python", class_type: str = "class") -> bool:
        """
        Create a class node in the graph
        
        Args:
            class_id: Unique class identifier
            name: Class name
            file_id: Parent file ID
            start_line: Starting line number
            end_line: Ending line number
            repo: Repository name
            language: Programming language (default: "python")
            class_type: Type of class (class, interface, enum)
            
        Returns:
            True if successful
        """
        self._ensure_connected()
        
        try:
            with self.driver.session() as session:
                query = """
                CREATE (c:Class {
                    id: $class_id,
                    name: $name,
                    file_id: $file_id,
                    start_line: $start_line,
                    end_line: $end_line,
                    repo: $repo,
                    language: $language,
                    class_type: $class_type
                })
                """
                session.run(query,
                           class_id=class_id, name=name, file_id=file_id,
                           start_line=start_line, end_line=end_line, repo=repo,
                           language=language, class_type=class_type)
                return True
        except Exception as e:
            logger.error(f"Failed to create class node: {e}")
            return False
    
    def create_function_node(self, function_id: str, name: str, file_id: str,
                           class_id: Optional[str], start_line: int, end_line: int,
                           signature: str, docstring: Optional[str], repo: str,
                           language: str = "python") -> bool:
        """
        Create a function node in the graph
        
        Args:
            function_id: Unique function identifier
            name: Function name
            file_id: Parent file ID
            class_id: Parent class ID (None if module-level)
            start_line: Starting line number
            end_line: Ending line number
            signature: Function signature
            docstring: Function docstring
            repo: Repository name
            language: Programming language (default: "python")
            
        Returns:
            True if successful
        """
        self._ensure_connected()
        
        try:
            with self.driver.session() as session:
                query = """
                CREATE (f:Function {
                    id: $function_id,
                    name: $name,
                    file_id: $file_id,
                    class_id: $class_id,
                    start_line: $start_line,
                    end_line: $end_line,
                    signature: $signature,
                    docstring: $docstring,
                    repo: $repo,
                    language: $language
                })
                """
                session.run(query,
                           function_id=function_id, name=name, file_id=file_id,
                           class_id=class_id, start_line=start_line, end_line=end_line,
                           signature=signature, docstring=docstring, repo=repo,
                           language=language)
                return True
        except Exception as e:
            logger.error(f"Failed to create function node: {e}")
            return False

    def create_contains_relationship(self, parent_id: str, child_id: str) -> bool:
        """
        Create a CONTAINS relationship between parent and child nodes
        
        Args:
            parent_id: Parent node ID (file or class)
            child_id: Child node ID (class or function)
            
        Returns:
            True if successful
        """
        self._ensure_connected()
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (parent {id: $parent_id})
                MATCH (child {id: $child_id})
                CREATE (parent)-[:CONTAINS]->(child)
                """
                session.run(query, parent_id=parent_id, child_id=child_id)
                return True
        except Exception as e:
            logger.error(f"Failed to create CONTAINS relationship: {e}")
            return False
    
    def create_calls_relationship(self, caller_id: str, callee_name: str) -> bool:
        """
        Create a CALLS relationship between functions
        
        Args:
            caller_id: Calling function ID
            callee_name: Called function name (may not have full ID)
            
        Returns:
            True if successful
        """
        self._ensure_connected()
        
        try:
            with self.driver.session() as session:
                # Try to find callee by name
                query = """
                MATCH (caller:Function {id: $caller_id})
                MATCH (callee:Function {name: $callee_name})
                WHERE caller.repo = callee.repo
                CREATE (caller)-[:CALLS]->(callee)
                """
                session.run(query, caller_id=caller_id, callee_name=callee_name)
                return True
        except Exception as e:
            logger.debug(f"Could not create CALLS relationship: {e}")
            return False
    
    def create_imports_relationship(self, file_id: str, imported_path: str) -> bool:
        """
        Create an IMPORTS relationship between files
        
        Args:
            file_id: Importing file ID
            imported_path: Imported file path
            
        Returns:
            True if successful
        """
        self._ensure_connected()
        
        try:
            with self.driver.session() as session:
                # Try to find imported file by path
                query = """
                MATCH (importer:File {id: $file_id})
                MATCH (imported:File)
                WHERE importer.repo = imported.repo 
                  AND (imported.path CONTAINS $imported_path OR imported.path = $imported_path)
                CREATE (importer)-[:IMPORTS]->(imported)
                """
                session.run(query, file_id=file_id, imported_path=imported_path)
                return True
        except Exception as e:
            logger.debug(f"Could not create IMPORTS relationship: {e}")
            return False
    
    def create_relationships_batch(self, relationships: List[Dict[str, Any]]) -> int:
        """
        Create multiple relationships in a batch
        
        Args:
            relationships: List of relationship dicts with keys: type, from_id, to_id/to_name
            
        Returns:
            Number of relationships created
        """
        self._ensure_connected()
        
        count = 0
        for rel in relationships:
            rel_type = rel.get('type')
            if rel_type == 'CONTAINS':
                if self.create_contains_relationship(rel['from_id'], rel['to_id']):
                    count += 1
            elif rel_type == 'CALLS':
                if self.create_calls_relationship(rel['from_id'], rel['to_name']):
                    count += 1
            elif rel_type == 'IMPORTS':
                if self.create_imports_relationship(rel['from_id'], rel['to_path']):
                    count += 1
        
        logger.info(f"Created {count} relationships in batch")
        return count

    def get_function_neighbors(self, function_id: str, 
                              relationship_type: str = "CALLS") -> List[Dict[str, Any]]:
        """
        Get neighboring functions connected by a specific relationship
        
        Args:
            function_id: Function ID to query
            relationship_type: Type of relationship (CALLS, etc.)
            
        Returns:
            List of neighbor function information
        """
        self._ensure_connected()
        
        try:
            with self.driver.session() as session:
                query = f"""
                MATCH (f:Function {{id: $function_id}})-[:{relationship_type}]->(neighbor:Function)
                RETURN neighbor.id as id, neighbor.name as name, 
                       neighbor.file_id as file_id, neighbor.signature as signature
                """
                result = session.run(query, function_id=function_id)
                
                neighbors = []
                for record in result:
                    neighbors.append({
                        'id': record['id'],
                        'name': record['name'],
                        'file_id': record['file_id'],
                        'signature': record['signature']
                    })
                
                return neighbors
        except Exception as e:
            logger.error(f"Failed to query function neighbors: {e}")
            return []
    
    def get_file_functions(self, file_id: str) -> List[Dict[str, Any]]:
        """
        Get all functions in a file
        
        Args:
            file_id: File ID to query
            
        Returns:
            List of function information
        """
        self._ensure_connected()
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (file:File {id: $file_id})-[:CONTAINS*1..2]->(func:Function)
                RETURN func.id as id, func.name as name, 
                       func.start_line as start_line, func.end_line as end_line,
                       func.signature as signature
                ORDER BY func.start_line
                """
                result = session.run(query, file_id=file_id)
                
                functions = []
                for record in result:
                    functions.append({
                        'id': record['id'],
                        'name': record['name'],
                        'start_line': record['start_line'],
                        'end_line': record['end_line'],
                        'signature': record['signature']
                    })
                
                return functions
        except Exception as e:
            logger.error(f"Failed to query file functions: {e}")
            return []
    
    def get_stats(self, repo_name: str) -> Dict[str, int]:
        """
        Get statistics about the graph for a repository
        
        Args:
            repo_name: Repository name
            
        Returns:
            Dictionary with node and edge counts
        """
        self._ensure_connected()
        
        try:
            with self.driver.session() as session:
                # Count nodes
                node_query = """
                MATCH (n {repo: $repo_name})
                RETURN labels(n)[0] as label, count(n) as count
                """
                node_result = session.run(node_query, repo_name=repo_name)
                
                stats = {'files': 0, 'classes': 0, 'functions': 0, 'relationships': 0}
                for record in node_result:
                    label = record['label']
                    count = record['count']
                    if label == 'File':
                        stats['files'] = count
                    elif label == 'Class':
                        stats['classes'] = count
                    elif label == 'Function':
                        stats['functions'] = count
                
                # Count relationships
                rel_query = """
                MATCH (n {repo: $repo_name})-[r]->()
                RETURN count(r) as count
                """
                rel_result = session.run(rel_query, repo_name=repo_name)
                for record in rel_result:
                    stats['relationships'] = record['count']
                
                return stats
        except Exception as e:
            logger.error(f"Failed to get graph stats: {e}")
            return {'files': 0, 'classes': 0, 'functions': 0, 'relationships': 0}
    def get_directory_summaries(self, repo_name: str) -> List[Dict[str, Any]]:
        """
        Get all directory summaries for a repository
        
        Args:
            repo_name: Repository name
            
        Returns:
            List of directory summaries
        """
        self._ensure_connected()
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (d:Directory {repo: $repo_name})
                RETURN d.path as path, d.summary as summary
                """
                result = session.run(query, repo_name=repo_name)
                
                summaries = []
                for record in result:
                    summaries.append({
                        'path': record['path'],
                        'summary': record['summary']
                    })
                return summaries
        except Exception as e:
            logger.error(f"Failed to get directory summaries: {e}")
            return []

    def get_functions_in_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Retrieve all functions defined in a specific file.
        
        Args:
            file_path: The file path (relative to repo root)
            
        Returns:
            List of function nodes (dict)
        """
        self._ensure_connected()
        query = """
        MATCH (f:File {path: $file_path})-[:CONTAINS]->(func:Function)
        RETURN func
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, file_path=file_path)
                functions = []
                for record in result:
                    node = record['func']
                    # Convert Neo4j node to dict and ensure ID is present
                    func_data = dict(node)
                    # Ensure essential fields are present
                    if 'id' not in func_data:
                        func_data['id'] = node.element_id # Fallback if id property missing
                    functions.append(func_data)
                return functions
        except Exception as e:
            logger.error(f"Failed to get functions in file {file_path}: {e}")
            return []

    def get_function_neighbors(self, function_ids: List[str]) -> Dict[str, Dict[str, List[str]]]:
        """
        Get immediate neighbors (callers and callees) for a list of functions.
        
        Args:
            function_ids: List of function IDs
            
        Returns:
            Dict mapping function_id to {'callers': [], 'callees': []}
        """
        self._ensure_connected()
        query = """
        MATCH (f:Function)
        WHERE f.id IN $function_ids
        OPTIONAL MATCH (caller:Function)-[:CALLS]->(f)
        OPTIONAL MATCH (f)-[:CALLS]->(callee:Function)
        RETURN f.id as func_id, 
               collect(DISTINCT caller.name) as callers,
               collect(DISTINCT callee.name) as callees
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, function_ids=function_ids)
                neighbors = {}
                for record in result:
                    neighbors[record['func_id']] = {
                        'callers': [c for c in record['callers'] if c],
                        'callees': [c for c in record['callees'] if c]
                    }
                return neighbors
        except Exception as e:
            logger.error(f"Failed to get function neighbors: {e}")
            return {}

    def get_context_subgraph(self, function_ids: List[str], depth: int = 1) -> str:
        """
        Retrieve a subgraph context for a list of functions
        
        Args:
            function_ids: List of function IDs to start from
            depth: Traversal depth
            
        Returns:
            String representation of the subgraph
        """
        self._ensure_connected()
        
        try:
            with self.driver.session() as session:
                # Get callers and callees
                query = """
                MATCH (f:Function)
                WHERE f.id IN $function_ids
                OPTIONAL MATCH (caller:Function)-[:CALLS]->(f)
                OPTIONAL MATCH (f)-[:CALLS]->(callee:Function)
                RETURN f.name as func, 
                       collect(DISTINCT caller.name) as callers,
                       collect(DISTINCT callee.name) as callees
                """
                result = session.run(query, function_ids=function_ids)
                
                context = "Graph Context:\n"
                for record in result:
                    func = record['func']
                    callers = [c for c in record['callers'] if c]
                    callees = [c for c in record['callees'] if c]
                    
                    context += f"- Function '{func}':\n"
                    if callers:
                        context += f"  - Called by: {', '.join(callers)}\n"
                    if callees:
                        context += f"  - Calls: {', '.join(callees)}\n"
                        
                return context
        except Exception as e:
            logger.error(f"Failed to get context subgraph: {e}")
            return "Error retrieving graph context"
