"""
LLM Service - Interface for Large Language Model interactions
Uses Google's Gemini models for code analysis and patch generation
"""

import logging
import os
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

try:
    from ...config import Config
except ImportError:
    try:
        from config import Config
    except ImportError:
        # Fallback for testing if config is not found
        class Config:
            GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
            OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
            LLM_MODEL_NAME = os.getenv('LLM_MODEL_NAME', 'gemma-3-4b')
            LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', 0.2))

logger = logging.getLogger(__name__)

class LLMService:
    """Service for interacting with LLMs (Gemini)"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = None):
        """
        Initialize LLM Service
        
        Args:
            api_key: Google API Key (defaults to config)
            model_name: Model name (defaults to config)
        """
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.openai_api_key = Config.OPENAI_API_KEY
        self.model_name = model_name or Config.LLM_MODEL_NAME
        self.temperature = Config.LLM_TEMPERATURE
        
        self.provider = "google"
        if self.model_name.startswith("gpt"):
            self.provider = "openai"
        
        if self.provider == "google":
            if not self.api_key:
                logger.warning("GEMINI_API_KEY not set. LLM features will be disabled.")
                self.llm = None
                return
                
            try:
                genai.configure(api_key=self.api_key)
                self.llm = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    temperature=self.temperature,
                    convert_system_message_to_human=True
                )
                logger.info(f"LLM Service initialized with Google model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Google LLM: {e}")
                self.llm = None
        
        elif self.provider == "openai":
            if not self.openai_api_key:
                logger.warning("OPENAI_API_KEY not set. LLM features will be disabled.")
                self.llm = None
                return
            
            if ChatOpenAI is None:
                logger.error("langchain_openai not installed. Please install it to use OpenAI models.")
                self.llm = None
                return

            try:
                self.llm = ChatOpenAI(
                    model=self.model_name,
                    api_key=self.openai_api_key,
                    temperature=self.temperature
                )
                logger.info(f"LLM Service initialized with OpenAI model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI LLM: {e}")
                self.llm = None

    def is_available(self) -> bool:
        """Check if LLM service is available"""
        return self.llm is not None





    def generate_patch(self, issue_title: str, issue_body: str, 
                      target_file: str, target_code: str, 
                      analysis: str) -> str:
        """
        Generate a patch for the bug
        
        Args:
            issue_title: Issue title
            issue_body: Issue body
            target_file: File to patch
            target_code: Original code of the file
            analysis: Previous analysis
            
        Returns:
            Generated patch (diff or new code)
        """
        if not self.is_available():
            return "LLM unavailable"
            
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert developer. Provide a concise step-by-step plan to fix the identified bug. You may include pseudocode if it helps clarify the logic. Do NOT provide full code patches, verbose explanations, or 'important considerations' sections. Keep it strictly to the plan."),
                ("human", """Issue: {title}
Analysis: {analysis}

Target File: {file}
Original Code:
```
{code}
```

Generate the solution plan:""")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({
                "title": issue_title,
                "analysis": analysis,
                "file": target_file,
                "code": target_code
            })
            
            return response.content
        except Exception as e:
            logger.error(f"Error generating patch: {e}")
            return f"Error generating patch: {e}"
    def retry_with_backoff(func):
        """Decorator for retrying with exponential backoff"""
        import time
        import functools
        import re
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            max_retries = 8 # Increased to allow for longer waits (up to ~17 mins total)
            base_delay = 4  # Increased base delay
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    is_rate_limit = "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg or "ratelimit" in error_msg
                    
                    if is_rate_limit:
                        if attempt == max_retries - 1:
                            logger.error(f"Max retries ({max_retries}) exceeded for rate limit.")
                            raise
                        
                        # Try to parse wait time from error message
                        wait_time = 0
                        # Pattern for "Please retry in Xs" or "retry_delay { seconds: X }"
                        match = re.search(r"retry in (\d+(\.\d+)?)s", error_msg)
                        if match:
                            wait_time = float(match.group(1))
                        else:
                            match = re.search(r"seconds:\s*(\d+)", error_msg)
                            if match:
                                wait_time = float(match.group(1))
                        
                        # Use parsed time + buffer, or exponential backoff
                        if wait_time > 0:
                            delay = wait_time + 2 # Add buffer
                        else:
                            delay = base_delay * (2 ** attempt)
                            
                        logger.warning(f"Rate limit hit. Retrying in {delay:.2f}s... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(delay)
                    else:
                        raise
            return None
        return wrapper





    @retry_with_backoff
    def select_functions(self, issue_title: str, issue_body: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Select the exact buggy function(s) from a list of candidates.
        
        Args:
            issue_title: Issue title
            issue_body: Issue body
            candidates: List of candidate dicts
            
        Returns:
            List of selected candidate dicts with 'reasoning'
        """
        if not self.is_available() or not candidates:
            return candidates[:1] # Fallback

        try:
            candidates_text = ""
            for i, cand in enumerate(candidates):
                # Increase context to 1000 chars
                code_snippet = cand.get('code', '')[:1000] 
                class_info = f"Class: {cand.get('class_name')}\n" if cand.get('class_name') else ""
                
                # Add Graph Context if available
                graph_context = ""
                if cand.get('callers') or cand.get('callees'):
                    graph_context = f"Graph Context:\n"
                    if cand.get('callers'):
                        graph_context += f"  - Called by: {', '.join(cand['callers'][:5])}\n"
                    if cand.get('callees'):
                        graph_context += f"  - Calls: {', '.join(cand['callees'][:5])}\n"
                
                candidates_text += f"Candidate {i} (ID: {cand.get('id')}):\nFile: {cand.get('file_path')}\n{class_info}Function: {cand.get('name')}\n{graph_context}Code:\n```\n{code_snippet}\n```\n\n"

            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert software engineer debugging a complex system.
