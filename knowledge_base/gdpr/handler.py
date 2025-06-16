# knowledge_base/gdpr/handler.py

import re
from typing import Dict, Any, List, Optional
from utils.regulation_handler_base import RegulationHandlerBase

class RegulationHandler(RegulationHandlerBase):
    """Simplified GDPR handler - no citation validation, trust the LLM."""
    
    def __init__(self, debug=False):
        """Initialize the GDPR handler."""
        super().__init__(debug)
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str, 
                             content_indicators: Optional[Dict[str, str]] = None,
                             potential_violations: Optional[List[Dict[str, Any]]] = None,
                             regulation_framework: str = "gdpr",
                             risk_level: str = "unknown") -> str:
        """Create a simple, focused GDPR analysis prompt."""
        
        # Simple risk guidance
        focus = ""
        if risk_level == "high":
            focus = "This section appears high-risk - be thorough in your analysis."
        elif risk_level == "low":
            focus = "This section appears low-risk - only flag clear, obvious violations."
        
        prompt_text = f"""Analyze this document section for GDPR compliance violations and strengths.

DOCUMENT SECTION: {section}
DOCUMENT TEXT:
{text}

RELEVANT GDPR ARTICLES:
{regulations}

{focus}

Find GDPR violations and compliance points in the document text above.

FORMAT:
COMPLIANCE ISSUES:
1. Brief issue description violating Article X. "exact quote from document"

COMPLIANCE POINTS:  
1. Brief compliance strength supporting Article X. "exact quote from document"

RULES:
- Only quote text that appears in the DOCUMENT TEXT above
- Include specific GDPR article numbers (Article 5, Article 7, etc.)
- Use HIGH confidence for clear violations, MEDIUM for likely issues, LOW for uncertain
- Write "NO COMPLIANCE ISSUES DETECTED" if none found
- Write "NO COMPLIANCE POINTS DETECTED" if none found
"""
        return prompt_text

    def parse_llm_response_simple(self, response: str, document_text: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """Simplified response parsing - trust the LLM output."""
        
        if self.debug:
            print("=" * 50)
            print("DEBUG: Raw LLM Response:")
            print(response[:500] + "..." if len(response) > 500 else response)
            print("=" * 50)
        
        result = {"issues": [], "compliance_points": []}
        
        # Simple cleanup - remove markdown formatting and extra whitespace
        response = self._clean_response_simple(response)
        
        # Parse issues
        if "NO COMPLIANCE ISSUES DETECTED" not in response.upper():
            issues_match = re.search(r'COMPLIANCE\s+ISSUES:?\s*\n(.*?)(?:COMPLIANCE\s+POINTS:|$)', 
                                   response, re.DOTALL | re.IGNORECASE)
            if issues_match:
                issues_text = issues_match.group(1)
                result["issues"] = self._parse_items_simple(issues_text, "issue")
                
                if self.debug:
                    print(f"DEBUG: Parsed {len(result['issues'])} issues")
                    for i, issue in enumerate(result["issues"]):
                        print(f"  Issue {i+1}: {issue.get('issue', 'NO TEXT')[:100]}...")
        
        # Parse compliance points
        if "NO COMPLIANCE POINTS DETECTED" not in response.upper():
            points_match = re.search(r'COMPLIANCE\s+POINTS:?\s*\n(.*?)$', 
                                   response, re.DOTALL | re.IGNORECASE)
            if points_match:
                points_text = points_match.group(1)
                result["compliance_points"] = self._parse_items_simple(points_text, "point")
                
                if self.debug:
                    print(f"DEBUG: Parsed {len(result['compliance_points'])} points")
        
        if self.debug:
            print("=" * 50)
        
        return result
    
    def _clean_response_simple(self, response: str) -> str:
        """Simple response cleaning - remove markdown and extra whitespace."""
        # Remove code blocks
        response = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
        
        # Remove markdown formatting
        response = re.sub(r'\*\*(.*?)\*\*', r'\1', response)  # **bold** -> bold
        response = re.sub(r'\*(.*?)\*', r'\1', response)      # *italic* -> italic
        
        # Remove extra whitespace
        response = re.sub(r'\n\s*\n\s*\n+', '\n\n', response)
        response = re.sub(r' +', ' ', response)
        
        return response.strip()
    
    def _parse_items_simple(self, text: str, item_type: str) -> List[Dict[str, Any]]:
        """Simple item parsing - no validation, trust the LLM."""
        items = []
        
        # Very permissive pattern for numbered items
        item_pattern = re.compile(r'(?:^|\n)\s*(\d+)\.\s*(.*?)(?=(?:\n\s*\d+\.)|$)', re.DOTALL)
        
        for match in item_pattern.finditer(text):
            item_text = match.group(2).strip()
            
            if len(item_text) < 10:  # Skip very short items
                continue
            
            # Extract quote - simple, no validation
            citation = self._extract_quote_simple(item_text)
            
            # Extract regulation reference
            regulation = self._extract_regulation_simple(item_text)
            
            # Simple confidence based on keywords only
            confidence = self._determine_confidence_simple(item_text)
            
            # Clean description (remove quote from description)
            description = self._clean_description(item_text, citation)
            
            if len(description) < 5:
                continue
            
            items.append({
                item_type: description,
                "regulation": regulation,
                "confidence": confidence,
                "citation": citation
            })
        
        return items
    
    def _extract_quote_simple(self, text: str) -> str:
        """Simple quote extraction - just look for quoted text, no validation."""
        # Look for text in quotes - simple patterns only
        quote_patterns = [
            r'"([^"]+)"',     # Double quotes
            r"'([^']+)'",     # Single quotes
        ]
        
        for pattern in quote_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Return the longest quote found
                longest_quote = max(matches, key=len)
                if len(longest_quote) > 3:  # Very minimal length requirement
                    return f'"{longest_quote}"'
        
        return "No specific quote provided."
    
    def _extract_regulation_simple(self, text: str) -> str:
        """Simple regulation extraction - look for explicit references first."""
        # Look for explicit Article references
        article_patterns = [
            r'Article\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)',
            r'article\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)',
            r'violating\s+Article\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)',
            r'supporting\s+Article\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)'
        ]
        
        for pattern in article_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"Article {match.group(1)}"
        
        # Context-based mapping as fallback
        text_lower = text.lower()
        
        # Storage and retention issues
        if any(term in text_lower for term in ['indefinite', 'retain', 'storage', 'delete', 'kept']):
            return "Article 5(1)(e)"
        
        # Consent issues
        if any(term in text_lower for term in ['consent', 'mandatory', 'required', 'opt-in', 'withdraw', 'agree']):
            return "Article 7"
        
        # Security issues
        if any(term in text_lower for term in ['security', 'encrypt', 'protection', 'breach', 'safeguard']):
            return "Article 32"
        
        # Transparency and information issues
        if any(term in text_lower for term in ['information', 'notify', 'transparent', 'disclosure', 'inform']):
            return "Article 13"
        
        # Automated decision-making
        if any(term in text_lower for term in ['automated', 'profiling', 'algorithm', 'decision']):
            return "Article 22"
        
        # Special categories
        if any(term in text_lower for term in ['sensitive', 'biometric', 'health', 'psychological']):
            return "Article 9"
        
        # Rights-related
        if any(term in text_lower for term in ['access', 'rectification', 'erasure', 'portability']):
            if 'access' in text_lower:
                return "Article 15"
            elif any(term in text_lower for term in ['erasure', 'deletion', 'delete']):
                return "Article 17"
            else:
                return "Article 16"
        
        # Default to general principles
        return "Article 5"
    
    def _determine_confidence_simple(self, text: str) -> str:
        """Simple confidence determination based on keywords only."""
        text_lower = text.lower()
        
        # High confidence indicators - clear violations
        high_confidence_terms = [
            'indefinitely', 'required', 'mandatory', 'automatic', 
            'no option', 'must accept', 'forced', 'without consent',
            'no choice', 'cannot refuse', 'will not implement'
        ]
        
        # Low confidence indicators - uncertain language
        low_confidence_terms = [
            'may', 'could', 'possibly', 'potentially', 'might',
            'appears', 'seems', 'suggests', 'unclear'
        ]
        
        # Check for high confidence
        if any(term in text_lower for term in high_confidence_terms):
            return "High"
        
        # Check for low confidence  
        elif any(term in text_lower for term in low_confidence_terms):
            return "Low"
        
        # Default to medium
        else:
            return "Medium"
    
    def _clean_description(self, text: str, citation: str) -> str:
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