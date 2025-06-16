# utils/llm_handler.py

from typing import List, Dict, Any, Optional
import re

# Import centralized performance configuration
from config.llm_performance import RAGConfig, LLMConfig

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
            from config.models import MODELS, DEFAULT_MODEL
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
        Analyze document chunk for compliance issues and compliance points.
        
        Args:
            document_chunk: Dictionary containing chunk text and metadata
            regulations: List of relevant regulations
            
        Returns:
            Dictionary with issues and compliance points
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
                "compliance_points": [],
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
            # 🔧 KEY CHANGE: Use configurable number of articles instead of hardcoded 3
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
        
        # 🔧 Check prompt length against configuration
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
            
            # Use regulation handler's parsing with citation validation
            result = self.prompt_manager.regulation_handler.parse_llm_response(response, doc_text)
        else:
            # Fall back to simple parsing
            result = self._parse_response_simple(response)
        
        # Add metadata to result
        result["position"] = chunk_position
        result["text"] = doc_text
        result["should_analyze"] = True
        
        # Add section info to issues and compliance points
        for issue in result.get("issues", []):
            issue["section"] = chunk_position
            
        for point in result.get("compliance_points", []):
            point["section"] = chunk_position
        
        if self.debug:
            issues = result.get("issues", [])
            points = result.get("compliance_points", [])
            print(f"Found {len(issues)} issues and {len(points)} compliance points")
        
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
        """Create a simple analysis prompt when no prompt manager is available."""
        return f"""Analyze this document section for regulatory compliance.

SECTION: {section}
DOCUMENT TEXT:
{text}

RELEVANT REGULATIONS:
{regulations}

Find violations and compliance strengths in the document text.

FORMAT:
COMPLIANCE ISSUES:
1. Brief issue description. "exact quote from document"

COMPLIANCE POINTS:
1. Brief compliance strength. "exact quote from document"

RULES:
- Only quote from the document text above
- Include regulation references where possible
- Write "NO COMPLIANCE ISSUES DETECTED" if none found
- Write "NO COMPLIANCE POINTS DETECTED" if none found
"""
    
    def _parse_response_simple(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Simple response parsing fallback with configurable validation."""
        result = {"issues": [], "compliance_points": []}
        
        # Remove code blocks
        response = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
        
        # Parse issues
        if "NO COMPLIANCE ISSUES DETECTED" not in response:
            issues_match = re.search(r'COMPLIANCE\s+ISSUES:?\s*\n(.*?)(?:COMPLIANCE\s+POINTS:|$)', 
                                   response, re.DOTALL | re.IGNORECASE)
            if issues_match:
                issues_text = issues_match.group(1)
                result["issues"] = self._parse_items_simple(issues_text, "issue")
        
        # Parse compliance points
        if "NO COMPLIANCE POINTS DETECTED" not in response:
            points_match = re.search(r'COMPLIANCE\s+POINTS:?\s*\n(.*?)$', 
                                   response, re.DOTALL | re.IGNORECASE)
            if points_match:
                points_text = points_match.group(1)
                result["compliance_points"] = self._parse_items_simple(points_text, "point")
        
        return result
    
    def _parse_items_simple(self, text: str, item_type: str) -> List[Dict[str, Any]]:
        """Simple item parsing with configurable confidence scoring."""
        items = []
        
        item_pattern = re.compile(r'(?:^|\n)\s*(\d+)\.\s+(.*?)(?=(?:\n\s*\d+\.)|$)', re.DOTALL)
        
        for match in item_pattern.finditer(text):
            item_text = match.group(2).strip()
            
            if len(item_text) < 10:
                continue
            
            # Extract quote with length validation
            citation = ""
            quote_match = re.search(r'"([^"]+)"', item_text)
            if quote_match:
                quote = quote_match.group(1)
                # 🔧 Use configurable citation length requirements
                if LLMConfig.CITATION_MIN_LENGTH <= len(quote) <= LLMConfig.CITATION_MAX_LENGTH:
                    citation = f'"{quote}"'
                else:
                    citation = "No specific quote provided."
            else:
                citation = "No specific quote provided."
            
            # Extract regulation
            regulation = "Unknown Regulation"
            reg_match = re.search(r'Article\s*(\d+)', item_text, re.IGNORECASE)
            if reg_match:
                regulation = f"Article {reg_match.group(1)}"
            
            # 🔧 Use configurable confidence scoring
            confidence = self._determine_confidence_simple(item_text, citation)
            
            # Clean description
            description = item_text
            if citation != "No specific quote provided.":
                description = description.replace(citation, "").strip()
            
            items.append({
                item_type: description,
                "regulation": regulation,
                "confidence": confidence,
                "citation": citation
            })
        
        return items
    
    def _determine_confidence_simple(self, item_text: str, citation: str) -> str:
        """Determine confidence using configurable terms."""
        text_lower = item_text.lower()
        
        # Check for high confidence terms
        has_high_terms = any(term in text_lower for term in LLMConfig.HIGH_CONFIDENCE_TERMS)
        
        # Check for low confidence terms  
        has_low_terms = any(term in text_lower for term in LLMConfig.LOW_CONFIDENCE_TERMS)
        
        # Check citation quality
        has_good_citation = citation != "No specific quote provided." and len(citation) > 20
        
        if has_high_terms and has_good_citation:
            return "High"
        elif has_low_terms:
            return "Low"
        else:
            return "Medium"