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

    @staticmethod
    def _optimize_token_usage(code: str) -> str:
        """
        Optimize code snippet for token usage.
        - Removes consecutive spaces/tabs
        - Removes empty lines
        - Reduces multiple newlines
        """
        if not code:
            return ""
        
        import re
        
        # 1. Replace tabs with 4 spaces (to standardise before reduction)
        code = code.replace('\t', '    ')
        
        # 2. Iterate line by line to trim
        lines = code.splitlines()
        optimized_lines = []
        for line in lines:
            stripped = line.rstrip() # Keep indentation
            if stripped:
                optimized_lines.append(stripped)
        
        # 3. Join back
        code = "\n".join(optimized_lines)
        
        # 4. Remove excessive newlines (more than 2)
        code = re.sub(r'\n{3,}', '\n\n', code)
        
        return code





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

Generate a concise solution plan.
1. Provide high-level pseudocode or step-by-step directions.
2. DO NOT generate actual code blocks.
3. Keep it short and actionable.""")
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
    def select_functions(self, issue_title: str, issue_body: str, candidates: Any) -> List[Dict[str, Any]]:
        """
        Select the exact buggy code entities (classes/functions) from a list of candidates.
        
        Args:
            issue_title: Issue title
            issue_body: Issue body
            candidates: List of candidate dicts OR Dict with keys 'files', 'classes', 'functions'
            
        Returns:
            Tuple of (List of selected candidate dicts with 'reasoning' and 'entity_type', token_usage)
        """
        if not self.is_available() or not candidates:
            return [], {} # Fallback

        try:
            # Handle input format
            if isinstance(candidates, list):
                # Legacy/Fallback mode
                files = [c for c in candidates if c.get('entity_type') == 'file']
                classes = [c for c in candidates if c.get('entity_type') == 'class']
                funcs = [c for c in candidates if c.get('entity_type') == 'function']
            else:
                files = candidates.get('files', [])
                classes = candidates.get('classes', [])
                funcs = candidates.get('functions', [])

            logger.info(f"LLM Input Candidates: {len(files)} Files, {len(classes)} Classes, {len(funcs)} Functions")
            
            # Helper to format a single candidate
            def format_cand(cand, idx, label):
                raw_code = cand.get('code', '')
                optimized_code = self._optimize_token_usage(raw_code)
                code_snippet = optimized_code[:1500] 
                
                type_label = cand.get('entity_type', 'unknown').upper()
                class_info = f"Class: {cand.get('class_name')}\n" if cand.get('class_name') and cand.get('entity_type') == 'function' else ""
                
                return f"[{label} Candidate {idx}] (ID: {cand.get('id')}):\nType: {type_label}\nFile: {cand.get('file_path')}\n{class_info}Name: {cand.get('name')}\nCode:\n```\n{code_snippet}\n```\n\n"

            # Build Prompt Sections
            files_text = "\n".join([format_cand(c, i, "FILE") for i, c in enumerate(files)])
            classes_text = "\n".join([format_cand(c, i, "CLASS") for i, c in enumerate(classes)])
            funcs_text = "\n".join([format_cand(c, i, "FUNC") for i, c in enumerate(funcs)])

            prompt = ChatPromptTemplate.from_messages([
                ("system", f"""You are an expert software engineer debugging a complex system.
Your task is to identify the **ROOT CAUSE** code entities (files, classes, or functions) that need to be modified to fix the bug.

**CRITICAL INSTRUCTIONS**:
1.  **Analyze Granularly**: You are provided with candidates grouped by type (Files, Classes, Functions).
2.  **Separate Predictions**:
    *   **Files**: Select files that are entirely missing, irrelevant, or need broad architectural changes.
    *   **Classes**: Select classes that have state/logic issues spanning multiple methods.
    *   **Functions**: Select specific functions where the bug logic resides.
3.  **Consistency**: If you select a Function, you imply its Class/File is relevant. You do NOT need to re-select the file unless the file *itself* has a separate issue.
4.  **Priorities**: detailed function fixes are usually preferred over broad file selections.

Return a JSON object with three keys: "selected_files", "selected_classes", "selected_functions". Default to empty lists if none apply for a category.
Each item in the lists must have:
- "id": The candidate ID.
- "reasoning": Brief explanation.

Example:
{{{{
  "selected_files": [ {{{{ "id": "file_1", "reasoning": "Missing config" }}}} ],
  "selected_classes": [],
  "selected_functions": [ {{{{ "id": "func_a", "reasoning": "Off-by-one error" }}}} ]
}}}}"""),
                ("human", """Issue: {title}
Description: {body}

=== CANDIDATE FILES ===
{files_text}

=== CANDIDATE CLASSES ===
{classes_text}

