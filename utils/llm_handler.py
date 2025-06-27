"""
LLM Handler Module

Manages interaction with language models for compliance analysis.
Supports Ollama local models with array-based response parsing.
"""

import logging
from typing import List, Dict, Any, Optional
import re
import json

from config import RAGConfig, LLMConfig

logger = logging.getLogger(__name__)


class LLMHandler:
    """
    Handles LLM interactions for compliance analysis.
    
    Uses array-based response parsing for reliable output processing.
    Supports multiple model configurations and batch processing.
    """
    
    def __init__(self, model_config: Optional[Dict[str, Any]] = None, 
                 prompt_manager: Optional[Any] = None, debug: bool = False) -> None:
        """
        Initialize the LLM handler.
        
        Args:
            model_config: Model configuration dictionary
            prompt_manager: PromptManager instance for generating prompts
            debug: Whether to enable debug logging
        """
        self.debug = debug
        
        # Use default configuration if none provided
        if model_config is None:
            from config import MODELS, DEFAULT_MODEL
            self.model_config = MODELS[DEFAULT_MODEL]
            self.model_key = DEFAULT_MODEL
        else:
            self.model_config = model_config
            self.model_key = model_config.get("key", "custom")
        
        # Initialize the model
        try:
            from langchain_ollama import OllamaLLM as Ollama
            self.llm = Ollama(
                model=self.model_config["name"],
                temperature=self.model_config.get("temperature", 0.1)
            )
        except ImportError:
            raise ImportError("langchain-ollama package is required. "
                            "Install with: pip install langchain-ollama")
        
        logger.info(f"Initialized LLM: {self.model_config['name']} ({self.model_key})")
        if self.debug:
            logger.debug(f"RAG Articles Count: {RAGConfig.ARTICLES_COUNT}")
            logger.debug("Using array-based response parsing")
        
        # Set prompt manager
        self.prompt_manager = prompt_manager
    
    def get_batch_size(self) -> int:
        """Return the recommended batch size for this model."""
        return self.model_config.get("batch_size", 1)
    
    def invoke(self, prompt: str) -> str:
        """
        Direct LLM invocation method.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            Raw LLM response string
        """
        try:
            return self.llm.invoke(prompt)
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            raise
    
    def analyze_compliance(self, document_chunk: Dict[str, Any], 
                          regulations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze document chunk for compliance issues.
        
        Args:
            document_chunk: Dictionary containing chunk text and metadata
            regulations: List of relevant regulations
            
        Returns:
            Dictionary with compliance issues and metadata
        """
        # Extract text and metadata
        doc_text = document_chunk.get("text", "")
        chunk_position = document_chunk.get("position", "Unknown")
        should_analyze = document_chunk.get("should_analyze", True)
        
        logger.debug(f"Analyzing chunk: '{chunk_position}' (Analyze: {should_analyze})")
        
        # Skip LLM for chunks marked as low-priority
        if not should_analyze:
            return {
                "issues": [],
                "position": chunk_position,
                "text": doc_text,
                "should_analyze": False
            }
        
        # Extract content indicators and potential violations
        content_indicators = {}
        potential_violations = []
        
        if self.prompt_manager and hasattr(self.prompt_manager, 'regulation_handler'):
            handler = self.prompt_manager.regulation_handler
            
            # Extract content indicators
            if hasattr(handler, 'extract_content_indicators'):
                content_indicators = handler.extract_content_indicators(doc_text)
            
            # Extract potential violations
            if hasattr(handler, 'extract_potential_violations'):
                regulation_patterns = getattr(self.prompt_manager, 'regulation_patterns', '')
                potential_violations = handler.extract_potential_violations(
                    doc_text, regulation_patterns
                )
        
        # Format regulations using prompt manager
        formatted_regulations = self._format_regulations(regulations)
        
        # Generate the analysis prompt
        prompt = self._create_analysis_prompt(
            doc_text, chunk_position, formatted_regulations, 
            content_indicators, potential_violations
        )
        
        # Check prompt length
        if len(prompt) > LLMConfig.MAX_PROMPT_LENGTH:
            logger.warning(f"Prompt length ({len(prompt)}) exceeds maximum ({LLMConfig.MAX_PROMPT_LENGTH})")
        
        # Get response from LLM
        try:
            response = self.llm.invoke(prompt)
            logger.debug(f"LLM response length: {len(response)}")
        except Exception as e:
            logger.error(f"LLM analysis failed for chunk {chunk_position}: {e}")
            return {
                "issues": [],
                "position": chunk_position,
                "text": doc_text,
                "should_analyze": True,
                "error": str(e)
            }
        
        # Parse response
        result = self._parse_response(response, doc_text)
        
        # Add metadata to result
        result.update({
            "position": chunk_position,
            "text": doc_text,
            "should_analyze": True
        })
        
        # Add section info to issues
        for issue in result.get("issues", []):
            issue["section"] = chunk_position
        
        logger.debug(f"Found {len(result.get('issues', []))} compliance issues")
        
        return result
    
    def _format_regulations(self, regulations: List[Dict[str, Any]]) -> str:
        """Format regulations for inclusion in prompts."""
        if self.prompt_manager:
            # Use configurable number of articles
            regs_to_use = regulations[:RAGConfig.ARTICLES_COUNT]
            logger.debug(f"Using {len(regs_to_use)} regulation articles")
            return self.prompt_manager.format_regulations(regs_to_use)
        else:
            # Simple formatting fallback
            max_regs = min(len(regulations), RAGConfig.ARTICLES_COUNT)
            return "\n\n".join([
                f"{reg.get('id', '')}: {reg.get('text', '')[:200]}..." 
                for reg in regulations[:max_regs]
            ])
    
    def _create_analysis_prompt(self, text: str, section: str, regulations: str,
                               content_indicators: Dict[str, Any],
                               potential_violations: List[Dict[str, Any]]) -> str:
        """Create analysis prompt using prompt manager or fallback."""
        if self.prompt_manager:
            return self.prompt_manager.create_analysis_prompt(
                text, section, regulations, content_indicators,
                potential_violations
            )
        else:
            # Simple fallback prompt
            return self._create_simple_prompt(text, section, regulations)
    
    def _create_simple_prompt(self, text: str, section: str, regulations: str) -> str:
        """Create a simple analysis prompt as fallback."""
        return f"""Find compliance violations in this document section.

SECTION: {section}
DOCUMENT TEXT:
{text}

RELEVANT REGULATIONS:
{regulations}

Return violations as a JSON array. Each violation should be:
[description, regulation, quote_from_document]

Response format:
[
["Clear violation description", "Article X", "exact quote from document"],
["Another violation", "Article Y", "another exact quote"]
]

If no violations found, return: []
"""
    
    def _parse_response(self, response: str, document_text: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """Parse LLM response using regulation handler or fallback."""
        if (self.prompt_manager and 
            hasattr(self.prompt_manager, 'regulation_handler')):
            # Use regulation handler's parsing
            return self.prompt_manager.regulation_handler.parse_llm_response(
                response, document_text
            )
        else:
            # Fall back to simple array parsing
            return self._parse_array_response(response)
    
    def _parse_array_response(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse array-based LLM response as fallback."""
        logger.debug("Using fallback array parser")
        
        result = {"issues": []}
        
        try:
            # Extract JSON array from response
            array_text = self._extract_json_array(response)
            
            if not array_text:
                logger.debug("No JSON array found in response")
                return result
            
            # Parse JSON
            violations = json.loads(array_text)
            logger.debug(f"Parsed {len(violations)} violations")
            
            # Convert to standard format
            for violation in violations:
                if isinstance(violation, list) and len(violation) >= 3:
                    issue_desc = str(violation[0]).strip()
                    regulation = str(violation[1]).strip()
                    citation = str(violation[2]).strip()
                    
                    if len(issue_desc) > 5:  # Meaningful description
                        result["issues"].append({
                            "issue": issue_desc,
                            "regulation": regulation,
                            "citation": f'"{citation}"' if citation and not citation.startswith('"') else citation
                        })
            
        except json.JSONDecodeError as e:
            logger.debug(f"JSON parsing failed: {e}, attempting regex fallback")
            result = self._fallback_array_parsing(response)
        except Exception as e:
            logger.error(f"Array parsing error: {e}")
        
        return result
    
    def _extract_json_array(self, response: str) -> str:
        """Extract JSON array from response text."""
        # Find the first opening bracket
        start = response.find('[')
        if start == -1:
            return ""
        
        # Find the matching closing bracket
        bracket_count = 0
        end = -1
        
        for i in range(start, len(response)):
            if response[i] == '[':
                bracket_count += 1
            elif response[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end = i
                    break
        
        if end == -1:
            return ""
        
        return response[start:end + 1]
    
    def _fallback_array_parsing(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Fallback parsing using regex patterns."""
        result = {"issues": []}
        
        # Look for array-like patterns
        patterns = [
            r'\[\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"\s*\]',
            r"\[\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\s*\]"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                if len(match) == 3 and len(match[0].strip()) > 5:
                    result["issues"].append({
                        "issue": match[0].strip(),
                        "regulation": match[1].strip(),
                        "citation": f'"{match[2].strip()}"'
                    })
        
        if result["issues"]:
            logger.debug(f"Fallback parsing found {len(result['issues'])} issues")
        
        return result