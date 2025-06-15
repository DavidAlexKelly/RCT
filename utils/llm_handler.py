# utils/llm_handler.py

from typing import List, Dict, Any, Optional
import re

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
        print(f"Initialized LLM with model: {self.model_config['name']} ({self.model_key})")
        
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
        Analyze document chunk for compliance issues and compliance points with enhanced citation validation.
        
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
            if detected_patterns:
                print(f"Detected patterns: {detected_patterns[:3]}")
        
        # Skip LLM for chunks marked as low-priority
        if not should_analyze:
            return {
                "issues": [],
                "compliance_points": [],
                "position": chunk_position,
                "text": doc_text,
                "should_analyze": False
            }
        
        # Extract content indicators and potential violations using regulation handler
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
            
            # If we have detected patterns from progressive analysis, convert them
            if detected_patterns:
                # Add them to potential violations for more comprehensive analysis
                for pattern in detected_patterns:
                    # Extract pattern name and indicator from the pattern string
                    if ":" in pattern:
                        parts = pattern.split(":", 1)
                        pattern_type = parts[0].strip()
                        indicator = parts[1].strip().strip("'")
                        
                        potential_violations.append({
                            "pattern": pattern_type,
                            "indicator": indicator,
                            "context": f"...{indicator}...",  # Simplified context
                            "related_refs": []  # No refs available from pattern matching
                        })
        
        # Format regulations using prompt manager
        formatted_regulations = ""
        if self.prompt_manager:
            # Use top regulations for analysis
            regs_to_use = regulations[:5]  # Limit to top 5 relevant regulations
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
            prompt = self._create_default_prompt(doc_text, chunk_position, formatted_regulations)
        
        # Get response from LLM (SINGLE CALL)
        response = self.llm.invoke(prompt)
        
        if self.debug:
            print(f"LLM response (first 200 chars): {response[:200]}...")
        
        # Parse response using regulation handler with document text validation
        result = {}
        if (self.prompt_manager and 
            hasattr(self.prompt_manager, 'regulation_handler') and
            hasattr(self.prompt_manager.regulation_handler, 'parse_llm_response')):
            
            # Use regulation handler's parsing with document text for citation validation
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
        
        # Debug: Report citation quality
        if self.debug:
            issues = result.get("issues", [])
            points = result.get("compliance_points", [])
            
            valid_citations = 0
            total_citations = 0
            
            for item in issues + points:
                citation = item.get("citation", "")
                if citation and citation != "No specific quote provided.":
                    total_citations += 1
                    # Quick check if citation looks like document text
                    if any(term in citation.lower() for term in ["data", "system", "user", "app", "project", "business"]):
                        valid_citations += 1
            
            if total_citations > 0:
                print(f"Citation quality: {valid_citations}/{total_citations} appear to be document text")
        
        return result
    
    def _format_regulations_simple(self, regulations: List[Dict]) -> str:
        """Simple regulation formatting fallback."""
        return "\n\n".join([
            f"REGULATION {i+1}: {reg.get('id', '')}\n{reg.get('text', '')}" 
            for i, reg in enumerate(regulations)
        ])
    
    def _create_default_prompt(self, text: str, section: str, regulations: str) -> str:
        """Create a default analysis prompt when no prompt manager is available."""
        return f"""You are an expert regulatory compliance auditor. Your task is to analyze this text section for compliance issues and points.

SECTION: {section}
DOCUMENT TEXT TO ANALYZE:
{text}

RELEVANT REGULATIONS:
{regulations}

🚨 CITATION RULES: ONLY quote from the DOCUMENT TEXT above, never from regulations.

INSTRUCTIONS:
1. Analyze this section for clear compliance issues based on the regulations provided.
2. For each issue, include a direct quote from the DOCUMENT TEXT only.
3. Format your response EXACTLY as shown in the example below.
4. Focus on clear violations rather than small technical details.

EXAMPLE REQUIRED FORMAT:
COMPLIANCE ISSUES:
1. The document states it will retain data indefinitely, violating storage limitation principles. "Retain all customer data indefinitely for long-term trend analysis."
2. Users cannot refuse data collection, violating consent requirements. "Users will be required to accept all data collection to use the app."

COMPLIANCE POINTS:
1. The document provides clear user notification about data usage. "Our implementation will use a simple banner stating 'By using this site, you accept our terms'."

If no issues are found, write "NO COMPLIANCE ISSUES DETECTED."
If no compliance points are found, write "NO COMPLIANCE POINTS DETECTED."
"""
    
    def _parse_response_simple(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Simple response parsing fallback when no regulation handler available."""
        result = {"issues": [], "compliance_points": []}
        
        # Remove code blocks
        response = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
        
        # Basic parsing for issues
        if "NO COMPLIANCE ISSUES DETECTED" not in response:
            issues_match = re.search(r'COMPLIANCE\s+ISSUES:?\s*\n(.*?)(?:COMPLIANCE\s+POINTS:|$)', 
                                   response, re.DOTALL | re.IGNORECASE)
            if issues_match:
                issues_text = issues_match.group(1)
                # Simple numbered item extraction
                for match in re.finditer(r'(?:^|\n)\s*\d+\.\s+(.+?)(?=(?:\n\s*\d+\.)|$)', issues_text, re.DOTALL):
                    item_text = match.group(1).strip()
                    
                    if len(item_text) < 10:  # Skip very short items
                        continue
                    
                    # Extract quote
                    citation = ""
                    quote_match = re.search(r'"([^"]+)"', item_text)
                    if quote_match:
                        citation = quote_match.group(0)
                    
                    # Extract regulation reference
                    regulation = "Unknown Regulation"
                    reg_patterns = [
                        r'\((?:(Article|Section|Rule|Standard|Requirement|Regulation|Part|Chapter)\s*)?(\d+(?:\.\d+)?(?:\(\d+\))?(?:\([a-z]\))?)\)',
                        r'\b(Article|Section|Rule|Standard|Requirement|Regulation|Part|Chapter)\s*(\d+(?:\.\d+)?(?:\(\d+\))?(?:\([a-z]\))?)\b'
                    ]
                    
                    for pattern in reg_patterns:
                        reg_match = re.search(pattern, item_text, re.IGNORECASE)
                        if reg_match:
                            ref_type = reg_match.group(1) if reg_match.group(1) else "Section"
                            ref_number = reg_match.group(2)
                            regulation = f"{ref_type} {ref_number}"
                            break
                    
                    # Clean description
                    description = item_text
                    if citation:
                        description = description.replace(citation, "").strip()
                    
                    result["issues"].append({
                        "issue": description,
                        "regulation": regulation,
                        "confidence": "Medium",
                        "citation": citation if citation else "No specific quote provided."
                    })
        
        # Basic parsing for compliance points
        if "NO COMPLIANCE POINTS DETECTED" not in response:
            points_match = re.search(r'COMPLIANCE\s+POINTS:?\s*\n(.*?)$', response, re.DOTALL | re.IGNORECASE)
            if points_match:
                points_text = points_match.group(1)
                for match in re.finditer(r'(?:^|\n)\s*\d+\.\s+(.+?)(?=(?:\n\s*\d+\.)|$)', points_text, re.DOTALL):
                    item_text = match.group(1).strip()
                    
                    if len(item_text) < 10:  # Skip very short items
                        continue
                    
                    # Extract quote
                    citation = ""
                    quote_match = re.search(r'"([^"]+)"', item_text)
                    if quote_match:
                        citation = quote_match.group(0)
                    
                    # Extract regulation reference
                    regulation = "Unknown Regulation"
                    reg_patterns = [
                        r'\((?:(Article|Section|Rule|Standard|Requirement|Regulation|Part|Chapter)\s*)?(\d+(?:\.\d+)?(?:\(\d+\))?(?:\([a-z]\))?)\)',
                        r'\b(Article|Section|Rule|Standard|Requirement|Regulation|Part|Chapter)\s*(\d+(?:\.\d+)?(?:\(\d+\))?(?:\([a-z]\))?)\b'
                    ]
                    
                    for pattern in reg_patterns:
                        reg_match = re.search(pattern, item_text, re.IGNORECASE)
                        if reg_match:
                            ref_type = reg_match.group(1) if reg_match.group(1) else "Section"
                            ref_number = reg_match.group(2)
                            regulation = f"{ref_type} {ref_number}"
                            break
                    
                    # Clean description
                    description = item_text
                    if citation:
                        description = description.replace(citation, "").strip()
                    
                    result["compliance_points"].append({
                        "point": description,
                        "regulation": regulation, 
                        "confidence": "Medium",
                        "citation": citation if citation else "No specific quote provided."
                    })
        
        return result