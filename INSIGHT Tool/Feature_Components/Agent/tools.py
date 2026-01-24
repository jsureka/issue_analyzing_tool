import logging
import json
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..KnowledgeBase.vector_store import VectorStore
from ..KnowledgeBase.graph_store import GraphStore
from ..KnowledgeBase.embedder import CodeEmbedder

logger = logging.getLogger(__name__)

class VectorSearchInput(BaseModel):
    query: str = Field(description="The natural language query to search for relevant code functions.")
    k: int = Field(default=10, description="Number of results to return.")

class VectorSearchTool(BaseTool):
    name: str = "vector_search"
    description: str = "Search for relevant code functions using semantic similarity. Returns a list of potential candidates."
    args_schema: type[BaseModel] = VectorSearchInput
    
    vector_store: VectorStore = None
    embedder: CodeEmbedder = None
    repo_name: str = ""

    def __init__(self, vector_store: VectorStore, embedder: CodeEmbedder, repo_name: str, **kwargs):
        super().__init__(**kwargs)
        self.vector_store = vector_store
        self.embedder = embedder
        self.repo_name = repo_name

    def _run(self, query: str, k: int = 10) -> str:
        try:
            # Embed query
            # embed_batch expects a list of strings
            embeddings = self.embedder.embed_batch([query])
            if embeddings is None or len(embeddings) == 0:
                return "Error: Failed to generate embedding for query."
            
            query_vec = embeddings[0]
            
            # Search
            indices, scores, metadata = self.vector_store.search(query_vec, k=k)
            
            results = []
            for i, meta in enumerate(metadata):
                results.append({
                    "id": meta.get("id"),
                    "name": meta.get("name"),
                    "signature": meta.get("signature"),
                    "score": float(scores[i]),
                    "file_path": meta.get("file_path"),
                    "start_line": meta.get("start_line")
                })
                
            return json.dumps(results, indent=2)
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return f"Error executing vector search: {str(e)}"

class GraphNeighborsInput(BaseModel):
    function_id: str = Field(description="The ID of the function to find neighbors for.")
    relationship_type: str = Field(default="CALLS", description="The type of relationship to traverse (e.g., CALLS).")

class GraphNeighborsTool(BaseTool):
    name: str = "graph_neighbors"
    description: str = "Find direct neighbors (callers/callees) of a function in the code knowledge graph."
    args_schema: type[BaseModel] = GraphNeighborsInput
    
    graph_store: GraphStore = None
    repo_name: str = ""

    def __init__(self, graph_store: GraphStore, repo_name: str, **kwargs):
        super().__init__(**kwargs)
        self.graph_store = graph_store
        self.repo_name = repo_name

    def _run(self, function_id: str, relationship_type: str = "CALLS") -> str:
        try:
            # GraphStore.get_function_neighbors returns List[Dict]
            neighbors = self.graph_store.get_function_neighbors(function_id, relationship_type)
            return json.dumps(neighbors, indent=2)
        except Exception as e:
            logger.error(f"Graph traversal failed: {e}")
            return f"Error traversing graph: {str(e)}"

class GraphContextInput(BaseModel):
    function_ids: List[str] = Field(description="List of function IDs to retrieve context for.")

class GraphContextTool(BaseTool):
    name: str = "graph_context"
    description: str = "Retrieve a subgraph context (callers/callees) for a list of functions to understand their relationships."
    args_schema: type[BaseModel] = GraphContextInput
    
    graph_store: GraphStore = None
    repo_name: str = ""
    
    def __init__(self, graph_store: GraphStore, repo_name: str, **kwargs):
        super().__init__(**kwargs)
        self.graph_store = graph_store
        self.repo_name = repo_name
        
    def _run(self, function_ids: List[str]) -> str:
        try:
            # GraphStore.get_context_subgraph returns a string representation
            context_str = self.graph_store.get_context_subgraph(function_ids)
            return context_str
        except Exception as e:
            logger.error(f"Graph context retrieval failed: {e}")
            return f"Error retrieving graph context: {str(e)}"
