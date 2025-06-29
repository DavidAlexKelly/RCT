# utils/llm_handler.py

from typing import List, Dict, Any, Optional
import re
import json

# Import centralized performance configuration
from config import RAGConfig, LLMConfig

class LLMHandler:
    def __init__(self, model_config=None, prompt_manager=None, debug=False):
        """
        Initialize the LLM handler with model configuration.
        
        Args:
            model_config: Dictionary with model configuration
            prompt_manager: PromptManager instance for generating prompts
            debug: Whether to print detailed debug information
        """
        self.debug = debug
        
        # Validate and set model configuration
        if model_config is None:
            from config import MODELS, DEFAULT_MODEL
            if DEFAULT_MODEL not in MODELS:
                available_models = list(MODELS.keys())
                raise ValueError(f"Default model '{DEFAULT_MODEL}' not found in MODELS configuration. Available: {available_models}")
            self.model_config = MODELS[DEFAULT_MODEL]
            self.model_key = DEFAULT_MODEL
        else:
            if not isinstance(model_config, dict):
                raise ValueError("model_config must be a dictionary")
            
            required_keys = ['name']
            missing_keys = [key for key in required_keys if key not in model_config]
            if missing_keys:
                raise ValueError(f"model_config missing required keys: {missing_keys}")
            
            self.model_config = model_config
            self.model_key = model_config.get("key", "custom")
        
        # Validate prompt manager
        if prompt_manager is None:
            raise ValueError("prompt_manager is required and cannot be None")
        
        if not hasattr(prompt_manager, 'create_analysis_prompt'):
            raise ValueError("prompt_manager must have create_analysis_prompt method")
        
        # Initialize the model
        try:
            from langchain_ollama import OllamaLLM as Ollama
            self.llm = Ollama(
                model=self.model_config["name"],
                temperature=self.model_config.get("temperature", 0.1)
            )
        except ImportError as e:
            raise RuntimeError(f"Failed to import Ollama: {e}. Make sure langchain_ollama is installed.")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Ollama with model '{self.model_config['name']}': {e}")
        
        if self.debug:
            print(f"Initialized LLM with model: {self.model_config['name']} ({self.model_key})")
            print(f"RAG Articles Count: {RAGConfig.ARTICLES_COUNT}")
            print("Using array-based response parsing")
        
        # Set prompt manager
        self.prompt_manager = prompt_manager
    
    def get_batch_size(self) -> int:
        """Return the recommended batch size for this model."""
        batch_size = self.model_config.get("batch_size", 1)
        if not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError(f"Invalid batch_size in model config: {batch_size}")
        return batch_size
    
    def invoke(self, prompt: str) -> str:
        """Direct LLM invocation method with validation."""
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        if len(prompt) > LLMConfig.MAX_PROMPT_LENGTH:
            raise ValueError(f"Prompt too long ({len(prompt)} chars). Maximum: {LLMConfig.MAX_PROMPT_LENGTH}")
        
        try:
            response = self.llm.invoke(prompt)
            if not response:
                raise RuntimeError("LLM returned empty response")
            return response
        except Exception as e:
            raise RuntimeError(f"LLM invocation failed: {e}")
    
    def analyze_compliance(self, document_chunk: Dict[str, Any], 
                           regulations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze document chunk for compliance issues using array-based responses.
        
        Args:
            document_chunk: Dictionary containing chunk text and metadata
            regulations: List of relevant regulations
            
        Returns:
            Dictionary with issues in standard format
        """
        # Validate inputs
        if not document_chunk:
            raise ValueError("document_chunk cannot be empty")
        
        if not isinstance(document_chunk, dict):
            raise ValueError("document_chunk must be a dictionary")
        
        doc_text = document_chunk.get("text", "")
        if not doc_text or not doc_text.strip():
            raise ValueError("document_chunk missing text content or text is empty")
        
        if not regulations:
            raise ValueError("regulations list cannot be empty")
        
        if not isinstance(regulations, list):
            raise ValueError("regulations must be a list")
        
        # Extract metadata
        chunk_position = document_chunk.get("position", "Unknown")
        should_analyze = document_chunk.get("should_analyze", True)
        
        if self.debug:
            print(f"\nAnalyzing chunk: '{chunk_position}' (Analyze: {should_analyze})")
            print(f"Text (first 50 chars): '{doc_text[:50]}...'")
        
        # Skip LLM for chunks marked as low-priority
        if not should_analyze:
            return {
                "issues": [],
                "position": chunk_position,
                "text": doc_text,
                "should_analyze": False
            }
        
        # Extract content indicators using regulation handler
        content_indicators = {}
        potential_violations = []
        
        if not self.prompt_manager:
            raise RuntimeError("prompt_manager is None - cannot proceed with analysis")
        
        if hasattr(self.prompt_manager, 'regulation_handler') and self.prompt_manager.regulation_handler:
            handler = self.prompt_manager.regulation_handler
            
            # Extract content indicators
            if hasattr(handler, 'extract_content_indicators'):
                try:
                    content_indicators = handler.extract_content_indicators(doc_text)
                except Exception as e:
                    if self.debug:
                        print(f"Warning: Failed to extract content indicators: {e}")
                    content_indicators = {}
            
            # Extract potential violations
            if hasattr(handler, 'extract_potential_violations'):
                try:
                    regulation_patterns = getattr(self.prompt_manager, 'regulation_patterns', '')
                    potential_violations = handler.extract_potential_violations(
                        doc_text, regulation_patterns
                    )
                except Exception as e:
                    if self.debug:
                        print(f"Warning: Failed to extract potential violations: {e}")
                    potential_violations = []
        
        # Format regulations using prompt manager
        try:
            # Use configurable number of articles
            regs_to_use = regulations[:RAGConfig.ARTICLES_COUNT]
            if self.debug:
                print(f"Using {len(regs_to_use)} regulation articles (configured: {RAGConfig.ARTICLES_COUNT})")
            formatted_regulations = self.prompt_manager.format_regulations(regs_to_use)
        except Exception as e:
            raise RuntimeError(f"Failed to format regulations: {e}")
        
        # Generate the analysis prompt
        try:
            prompt = self.prompt_manager.create_analysis_prompt(
                doc_text, 
                chunk_position, 
                formatted_regulations, 
                content_indicators,
                potential_violations
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create analysis prompt: {e}")
        
        # Check prompt length
        if len(prompt) > LLMConfig.MAX_PROMPT_LENGTH:
            if self.debug:
                print(f"Warning: Prompt length ({len(prompt)}) exceeds max ({LLMConfig.MAX_PROMPT_LENGTH})")
            # Truncate regulations if prompt is too long
            truncated_regs = regs_to_use[:max(1, len(regs_to_use)//2)]
            if self.debug:
                print(f"Truncating to {len(truncated_regs)} regulations")
            formatted_regulations = self.prompt_manager.format_regulations(truncated_regs)
            prompt = self.prompt_manager.create_analysis_prompt(
                doc_text, chunk_position, formatted_regulations, 
                content_indicators, potential_violations
            )
        
        # Get response from LLM
        try:
            response = self.llm.invoke(prompt)
        except Exception as e:
            raise RuntimeError(f"LLM analysis failed for chunk '{chunk_position}': {e}")
        
        if self.debug:
            print(f"LLM response: {response[:200]}...")
        
        # Parse response using regulation handler or fallback
        try:
            if (self.prompt_manager and 
                hasattr(self.prompt_manager, 'regulation_handler') and
                self.prompt_manager.regulation_handler):
                
                # Use regulation handler's array parsing
                result = self.prompt_manager.regulation_handler.parse_llm_response(response, doc_text)
            else:
                # Fall back to simple array parsing
                result = self._parse_array_response(response)
        except Exception as e:
            raise RuntimeError(f"Failed to parse LLM response for chunk '{chunk_position}': {e}")
        
        # Add metadata to result
        result["position"] = chunk_position
        result["text"] = doc_text
        result["should_analyze"] = True
        
        # Add section info to issues
        for issue in result.get("issues", []):
            issue["section"] = chunk_position
        
        if self.debug:
            issues = result.get("issues", [])
            print(f"Found {len(issues)} compliance issues")
            for i, issue in enumerate(issues):
                print(f"  Issue {i+1}: {issue.get('issue', 'Unknown')[:50]}... [{issue.get('regulation', 'Unknown')}]")
        
        return result
    
    def _parse_array_response(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse array-based LLM response - simple and reliable."""
        
        if not response or not response.strip():
            raise ValueError("LLM response is empty")
        
        if self.debug:
            print("=" * 50)
            print("DEBUG: Base Array Parser")
            print(f"Response: {response}")
            print("=" * 50)
        
        result = {"issues": []}
        
        try:
            # Extract JSON array from response
            array_text = self._extract_json_array(response)
            
            if not array_text:
                if self.debug:
                    print("DEBUG: No JSON array found in response")
                # Check if response indicates no issues
                if any(phrase in response.lower() for phrase in ["no compliance issues", "no violations", "[]"]):
                    return result
                else:
                    raise ValueError("Could not find JSON array in LLM response")
            
            if self.debug:
                print(f"DEBUG: Extracted array: {array_text}")
            
            # Parse JSON
            violations = json.loads(array_text)
            
            if not isinstance(violations, list):
                raise ValueError(f"Expected JSON array, got {type(violations).__name__}")
            
            if self.debug:
                print(f"DEBUG: Parsed {len(violations)} violations")
            
            # Convert to standard format
            for i, violation in enumerate(violations):
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
                        
                        if self.debug:
                            print(f"  Added: {issue_desc[:40]}... [{regulation}]")
                    else:
                        if self.debug:
                            print(f"  Skipped issue {i+1}: description too short")
                else:
                    if self.debug:
                        print(f"  Skipped violation {i+1}: invalid format {violation}")
            
        except json.JSONDecodeError as e:
            if self.debug:
                print(f"DEBUG: JSON parsing failed: {e}")
                print("DEBUG: Attempting regex fallback...")
            
            # Fallback to regex extraction
            result = self._fallback_array_parsing(response)
            
        except Exception as e:
            if self.debug:
                print(f"DEBUG: Array parsing error: {e}")
            raise RuntimeError(f"Failed to parse LLM response: {e}")
        
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
        
        if self.debug and result["issues"]:
            print(f"DEBUG: Fallback found {len(result['issues'])} issues")
        
        return result