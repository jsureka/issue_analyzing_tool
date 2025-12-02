"""
LLM Service - Interface for Large Language Model interactions
Uses Google's Gemini models for code analysis and patch generation
"""

import logging
import os
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
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
        self.model_name = model_name or Config.LLM_MODEL_NAME
        self.temperature = Config.LLM_TEMPERATURE
        
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
            logger.info(f"LLM Service initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM Service: {e}")
            self.llm = None

    def is_available(self) -> bool:
        """Check if LLM service is available"""
        return self.llm is not None

    def summarize_code(self, code_text: str, file_path: str) -> str:
        """
        Generate a summary of a code block or file
        
        Args:
            code_text: The source code text
            file_path: Path to the file (for context)
            
        Returns:
            Summary string
        """
        if not self.is_available():
            return "LLM service unavailable"
            
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert software engineer. Summarize the purpose and key functionality of the following code file. Be concise."),
                ("human", "File: {file_path}\n\nCode:\n```{language}\n{code}\n```")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({
                "file_path": file_path,
                "language": "python" if file_path.endswith(".py") else "java",
                "code": code_text[:10000]  # Truncate if too long
            })
            
            return response.content
        except Exception as e:
            logger.error(f"Error summarizing code: {e}")
            return "Error generating summary"

    def analyze_issue(self, issue_title: str, issue_body: str, 
                     code_context: List[Dict[str, Any]], 
                     graph_context: str) -> Dict[str, str]:
        """
        Analyze an issue with code and graph context
        
        Args:
            issue_title: GitHub issue title
            issue_body: GitHub issue body
            code_context: List of relevant code snippets (from Vector Search)
            graph_context: String description of graph relationships (from Neo4j)
            
        Returns:
            Dictionary with 'analysis' and 'hypothesis'
        """
        if not self.is_available():
            return {"analysis": "LLM unavailable", "hypothesis": "None"}
            
        try:
            # Format code context
            formatted_code = ""
            for idx, item in enumerate(code_context):
                formatted_code += f"\n--- Snippet {idx+1}: {item.get('name')} in {item.get('file_path')} ---\n"
                formatted_code += f"```{item.get('language', 'text')}\n{item.get('snippet', '')}\n```\n"
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a senior software engineer debugging an issue. 
Analyze the issue based on the provided code snippets and architectural context (graph).
Identify the root cause and explain your reasoning."""),
                ("human", """Issue: {title}
Description: {body}

Code Context:
{code_context}

Architectural Context (Graph):
{graph_context}

Provide a JSON response with:
1. 'analysis': A concise technical explanation of the bug (2-3 sentences max). Follow this with a bulleted list of the key issue details.
2. 'hypothesis': Where specifically the bug is likely located (file and function).""")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({
                "title": issue_title,
                "body": issue_body,
                "code_context": formatted_code,
                "graph_context": graph_context
            })
            
            # Simple parsing (in a real app, use JsonOutputParser)
            content = response.content
            # Cleanup markdown json blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            import json
            try:
                return json.loads(content)
            except:
                return {"analysis": content, "hypothesis": "See analysis"}
                
        except Exception as e:
            logger.error(f"Error analyzing issue: {e}")
            return {"analysis": f"Error: {str(e)}", "hypothesis": "Unknown"}

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
                    if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
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
    def rerank_candidates(self, issue_title: str, issue_body: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Re-rank candidates based on relevance to the issue using LLM with Chain of Thought.
        
        Args:
            issue_title: Issue title
            issue_body: Issue body
            candidates: List of candidate dicts with 'id', 'name', 'file_path', 'code', 'class_name', 'source'
            
        Returns:
            List of candidates with updated 'score' and 'reasoning'
        """
        if not self.is_available() or not candidates:
            return candidates

        try:
            # Prepare candidates for prompt
            candidates_text = ""
            for i, cand in enumerate(candidates):
                # Truncate code if too long
                code_snippet = cand.get('code', '')[:1000] 
                class_info = f"Class: {cand.get('class_name')}\n" if cand.get('class_name') else ""
                source_info = f"Source: {list(cand.get('sources', []))}\n"
                candidates_text += f"Candidate {i} (ID: {cand.get('id')}):\nFile: {cand.get('file_path')}\n{class_info}Function: {cand.get('name')}\n{source_info}Code:\n```\n{code_snippet}\n```\n\n"

            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert software engineer debugging a large codebase. 
Your task is to identify which of the provided code candidates is most likely to contain the bug described in the issue.

For each candidate:
1. Analyze the code and its context (file path, class name, function name).
2. Compare it against the issue description.
3. Provide a brief "Reasoning" explaining why it is or isn't relevant.
4. Assign a "Relevance Score" from 0.0 (irrelevant) to 1.0 (highly relevant/buggy).

