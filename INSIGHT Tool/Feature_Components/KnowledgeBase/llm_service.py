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
            LLM_MODEL_NAME = os.getenv('LLM_MODEL_NAME', 'gemini-2.0-flash')
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
