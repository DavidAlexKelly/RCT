# utils/regulation_handler_base.py

import re
from typing import Dict, Any, List, Optional

class RegulationHandlerBase:
    """Simplified base class for regulation handlers - no citation validation."""
    
    def __init__(self, debug=False):
        """Initialize the regulation handler."""
        self.debug = debug
    
    def extract_content_indicators(self, text: str) -> Dict[str, str]:
        """Extract content indicators from text."""
        indicators = {
            "has_personal_data": "Yes" if re.search(r'\b(personal data|information|email|name|address|phone|profile)\b', text, re.I) else "No",
            "has_data_collection": "Yes" if re.search(r'\b(collect|gather|obtain|capture|record)\b', text, re.I) else "No",
            "has_data_sharing": "Yes" if re.search(r'\b(share|transfer|disclose|send|provide|third party)\b', text, re.I) else "No",
            "has_retention": "Yes" if re.search(r'\b(retain|store|keep|save|archive|delete|period)\b', text, re.I) else "No",
            "has_consent": "Yes" if re.search(r'\b(consent|agree|accept|approve|opt-in|opt-out)\b', text, re.I) else "No",
            "has_rights": "Yes" if re.search(r'\b(right|access|rectification|erasure|restriction|portability|object)\b', text, re.I) else "No",
            "has_automated": "Yes" if re.search(r'\b(automated|automatic|algorithm|profiling|AI|machine learning)\b', text, re.I) else "No",
            "has_sensitive": "Yes" if re.search(r'\b(sensitive|biometric|health|race|political|religion)\b', text, re.I) else "No"
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
        """Parse LLM response - simplified version without validation."""
        # Try simplified parsing first (if handler has it)
        if hasattr(self, 'parse_llm_response_simple'):
            return self.parse_llm_response_simple(response, document_text)
        
        # Fallback to basic parsing
        return self._parse_response_basic(response)
    
    def _parse_response_basic(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Basic response parsing fallback - simplified."""
        result = {"issues": [], "compliance_points": []}
        
        # Clean response - remove markdown and code blocks
        response = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
        response = re.sub(r'\*\*(.*?)\*\*', r'\1', response)  # **bold** -> bold
        response = re.sub(r'\*(.*?)\*', r'\1', response)      # *italic* -> italic
        
        # Parse issues
        if "NO COMPLIANCE ISSUES DETECTED" not in response:
            issues_match = re.search(r'COMPLIANCE\s+ISSUES:?\s*\n(.*?)(?:COMPLIANCE\s+POINTS:|$)', 
                                   response, re.DOTALL | re.IGNORECASE)
            if issues_match:
                issues_text = issues_match.group(1)
                result["issues"] = self._parse_items_basic(issues_text, "issue")
        
        # Parse compliance points
        if "NO COMPLIANCE POINTS DETECTED" not in response:
            points_match = re.search(r'COMPLIANCE\s+POINTS:?\s*\n(.*?)$', 
                                   response, re.DOTALL | re.IGNORECASE)
            if points_match:
                points_text = points_match.group(1)
                result["compliance_points"] = self._parse_items_basic(points_text, "point")
        
        return result
    
    def _parse_items_basic(self, text: str, item_type: str) -> List[Dict[str, Any]]:
        """Basic item parsing - simplified, no validation."""
        items = []
        
        item_pattern = re.compile(r'(?:^|\n)\s*(\d+)\.\s+(.*?)(?=(?:\n\s*\d+\.)|$)', re.DOTALL)
        
        for match in item_pattern.finditer(text):
            item_text = match.group(2).strip()
            
            if len(item_text) < 5:  # Minimal length check
                continue
            
            # Extract quote - simple
            citation = self._extract_quote_basic(item_text)
            
            # Extract regulation
            regulation = self._extract_regulation_basic(item_text)
            
            # Simple confidence
            confidence = self._determine_confidence_basic(item_text)
            
            # Clean description
            description = item_text
            if citation != "No specific quote provided.":
                description = description.replace(citation, "").strip()
            
            description = re.sub(r'\s+', ' ', description).strip()
            
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
        """Basic regulation extraction."""
        reg_match = re.search(r'Article\s*(\d+)', text, re.IGNORECASE)
        if reg_match:
            return f"Article {reg_match.group(1)}"
        return "Unknown Regulation"
    
    def _determine_confidence_basic(self, text: str) -> str:
        """Basic confidence determination."""
        text_lower = text.lower()
        
        # Simple keyword-based confidence
        if any(term in text_lower for term in ['indefinitely', 'mandatory', 'required']):
            return "High"
        elif any(term in text_lower for term in ['may', 'could', 'possibly']):
            return "Low"
        else:
            return "Medium"
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str,
                              content_indicators: Optional[Dict[str, str]] = None,
                              potential_violations: Optional[List[Dict[str, Any]]] = None,
                              regulation_framework: str = "",
                              risk_level: str = "unknown") -> str:
        """Create a simple analysis prompt."""
        
        focus = ""
        if risk_level == "high":
            focus = "This section appears high-risk - be thorough."
        elif risk_level == "low":  
            focus = "This section appears low-risk - only flag obvious violations."
        
        return f"""Analyze this document section for regulatory compliance.

SECTION: {section}
DOCUMENT TEXT:
{text}

RELEVANT REGULATIONS:
{regulations}

{focus}

Find violations and compliance strengths.

FORMAT:
COMPLIANCE ISSUES:
1. Brief issue description. "quote from document"

COMPLIANCE POINTS:
1. Brief compliance strength. "quote from document"

RULES:
- Only quote from the document text above
- Include regulation references where possible
- Write "NO COMPLIANCE ISSUES DETECTED" if none found
- Write "NO COMPLIANCE POINTS DETECTED" if none found
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