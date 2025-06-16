# utils/llm_handler.py

from typing import List, Dict, Any, Optional
import re

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
            print(f"Citation Validation: {'Enabled' if LLMConfig.VALIDATE_CITATIONS else 'Disabled'}")
        
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
        Analyze document chunk for compliance issues only.
        
        Args:
            document_chunk: Dictionary containing chunk text and metadata
            regulations: List of relevant regulations
            
        Returns:
            Dictionary with issues only
        """
        # Extract text and metadata
        doc_text = document_chunk.get("text", "")
        chunk_position = document_chunk.get("position", "Unknown")
        should_analyze = document_chunk.get("should_analyze", True)
        detected_patterns = document_chunk.get("detected_patterns", [])
        
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
            print(f"LLM response (first 100 chars): {response[:100]}...")
        
        # Parse response using regulation handler
        result = {}
        if (self.prompt_manager and 
            hasattr(self.prompt_manager, 'regulation_handler')):
            
            # Use regulation handler's parsing (simplified - no validation)
            result = self.prompt_manager.regulation_handler.parse_llm_response(response, doc_text)
        else:
            # Fall back to simple parsing
            result = self._parse_response_simple(response)
        
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
        """Create a simple analysis prompt that prevents artifacts."""
        
        # 🔧 FIXED PROMPT - Prevents instruction leakage and markdown
        return f"""You are a regulatory compliance expert. Analyze this document section for violations.

SECTION: {section}
DOCUMENT TEXT:
{text}

RELEVANT REGULATIONS:
{regulations}

TASK: Find regulatory compliance violations in the document text above.

RESPONSE FORMAT:
COMPLIANCE ISSUES:
1. Issue description violating [regulation]. "exact quote from document"
2. Another issue description violating [regulation]. "exact quote from document"

IMPORTANT CONSTRAINTS:
- Use plain text only (no bold, italic, or markdown formatting)
- Do not repeat these instructions in your response
- Only quote text that appears in the DOCUMENT TEXT above
- Include regulation references where possible
- If no violations found, write: "NO COMPLIANCE ISSUES DETECTED"

CONFIDENCE LEVELS: Use High for clear violations, Medium for likely issues, Low for uncertain violations.
"""
    
    def _parse_response_simple(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Simple response parsing fallback - should be cleaner now."""
        result = {"issues": []}
        
        # Light cleanup - should be minimal with better prompts
        response = self._light_cleanup(response)
        
        # Parse issues only
        if "NO COMPLIANCE ISSUES DETECTED" not in response:
            issues_match = re.search(r'COMPLIANCE\s+ISSUES:?\s*\n(.*?)$', 
                                   response, re.DOTALL | re.IGNORECASE)
            if issues_match:
                issues_text = issues_match.group(1)
                result["issues"] = self._parse_items_simple(issues_text, "issue")
        
        return result
    
    def _light_cleanup(self, response: str) -> str:
        """Light cleanup - should be minimal with better prompts."""
        
        # Remove code blocks (if any)
        response = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
        
        # Basic whitespace normalization
        response = re.sub(r'\n\s*\n\s*\n+', '\n\n', response)
        response = re.sub(r' +', ' ', response)
        
        return response.strip()
    
    def _parse_items_simple(self, text: str, item_type: str) -> List[Dict[str, Any]]:
        """Simple item parsing - should be cleaner now."""
        items = []
        
        item_pattern = re.compile(r'(?:^|\n)\s*(\d+)\.\s+(.*?)(?=(?:\n\s*\d+\.)|$)', re.DOTALL)
        
        for match in item_pattern.finditer(text):
            item_text = match.group(2).strip()
            
            if len(item_text) < 5:  # Very minimal length requirement
                continue
            
            # Extract quote - simple, no validation
            citation = self._extract_quote_simple(item_text)
            
            # Extract regulation
            regulation = self._extract_regulation_simple(item_text)
            
            # Simple confidence based on keywords only
            confidence = self._determine_confidence_simple(item_text)
            
            # Clean description
            description = self._clean_description_simple(item_text, citation)
            
            if len(description) < 3:
                continue
            
            items.append({
                item_type: description,
                "regulation": regulation,
                "confidence": confidence,
                "citation": citation
            })
        
        return items
    
    def _extract_quote_simple(self, text: str) -> str:
        """Simple quote extraction - no validation."""
        # Look for quoted text
        quote_patterns = [r'"([^"]+)"', r"'([^']+)'"]
        
        for pattern in quote_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Return the longest quote
                longest_quote = max(matches, key=len)
                if len(longest_quote) > 3:
                    return f'"{longest_quote}"'
        
        return "No specific quote provided."
    
    def _extract_regulation_simple(self, text: str) -> str:
        """Simple regulation extraction."""
        # Look for Article references
        reg_match = re.search(r'Article\s*(\d+)', text, re.IGNORECASE)
        if reg_match:
            return f"Article {reg_match.group(1)}"
        
        return "Unknown Regulation"
    
    def _determine_confidence_simple(self, text: str) -> str:
        """Simple confidence determination - no citation validation."""
        text_lower = text.lower()
        
        # High confidence terms
        if any(term in text_lower for term in LLMConfig.HIGH_CONFIDENCE_TERMS):
            return "High"
        
        # Low confidence terms  
        elif any(term in text_lower for term in LLMConfig.LOW_CONFIDENCE_TERMS):
            return "Low"
        
        else:
            return "Medium"
    
    def _clean_description_simple(self, text: str, citation: str) -> str:
        """Clean the description by removing the citation."""
        description = text
        
        # Remove citation from description
        if citation and citation != "No specific quote provided.":
            citation_clean = citation.strip('"').strip("'")
            description = description.replace(citation, "").replace(citation_clean, "")
        
        # Clean up whitespace and formatting
        description = re.sub(r'\s+', ' ', description)
        description = description.strip()
        
        # Remove leading/trailing punctuation
        description = re.sub(r'^[^\w]+', '', description)
        description = re.sub(r'[^\w]+$', '', description)
        
        # Ensure it ends with a period
        if description and not description.endswith('.'):
            description += '.'
        
        return description