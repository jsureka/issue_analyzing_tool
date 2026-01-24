"""
LLM Service - Interface for Large Language Model interactions
Uses Google's Gemini models for code analysis and patch generation
"""

import logging
import os
import time
import functools
import re
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

    # NOTE: generate_patch() has been removed from LLMService.
    # Patch generation is now handled by BugLocalizationAgent.patch_generator_node()
    # which implements proper Chain-of-Thought reasoning based on:
    # - ThinkRepair (Yin et al., ISSTA 2024)
    # - SCoT (Li et al., TOSEM 2025)

    
    def retry_with_backoff(func):
        """Decorator for retrying with exponential backoff"""
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            max_retries = 8 
            base_delay = 4
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    is_rate_limit = "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg
                    
                    if is_rate_limit:
                        if attempt == max_retries - 1:
                            logger.error(f"Max retries ({max_retries}) exceeded for rate limit.")
                            raise
                        
                        wait_time = 0
                        match = re.search(r"retry in (\d+(\.\d+)?)s", error_msg)
                        if match:
                            wait_time = float(match.group(1))
                        else:
                            match = re.search(r"seconds:\s*(\d+)", error_msg)
                            if match:
                                wait_time = float(match.group(1))
                        
                        if wait_time > 0:
                            delay = wait_time + 2
                        else:
                            delay = base_delay * (2 ** attempt)
                            
                        logger.warning(f"Rate limit hit. Retrying in {delay:.2f}s... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(delay)
                    else:
                        raise
            return None
        return wrapper



    @retry_with_backoff
    def get_response(self, prompt: str, system_message: str = None, json_mode: bool = False) -> str:
        """
        Get a simple text response from the LLM.
        
        Args:
            prompt: User prompt
            system_message: System instruction
            json_mode: Whether to expect/enforce JSON output (handled via prompt usually, but can enable model flags if supported)
            
        Returns:
            Response string
        """
        if not self.is_available():
            return "LLM unavailable"
            
        try:
            # Use ("human", "{user_input}") and pass input in invoke to avoid template issues
            
            # Use ("human", "{user_input}") and pass input in invoke to avoid template issues
            
            safe_messages = []
            if system_message:
                # specific to system message which might be static
                safe_system_msg = system_message.replace('{', '{{').replace('}', '}}')
                safe_messages.append(("system", safe_system_msg))
            
            safe_messages.append(("human", "{user_input}"))
            
            prompt_template = ChatPromptTemplate.from_messages(safe_messages)
            chain = prompt_template | self.llm
            
            response = chain.invoke({"user_input": prompt})
            return response.content
        except Exception as e:
            logger.error(f"Error getting response: {e}")
            return f"Error executing LLM request: {str(e)}"

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