Your task is to identify the **ROOT CAUSE** function(s) that need to be modified to fix the bug.

**CRITICAL INSTRUCTIONS**:
1.  **Analyze Code Snippets**: You are provided with code snippets retrieved from the vector database. **YOU MUST USE THESE SNIPPETS** to make your decision. Do not hallucinate code that is not present.
2.  **Filter Irrelevant Candidates**: Many candidates may be irrelevant. If a candidate's code does not match the issue logic, **DISCARD IT**. Do not select it just because it was retrieved.
3.  **Look Deeper**: Do not just pick the public entry point (e.g., `list_replicas`). Look for the internal helper function or implementation method (e.g., `_list_replicas_internal`) where the logic actually resides.
4.  **Multi-Selection**: You MUST select EXACTLY 5 most likely functions (or fewer if less than 5 candidates are provided). We prioritize Recall. Rank them from most likely to least likely.

Return a JSON object with a single key "selected_functions" containing a list of EXACTLY 5 objects (or fewer if less than 5 candidates provided).
Each object must have:
- "id": The candidate ID.
- "reasoning": Brief explanation of why this is the root cause, referencing specific lines or logic from the provided snippet.

Example: {{ "selected_functions": [ {{ "id": "func_1", "reasoning": "Snippet shows logic error in loop condition at line 5" }}, {{ "id": "func_2", "reasoning": "Snippet confirms it handles null input from func_1 incorrectly" }}, {{ "id": "func_3", "reasoning": "Related helper that processes the data" }}, {{ "id": "func_4", "reasoning": "Caller function that invokes func_1" }}, {{ "id": "func_5", "reasoning": "Utility function used in error path" }} ] }}"""),
                ("human", """Issue: {title}
Description: {body}

Candidate Functions:
{candidates_text}

Select the top 5 buggy function(s):""")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({
                "title": issue_title,
                "body": issue_body,
                "candidates_text": candidates_text
            })
            
            content = response.content
            # Cleanup markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            import json
            result = json.loads(content)
            selected_items = result.get("selected_functions", [])
            
            selected_candidates = []
            for item in selected_items[:5]:  # Enforce top 5 limit
                cand_id = item.get('id')
                # Find original candidate
                orig_cand = next((c for c in candidates if c.get('id') == cand_id), None)
                if orig_cand:
                    # Create a copy to avoid mutating original list if needed
                    new_cand = orig_cand.copy()
                    new_cand['llm_reasoning'] = item.get('reasoning')
                    selected_candidates.append(new_cand)
            
            # Extract token usage
            token_usage = {}
            if hasattr(response, 'response_metadata'):
                token_usage = response.response_metadata.get('token_usage', {})
            
            return selected_candidates, token_usage

        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "rate limit" in str(e).lower():
                raise
            logger.error(f"Error selecting functions: {e}")
            return candidates[:1], {} # Fallback

    @retry_with_backoff
    def generate_search_query(self, issue_title: str, issue_body: str) -> str:
        """
        Generate a concise search query from the issue description.
        
        Args:
            issue_title: Issue title
            issue_body: Issue body
            
        Returns:
            Generated search query string
        """
        if not self.is_available():
            return f"{issue_title} {issue_body}"[:512] # Fallback to raw text

        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert developer assisting with bug localization.
Your task is to generate a **concise, semantic search query** that will be used to retrieve relevant code functions from a vector database.

**Instructions**:
1.  Analyze the issue title and body to understand the core technical problem.
2.  Identify key concepts, specific class/function names mentioned, and the type of logic involved.
3.  Formulate a query that captures these elements.
4.  **Do NOT** include generic terms like "bug", "issue", "fix", or "error". Focus on the *code* concepts.
5.  **Do NOT** return JSON. Return ONLY the query string.

Example Issue: "AttributeError: 'NoneType' object has no attribute 'get' in process_data"
Example Query: process_data function AttributeError NoneType get method data processing logic"""),
                ("human", """Issue: {title}
Description: {body}

Generate the search query:""")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({
                "title": issue_title,
                "body": issue_body
            })
            
            query = response.content.strip()
            # Remove quotes if present
            if query.startswith('"') and query.endswith('"'):
                query = query[1:-1]
            
            return query

        except Exception as e:
            logger.error(f"Error generating search query: {e}")
            return f"{issue_title} {issue_body}"[:512] # Fallback
