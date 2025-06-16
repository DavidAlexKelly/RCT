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
        
        # Use default configuration if none provided
        if model_config is None:
            from config import MODELS, DEFAULT_MODEL
            self.model_config = MODELS[DEFAULT_MODEL]
            self.model_key = DEFAULT_MODEL
        else:
            self.model_config = model_config
            self.model_key = model_config.get("key", "custom")
        
        # Initialize the model
        from langchain_ollama import OllamaLLM as Ollama
        self.llm = Ollama(
            model=self.model_config["name"],
            temperature=self.model_config.get("temperature", 0.1)
        )
        
        if self.debug:
            print(f"Initialized LLM with model: {self.model_config['name']} ({self.model_key})")
            print(f"RAG Articles Count: {RAGConfig.ARTICLES_COUNT}")
            print("Using array-based response parsing")
        
        # Set prompt manager
        self.prompt_manager = prompt_manager
    
    def get_batch_size(self) -> int:
        """Return the recommended batch size for this model."""
        return self.model_config.get("batch_size", 1)
    
    def invoke(self, prompt: str) -> str:
        """Direct LLM invocation method."""
        return self.llm.invoke(prompt)
    
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
        # Extract text and metadata
        doc_text = document_chunk.get("text", "")
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
        formatted_regulations = ""
        if self.prompt_manager:
            # Use configurable number of articles
            regs_to_use = regulations[:RAGConfig.ARTICLES_COUNT]
            if self.debug:
                print(f"Using {len(regs_to_use)} regulation articles (configured: {RAGConfig.ARTICLES_COUNT})")
            formatted_regulations = self.prompt_manager.format_regulations(regs_to_use)
        else:
            # Simple formatting if no prompt manager
            formatted_regulations = self._format_regulations_simple(regulations)
        
        # Generate the analysis prompt
        prompt = ""
        if self.prompt_manager:
            prompt = self.prompt_manager.create_analysis_prompt(
                doc_text, 
                chunk_position, 
                formatted_regulations, 
                content_indicators,
                potential_violations
            )
        else:
            # Create a minimal prompt if no manager
            prompt = self._create_simple_prompt(doc_text, chunk_position, formatted_regulations)
        
        # Check prompt length
        if len(prompt) > LLMConfig.MAX_PROMPT_LENGTH:
            if self.debug:
                print(f"Warning: Prompt length ({len(prompt)}) exceeds max ({LLMConfig.MAX_PROMPT_LENGTH})")
        
        # Get response from LLM
        response = self.llm.invoke(prompt)
        
        if self.debug:
            print(f"LLM response: {response[:200]}...")
        
        # Parse response using regulation handler or fallback
        result = {}
        if (self.prompt_manager and 
            hasattr(self.prompt_manager, 'regulation_handler')):
            
            # Use regulation handler's array parsing
            result = self.prompt_manager.regulation_handler.parse_llm_response(response, doc_text)
        else:
            # Fall back to simple array parsing
            result = self._parse_array_response(response)
        
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
    
    def _format_regulations_simple(self, regulations: List[Dict]) -> str:
        """Simple regulation formatting fallback."""
        # Use configurable number of articles
        max_regs = min(len(regulations), RAGConfig.ARTICLES_COUNT)
        return "\n\n".join([
            f"{reg.get('id', '')}: {reg.get('text', '')[:200]}..." 
            for reg in regulations[:max_regs]
        ])
    
    def _create_simple_prompt(self, text: str, section: str, regulations: str) -> str:
        """Create a simple prompt that requests array format."""
        
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
    
    def _parse_array_response(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse array-based LLM response - simple and reliable."""
        
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
                return result
            
            if self.debug:
                print(f"DEBUG: Extracted array: {array_text}")
            
            # Parse JSON
            violations = json.loads(array_text)
            
            if self.debug:
                print(f"DEBUG: Parsed {len(violations)} violations")
            
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
                        
                        if self.debug:
                            print(f"  Added: {issue_desc[:40]}... [{regulation}]")
            
        except json.JSONDecodeError as e:
            if self.debug:
                print(f"DEBUG: JSON parsing failed: {e}")
                print("DEBUG: Attempting regex fallback...")
            
            # Fallback to regex extraction
            result = self._fallback_array_parsing(response)
            
        except Exception as e:
            if self.debug:
                print(f"DEBUG: Array parsing error: {e}")
        
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