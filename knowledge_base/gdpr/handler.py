# knowledge_base/gdpr/handler.py

import re
from typing import Dict, Any, List, Optional
from utils.regulation_handler_base import RegulationHandlerBase

class RegulationHandler(RegulationHandlerBase):
    """Simplified GDPR handler with focused prompts and reliable citation extraction."""
    
    def __init__(self, debug=False):
        """Initialize the GDPR handler."""
        super().__init__(debug)
        
        # Simple business vs legal term lists
        self.business_terms = {
            'data', 'user', 'customer', 'app', 'system', 'platform', 'project', 
            'business', 'revenue', 'marketing', 'team', 'company', 'implement',
            'budget', 'timeline', 'indefinitely', 'automatic', 'required', 'will'
        }
        
        self.legal_terms = {
            'shall', 'controller', 'data subject', 'supervisory authority',
            'member state', 'union law', 'pursuant to', 'notwithstanding'
        }
    
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
        
        return f"""Analyze this document section for GDPR compliance violations and strengths.

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
- Quote business language, not legal language
- Include specific GDPR article numbers (Article 5, Article 7, etc.)
- Use HIGH confidence for clear violations, MEDIUM for likely issues, LOW for uncertain
- Write "NO COMPLIANCE ISSUES DETECTED" if none found
- Write "NO COMPLIANCE POINTS DETECTED" if none found
"""

    def extract_citation_simple(self, text: str, document_text: str) -> str:
        """Simple, reliable citation extraction."""
        # Look for quotes in the text
        quote_patterns = [r'"([^"]+)"', r"'([^']+)'"]
        
        for pattern in quote_patterns:
            matches = re.findall(pattern, text)
            for quote in matches:
                if self._is_business_citation(quote) and self._appears_in_document(quote, document_text):
                    return f'"{quote}"'
        
        return "No specific quote provided."
    
    def _is_business_citation(self, quote: str) -> bool:
        """Check if quote sounds like business document text."""
        quote_lower = quote.lower()
        
        # Must have at least one business term
        has_business = any(term in quote_lower for term in self.business_terms)
        
        # Must not have legal terms
        has_legal = any(term in quote_lower for term in self.legal_terms)
        
        # Must be reasonable length
        word_count = len(quote.split())
        
        return has_business and not has_legal and 3 <= word_count <= 50
    
    def _appears_in_document(self, quote: str, document_text: str) -> bool:
        """Check if quote actually appears in document."""
        if not document_text:
            return True  # Can't verify, assume valid
        
        # Check if quote or close variant appears in document
        quote_clean = quote.lower().strip()
        doc_clean = document_text.lower()
        
        # Direct match
        if quote_clean in doc_clean:
            return True
        
        # Check if key words from quote appear near each other in document
        quote_words = quote_clean.split()
        if len(quote_words) >= 3:
            # All words must appear in document
            if all(word in doc_clean for word in quote_words):
                return True
        
        return False
    
    def extract_regulation_reference_improved(self, text: str) -> str:
        """Improved GDPR article extraction with better context mapping."""
        
        # Direct article patterns
        direct_patterns = [
            r'Article\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)',
            r'violating\s+Article\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)',
            r'supporting\s+Article\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)'
        ]
        
        for pattern in direct_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"Article {match.group(1)}"
        
        # Context-based mapping (simplified)
        text_lower = text.lower()
        
        # Storage and retention issues
        if any(term in text_lower for term in ['indefinite', 'retain', 'storage', 'delete']):
            return "Article 5(1)(e)"
        
        # Consent issues
        if any(term in text_lower for term in ['consent', 'mandatory', 'required', 'opt-in', 'withdraw']):
            return "Article 7"
        
        # Security issues
        if any(term in text_lower for term in ['security', 'encrypt', 'protection', 'breach']):
            return "Article 32"
        
        # Transparency issues
        if any(term in text_lower for term in ['information', 'notify', 'transparent', 'disclosure']):
            return "Article 13"
        
        # Automated decision-making
        if any(term in text_lower for term in ['automated', 'profiling', 'algorithm', 'decision']):
            return "Article 22"
        
        # Special categories
        if any(term in text_lower for term in ['sensitive', 'biometric', 'health', 'psychological']):
            return "Article 9"
        
        # Rights
        if any(term in text_lower for term in ['access', 'rectification', 'erasure', 'portability']):
            if 'access' in text_lower:
                return "Article 15"
            elif 'erasure' in text_lower or 'deletion' in text_lower:
                return "Article 17"
            else:
                return "Article 16"
        
        # Default to general principles
        return "Article 5"
    
    def parse_llm_response_simple(self, response: str, document_text: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """Simplified response parsing with better confidence handling."""
        result = {"issues": [], "compliance_points": []}
        
        # Clean response
        response = self._clean_response_simple(response)
        
        # Parse issues
        if "NO COMPLIANCE ISSUES DETECTED" not in response:
            issues_match = re.search(r'COMPLIANCE\s+ISSUES:?\s*\n(.*?)(?:COMPLIANCE\s+POINTS:|$)', 
                                   response, re.DOTALL | re.IGNORECASE)
            if issues_match:
                issues_text = issues_match.group(1)
                result["issues"] = self._parse_items_simple(issues_text, "issue", document_text)
        
        # Parse compliance points
        if "NO COMPLIANCE POINTS DETECTED" not in response:
            points_match = re.search(r'COMPLIANCE\s+POINTS:?\s*\n(.*?)$', 
                                   response, re.DOTALL | re.IGNORECASE)
            if points_match:
                points_text = points_match.group(1)
                result["compliance_points"] = self._parse_items_simple(points_text, "point", document_text)
        
        return result
    
    def _clean_response_simple(self, response: str) -> str:
        """Simple response cleaning."""
        # Remove code blocks
        response = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
        
        # Remove extra whitespace
        response = re.sub(r'\n\s*\n\s*\n+', '\n\n', response)
        response = re.sub(r' +', ' ', response)
        
        return response.strip()
    
    def _parse_items_simple(self, text: str, item_type: str, document_text: str = "") -> List[Dict[str, Any]]:
        """Simple item parsing with confidence detection."""
        items = []
        
        # Pattern for numbered items
        item_pattern = re.compile(r'(?:^|\n)\s*(\d+)\.\s+(.*?)(?=(?:\n\s*\d+\.)|$)', re.DOTALL)
        
        for match in item_pattern.finditer(text):
            item_text = match.group(2).strip()
            
            if len(item_text) < 10:
                continue
            
            # Extract citation
            citation = self.extract_citation_simple(item_text, document_text)
            
            # Extract regulation
            regulation = self.extract_regulation_reference_improved(item_text)
            
            # Determine confidence based on citation quality and keywords
            confidence = self._determine_confidence(item_text, citation, document_text)
            
            # Clean description
            description = self._clean_description_simple(item_text, citation)
            
            if len(description) < 5:
                continue
            
            item = {
                item_type: description,
                "regulation": regulation,
                "confidence": confidence,
                "citation": citation
            }
            
            items.append(item)
        
        return items
    
    def _determine_confidence(self, item_text: str, citation: str, document_text: str) -> str:
        """Determine confidence level based on evidence quality."""
        text_lower = item_text.lower()
        
        # High confidence indicators
        high_confidence_terms = ['indefinitely', 'required', 'mandatory', 'automatic', 'no option']
        
        # Check citation quality
        has_good_citation = citation != "No specific quote provided." and len(citation) > 20
        
        # Check for strong violation indicators
        has_strong_violation = any(term in text_lower for term in high_confidence_terms)
        
        # Check if violation is clear and specific
        has_specific_article = 'article' in text_lower and any(num in item_text for num in ['5', '7', '13', '32'])
        
        if has_good_citation and has_strong_violation and has_specific_article:
            return "High"
        elif has_good_citation or has_strong_violation:
            return "Medium"
        else:
            return "Low"
    
    def _clean_description_simple(self, text: str, citation: str) -> str:
        """Simple description cleaning."""
        # Remove citation from description
        if citation and citation != "No specific quote provided.":
            citation_clean = citation.strip('"').strip("'")
            text = text.replace(citation, "").replace(citation_clean, "")
        
        # Remove redundant phrases
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'^\W+', '', text)
        text = text.strip()
        
        if text and not text.endswith('.'):
            text += '.'
        
        return text