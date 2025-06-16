# utils/regulation_handler_base.py

import re
from typing import Dict, Any, List, Optional

class RegulationHandlerBase:
    """Framework-agnostic base class with improved prompts to prevent artifacts."""
    
    def __init__(self, debug=False):
        """Initialize the regulation handler."""
        self.debug = debug
    
    def extract_content_indicators(self, text: str) -> Dict[str, str]:
        """Extract content indicators from text - framework agnostic."""
        # Use generic terms that apply across regulation frameworks
        indicators = {
            "has_entity_data": "Yes" if re.search(r'\b(information|data|record|file|database|document)\b', text, re.I) else "No",
            "has_collection": "Yes" if re.search(r'\b(collect|gather|obtain|capture|record|store|maintain)\b', text, re.I) else "No",
            "has_sharing": "Yes" if re.search(r'\b(share|transfer|disclose|send|provide|distribute|exchange)\b', text, re.I) else "No",
            "has_retention": "Yes" if re.search(r'\b(retain|store|keep|save|archive|delete|destroy|dispose)\b', text, re.I) else "No",
            "has_agreement": "Yes" if re.search(r'\b(agreement|consent|approve|accept|authorize|permit|allow)\b', text, re.I) else "No",
            "has_requirements": "Yes" if re.search(r'\b(requirement|obligation|standard|rule|regulation|policy)\b', text, re.I) else "No",
            "has_automated": "Yes" if re.search(r'\b(automated|automatic|algorithm|system|process|procedure)\b', text, re.I) else "No",
            "has_sensitive": "Yes" if re.search(r'\b(sensitive|confidential|restricted|classified|protected)\b', text, re.I) else "No"
        }
        return indicators
    
    def extract_potential_violations(self, text: str, patterns_text: str) -> List[Dict[str, Any]]:
        """Extract potential violation patterns from text."""
        if not patterns_text:
            return []
        
        violations = []
        
        # Parse pattern blocks from common_patterns.txt
        pattern_blocks = patterns_text.split('\n\n')
        for block in pattern_blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
            
            pattern_name, description, indicators, related_refs = self._parse_pattern_block(lines)
            
            if pattern_name and indicators:
                for indicator in indicators:
                    if indicator.lower() in text.lower():
                        violations.append({
                            "pattern": pattern_name,
                            "description": description,
                            "indicator": indicator,
                            "context": self._get_context(text, indicator),
                            "related_refs": related_refs
                        })
        
        return violations
    
    def parse_llm_response(self, response: str, document_text: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """Parse LLM response - compliance issues only."""
        # Try simplified parsing first (if handler has it)
        if hasattr(self, 'parse_llm_response_simple'):
            return self.parse_llm_response_simple(response, document_text)
        
        # Fallback to basic parsing
        return self._parse_response_basic(response)
    
    def _parse_response_basic(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Basic response parsing fallback - should be cleaner now."""
        result = {"issues": []}
        
        # Light cleanup - should be minimal with better prompts
        response = self._light_cleanup(response)
        
        # Parse issues only
        if "NO COMPLIANCE ISSUES DETECTED" not in response:
            issues_match = re.search(r'COMPLIANCE\s+ISSUES:?\s*\n(.*?)$', 
                                   response, re.DOTALL | re.IGNORECASE)
            if issues_match:
                issues_text = issues_match.group(1)
                result["issues"] = self._parse_items_basic(issues_text, "issue")
        
        return result
    
    def _light_cleanup(self, response: str) -> str:
        """Light cleanup - should be minimal with better prompts."""
        
        # Remove code blocks (if any)
        response = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
        
        # Basic whitespace normalization
        response = re.sub(r'\n\s*\n\s*\n+', '\n\n', response)
        response = re.sub(r' +', ' ', response)
        
        return response.strip()
    
    def _parse_items_basic(self, text: str, item_type: str) -> List[Dict[str, Any]]:
        """Basic item parsing - should be cleaner now."""
        items = []
        
        item_pattern = re.compile(r'(?:^|\n)\s*(\d+)\.\s+(.*?)(?=(?:\n\s*\d+\.)|$)', re.DOTALL)
        
        for match in item_pattern.finditer(text):
            item_text = match.group(2).strip()
            
            if len(item_text) < 5:  # Minimal length check
                continue
            
            # Extract quote - simple
            citation = self._extract_quote_basic(item_text)
            
            # Extract regulation - framework agnostic
            regulation = self._extract_regulation_basic(item_text)
            
            # Simple confidence
            confidence = self._determine_confidence_basic(item_text)
            
            # Clean description
            description = self._clean_description_basic(item_text, citation)
            
            items.append({
                item_type: description,
                "regulation": regulation,
                "confidence": confidence,
                "citation": citation
            })
        
        return items
    
    def _extract_quote_basic(self, text: str) -> str:
        """Basic quote extraction - no validation."""
        quote_match = re.search(r'"([^"]+)"', text)
        if quote_match:
            quote = quote_match.group(1)
            if len(quote) > 3:
                return f'"{quote}"'
        return "No specific quote provided."
    
    def _extract_regulation_basic(self, text: str) -> str:
        """Framework-agnostic regulation extraction."""
        # Try multiple regulation reference formats
        regulation_patterns = [
            r'(Article\s+\d+(?:\([^)]+\))?)',           # Article 5(1)(a)
            r'(Section\s+\d+(?:\.[^a-z\s]+)?)',        # Section 3.1
            r'(Rule\s+\d+(?:\.[^a-z\s]+)?)',           # Rule 123.4
            r'(Standard\s+\d+(?:\.[^a-z\s]+)?)',       # Standard 21.1
            r'(Regulation\s+\d+(?:\.[^a-z\s]+)?)',     # Regulation 456
            r'(Requirement\s+\d+(?:\.[^a-z\s]+)?)',    # Requirement 7.2
            r'(Chapter\s+\d+(?:\.[^a-z\s]+)?)',        # Chapter 4
            r'(Part\s+\d+(?:\.[^a-z\s]+)?)',           # Part 100.1
            r'(Subpart\s+[A-Z])',                      # Subpart A
            r'(\d+\s+CFR\s+\d+(?:\.\d+)?)',           # 21 CFR 110.5
        ]
        
        for pattern in regulation_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "Unknown Regulation"
    
    def _determine_confidence_basic(self, text: str) -> str:
        """Basic confidence determination."""
        text_lower = text.lower()
        
        # High confidence indicators - framework agnostic
        high_confidence_terms = [
            'mandatory', 'required', 'must', 'shall', 'prohibited',
            'forbidden', 'illegal', 'unauthorized', 'violation', 'breach'
        ]
        
        # Low confidence indicators
        low_confidence_terms = [
            'may', 'could', 'possibly', 'potentially', 'might',
            'appears', 'seems', 'suggests', 'unclear', 'ambiguous'
        ]
        
        if any(term in text_lower for term in high_confidence_terms):
            return "High"
        elif any(term in text_lower for term in low_confidence_terms):
            return "Low"
        else:
            return "Medium"
    
    def _clean_description_basic(self, text: str, citation: str) -> str:
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
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str,
                              content_indicators: Optional[Dict[str, str]] = None,
                              potential_violations: Optional[List[Dict[str, Any]]] = None,
                              regulation_framework: str = "",
                              risk_level: str = "unknown") -> str:
        """Create a framework-agnostic analysis prompt that prevents artifacts."""
        
        focus = ""
        if risk_level == "high":
            focus = "This section appears high-risk - be thorough."
        elif risk_level == "low":  
            focus = "This section appears low-risk - only flag obvious violations."
        
        # 🔧 FIXED PROMPT - Prevents instruction leakage and markdown
        return f"""You are a regulatory compliance expert. Analyze this document section for violations.

SECTION: {section}
DOCUMENT TEXT:
{text}

RELEVANT REGULATIONS:
{regulations}

{focus}

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
    
    def format_regulations(self, regulations: List[Dict[str, Any]], 
                         regulation_context: str = "", regulation_patterns: str = "") -> str:
        """Format regulations for prompts."""
        formatted_regs = []
        
        if regulation_context:
            formatted_regs.append(f"CONTEXT:\n{regulation_context[:500]}...")
        
        for i, reg in enumerate(regulations):
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", f"Regulation {i+1}")
            
            formatted_reg = f"{reg_id}:\n{reg_text}"
            formatted_regs.append(formatted_reg)
        
        return "\n\n".join(formatted_regs)
    
    def _parse_pattern_block(self, lines: List[str]) -> tuple:
        """Parse a pattern block from common_patterns.txt."""
        pattern_name = ""
        description = ""
        indicators = []
        related_refs = []
        
        for line in lines:
            line = line.strip()
            if line.startswith("Pattern:"):
                pattern_name = line.replace("Pattern:", "").strip()
            elif line.startswith("Description:"):
                description = line.replace("Description:", "").strip()
            elif line.startswith("Indicators:"):
                indicator_text = line.replace("Indicators:", "").strip()
                indicators = re.findall(r'"([^"]*)"', indicator_text)
                if not indicators:
                    indicators = [i.strip() for i in indicator_text.split(',') if i.strip()]
            elif line.startswith("Related"):
                refs_text = line.split(":", 1)[1].strip() if ":" in line else ""
                related_refs = [r.strip() for r in refs_text.split(",") if r.strip()]
        
        return pattern_name, description, indicators, related_refs
    
    def _get_context(self, text: str, indicator: str) -> str:
        """Get context around an indicator match."""
        try:
            if not text or not indicator:
                return indicator or ""
            
            match_idx = text.lower().find(indicator.lower())
            if match_idx == -1:
                return indicator
            
            start = max(0, match_idx - 50)
            end = min(len(text), match_idx + len(indicator) + 50)
            return text[start:end]
        except Exception:
            return indicator or ""