Output a SINGLE JSON object where keys are candidate IDs and values are objects containing "reasoning" and "score".
Example:
{{
  "func_id_1": {{
    "reasoning": "The function name matches the stack trace and the logic handles the specific error case described.",
    "score": 0.95
  }},
  "func_id_2": {{
    "reasoning": "This is a utility function that seems unrelated to the core issue.",
    "score": 0.1
  }}
}}"""),
                ("human", """Issue: {title}
Description: {body}

Candidates:
{candidates_text}

Provide the JSON analysis and ranking:""")
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
            analysis_result = json.loads(content)
            
            # Update scores
            reranked_candidates = []
            for cand in candidates:
                cand_id = cand.get('id')
                if cand_id in analysis_result:
                    result = analysis_result[cand_id]
                    llm_score = float(result.get('score', 0.0))
                    reasoning = result.get('reasoning', '')
                    
                    cand['llm_score'] = llm_score
                    cand['llm_reasoning'] = reasoning
                    
                    # Boost logic: 
                    # If LLM is very confident (>0.8), significantly boost.
                    # If LLM is confident (>0.5), moderately boost.
                    # If LLM is low confidence, penalize or keep same.
                    
                    if llm_score > 0.8:
                        boost = 2.0
                    elif llm_score > 0.5:
                        boost = 1.5
                    elif llm_score < 0.2:
                        boost = 0.5
                    else:
                        boost = 1.0
                        
                    cand['final_score'] = cand['score'] * boost
                else:
                    cand['llm_score'] = 0.0
                    cand['llm_reasoning'] = "Not analyzed by LLM"
                    cand['final_score'] = cand['score'] # No boost
                reranked_candidates.append(cand)
                
            # Sort by final score
            reranked_candidates.sort(key=lambda x: x.get('final_score', 0), reverse=True)
            return reranked_candidates

        except Exception as e:
            logger.error(f"Error reranking candidates: {e}")
            return candidates

    @retry_with_backoff
    def filter_files(self, issue_title: str, issue_body: str, file_paths: List[str]) -> List[str]:
        """
        Select the most relevant files from a list based on the issue description.
        
        Args:
            issue_title: Issue title
            issue_body: Issue body
            file_paths: List of file paths to filter
            
        Returns:
            List of selected file paths (subset of input)
        """
        if not self.is_available() or not file_paths:
            return file_paths[:5] # Fallback

        try:
            files_text = "\n".join([f"- {path}" for path in file_paths])
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert software engineer. Your task is to identify the files that likely contain the bug described in the issue.
You will be given a list of candidate file paths from the repository.
Select the top 3-5 files that are most relevant to the issue.
Consider the file names and their likely responsibilities.

Return a JSON object with a single key "selected_files" containing the list of file paths.
Example: {{ "selected_files": ["lib/rucio/core/replica.py", "lib/rucio/api/did.py"] }}"""),
                ("human", """Issue: {title}
Description: {body}

Candidate Files:
{files_text}

Select the relevant files:""")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({
                "title": issue_title,
                "body": issue_body,
                "files_text": files_text
            })
            
            content = response.content
            # Cleanup markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            import json
            result = json.loads(content)
            selected = result.get("selected_files", [])
            
            # Validate that selected files are in the input list
            valid_selected = [f for f in selected if f in file_paths]
            
            # If LLM returns nothing valid, fallback to top 3 input files
            if not valid_selected:
                return file_paths[:3]
                
            return valid_selected

        except Exception as e:
            logger.error(f"Error filtering files: {e}")
            return file_paths[:3] # Fallback

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
1.  **Look Deeper**: Do not just pick the public entry point (e.g., `list_replicas`). Look for the internal helper function or implementation method (e.g., `_list_replicas_internal`) where the logic actually resides.
2.  **Conservative Selection**: Select ONLY the function(s) you are confident contain the bug. If unsure, select the most likely one.

Return a JSON object with a single key "selected_functions" containing a list of objects.
Each object must have:
- "id": The candidate ID.
- "reasoning": Brief explanation of why this is the root cause.

Example: {{ "selected_functions": [ {{ "id": "func_1", "reasoning": "Logic error in loop condition" }} ] }}"""),
                ("human", """Issue: {title}
Description: {body}

Candidate Functions:
{candidates_text}

Select the buggy function(s):""")
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
            for item in selected_items:
                cand_id = item.get('id')
                # Find original candidate
                orig_cand = next((c for c in candidates if c.get('id') == cand_id), None)
                if orig_cand:
                    # Create a copy to avoid mutating original list if needed
                    new_cand = orig_cand.copy()
                    new_cand['llm_reasoning'] = item.get('reasoning')
                    selected_candidates.append(new_cand)
            
            return selected_candidates

        except Exception as e:
            logger.error(f"Error selecting functions: {e}")
            return candidates[:1] # Fallback