=== CANDIDATE FUNCTIONS ===
{funcs_text}

Select the buggy entities.""")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({
                "title": issue_title,
                "body": issue_body,
                "files_text": files_text,
                "classes_text": classes_text,
                "funcs_text": funcs_text
            })
            
            content = response.content
            logger.info(f"Raw LLM Response: {content}")
            
            # Cleanup markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            import json
            result = json.loads(content)
            
            selected_candidates = []
            
            # Helper to map back
            all_source_map = {c['id']: c for c in files + classes + funcs}
            
            # Aggregate in priority order: Functions > Classes > Files
            for category in ["selected_functions", "selected_classes", "selected_files"]:
                items = result.get(category, [])
                for item in items:
                    cand_id = item.get('id')
                    if not cand_id: continue
                    
                    orig_cand = all_source_map.get(cand_id)
                    if orig_cand:
                        new_cand = orig_cand.copy()
                        new_cand['llm_reasoning'] = item.get('reasoning')
                        # Ensure entity type is correct based on category bucket? 
                        # Or trust original. Trust original.
                        selected_candidates.append(new_cand)

            # Limit total selection count? Or just return all relevant.
            # config.LLM_SELECTION_COUNT applies to total items usually.
            
            # Sort by priority? The prompt asked for granular. 
            # We just return the list; the caller sorts/ranks.
            
            # Extract token usage
            token_usage = {}
            if hasattr(response, 'response_metadata'):
                token_usage = response.response_metadata.get('token_usage', {})
            
            return selected_candidates, token_usage

        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "rate limit" in str(e).lower():
                raise
            logger.error(f"Error selecting functions: {e}")
            # Fallback
            flat_candidates = (files if 'files' in locals() else []) + (classes if 'classes' in locals() else []) + (funcs if 'funcs' in locals() else [])
            return flat_candidates[:1], {} 

    @retry_with_backoff
    def generate_search_query(self, issue_title: str, issue_body: str) -> Dict[str, Any]:
        """
        Generate a search query and determines if the issue is related to test files.
        """
        if not self.is_available():
            return {"query": f"{issue_title} {issue_body}"[:200], "is_test_related": True}

        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert developer.
Target:
1. Generate a concise search query (5-10 keywords) to find the relevant code.
2. **Predict specific Class Names** or File Names that are likely to be relevant based on the issue description.
3. Determine if the issue is strictly about fixing **TEST code**.

Return a JSON object:
{{
  "query": "class_name function_name key_terms",
  "potential_class_names": "ClassA ClassB FileC",
  "is_test_related": boolean
}}
"""),
                ("human", "Issue: {title}\nDescription: {body}\n\nOutput JSON:")
            ])
            
            chain = prompt | self.llm
            response = chain.invoke({"title": issue_title, "body": issue_body})
            
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            import json
            result = json.loads(content)
            
            base_query = result.get("query", f"{issue_title}")
            class_names = result.get("potential_class_names", "")
            
            # Enrich query with class names if available
            final_query = f"{base_query} {class_names}".strip()
            
            return {
                "query": final_query,
                "is_test_related": result.get("is_test_related", False)
            }

        except Exception as e:
            logger.error(f"Error generating search query: {e}")
            return {"query": f"{issue_title}", "is_test_related": True}

    @retry_with_backoff
    def generate_candidate_analysis(self, issue_title: str, issue_body: str, candidates: List[Dict[str, Any]]) -> str:
        """
        Generate a technical analysis for the selected candidates.
        Used as a fallback when granular reasoning is unavailable.
        """
        if not self.is_available() or not candidates:
            return "Analysis unavailable."

        try:
            # Format candidates
            candidates_text = ""
            for i, cand in enumerate(candidates, 1):
                name = cand.get('name', 'Unknown')
                path = cand.get('file_path', 'Unknown')
                code = self._optimize_token_usage(cand.get('code', ''))[:1000]
                candidates_text += f"Candidate {i}: {name} in {path}\nCode:\n{code}\n\n"

            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert developer.
Analyze the provided candidate functions in relation to the reported issue.
Provide a brief Technical Analysis explaining why these functions are relevant and how they might be contributing to the bug.
Do not just list them. Synthesize an explanation.
"""),
                ("human", """Issue: {title}
Description: {body}

{candidates_text}

Provide a concise technical analysis (2-3 paragraphs).""")
            ])

            chain = prompt | self.llm
            response = chain.invoke({
                "title": issue_title,
                "body": issue_body,
                "candidates_text": candidates_text
            })
            
            return response.content

        except Exception as e:
            logger.error(f"Error generating candidate analysis: {e}")
            return "Technical analysis generation failed."
