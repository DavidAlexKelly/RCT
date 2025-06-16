# knowledge_base/gdpr/handler.py

import re
import json
from typing import Dict, Any, List, Optional
from utils.regulation_handler_base import RegulationHandlerBase

class RegulationHandler(RegulationHandlerBase):
    """GDPR handler with array-based response system - much simpler and more reliable."""
    
    def __init__(self, debug=False):
        """Initialize the GDPR handler."""
        super().__init__(debug)
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str, 
                             content_indicators: Optional[Dict[str, str]] = None,
                             potential_violations: Optional[List[Dict[str, Any]]] = None,
                             regulation_framework: str = "gdpr",
                             risk_level: str = "unknown") -> str:
        """Create a GDPR prompt that requests simple array format."""
        
        focus = ""
        if risk_level == "high":
            focus = "This section appears high-risk - be thorough in finding violations."
        elif risk_level == "low":
            focus = "This section appears low-risk - only flag clear, obvious violations."
        
        return f"""Analyze this document section for GDPR compliance violations.

DOCUMENT SECTION: {section}
DOCUMENT TEXT:
{text}

RELEVANT GDPR ARTICLES:
{regulations}

{focus}

TASK: Find GDPR violations and return them as a simple array.

RESPONSE FORMAT - Return ONLY a JSON array, nothing else:
[
["Clear description of the violation", "Article X", "Exact quote from the document"],
["Another violation description", "Article Y", "Another exact quote from document"],
["Third violation if found", "Article Z", "Third exact quote"]
]

RULES:
- Each violation = [description, article_number, exact_document_quote]
- Only quote text that appears EXACTLY in the document above
- Use specific GDPR article numbers: Article 5, Article 7, Article 13, Article 32, etc.
- Keep descriptions clear and concise
- If no violations found, return: []

EXAMPLES:
["Data stored indefinitely violates storage limitation", "Article 5(1)(e)", "All customer data will be stored indefinitely"]
["No consent withdrawal mechanism provided", "Article 7(3)", "irrevocable consent required"]
["No encryption at rest implemented", "Article 32", "Due to budget constraints, we will not implement: - Data encryption at rest"]
"""

    def parse_llm_response(self, response: str, document_text: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """Parse array-based LLM response - dramatically simpler than text parsing."""
        
        if self.debug:
            print("=" * 60)
            print("DEBUG: GDPR Array Parser")
            print(f"Raw response length: {len(response)}")
            print(f"Raw response: {response}")
            print("=" * 60)
        
        result = {"issues": []}
        
        try:
            # Extract the JSON array from the response
            clean_array = self._extract_json_array(response)
            
            if self.debug:
                print(f"DEBUG: Extracted array: {clean_array}")
            
            if not clean_array:
                if self.debug:
                    print("DEBUG: No array found in response")
                return result
            
            # Parse the JSON array
            violations_array = json.loads(clean_array)
            
            if self.debug:
                print(f"DEBUG: Parsed {len(violations_array)} violations from array")
            
            # Convert each array item to our standard format
            for i, violation in enumerate(violations_array):
                if self._is_valid_violation_array(violation):
                    issue_desc = str(violation[0]).strip()
                    regulation = self._standardize_regulation(str(violation[1]).strip())
                    citation = str(violation[2]).strip()
                    
                    # Clean up the citation
                    if citation and not citation.startswith('"'):
                        citation = f'"{citation}"'
                    elif not citation:
                        citation = "No specific quote provided."
                    
                    result["issues"].append({
                        "issue": issue_desc,
                        "regulation": regulation,
                        "citation": citation
                    })
                    
                    if self.debug:
                        print(f"  {i+1}. {issue_desc[:50]}... [{regulation}]")
                else:
                    if self.debug:
                        print(f"DEBUG: Skipping invalid violation format: {violation}")
            
        except json.JSONDecodeError as e:
            if self.debug:
                print(f"DEBUG: JSON parse failed: {e}")
                print("DEBUG: Attempting fallback parsing...")
            
            # Fallback to regex-based array extraction
            result = self._fallback_array_parsing(response)
            
        except Exception as e:
            if self.debug:
                print(f"DEBUG: Unexpected parsing error: {e}")
            result = {"issues": []}
        
        if self.debug:
            print(f"DEBUG: Final result: {len(result['issues'])} GDPR violations found")
            print("=" * 60)
        
        return result
    
    def _extract_json_array(self, response: str) -> str:
        """Extract the JSON array from the LLM response."""
        
        # Remove any text before the opening bracket
        start_idx = response.find('[')
        if start_idx == -1:
            return ""
        
        # Find the matching closing bracket
        bracket_count = 0
        end_idx = -1
        
        for i in range(start_idx, len(response)):
            if response[i] == '[':
                bracket_count += 1
            elif response[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i
                    break
        
        if end_idx == -1:
            return ""
        
        # Extract the array portion
        array_text = response[start_idx:end_idx + 1]
        
        # Clean up formatting
        array_text = array_text.replace('\n', ' ')
        array_text = re.sub(r'\s+', ' ', array_text)
        
        return array_text
    
    def _is_valid_violation_array(self, violation) -> bool:
        """Check if the violation array has the correct format."""
        return (
            isinstance(violation, list) and 
            len(violation) >= 3 and
            len(str(violation[0]).strip()) > 5 and  # Meaningful description
            len(str(violation[1]).strip()) > 0      # Some regulation reference
        )
    
    def _standardize_regulation(self, regulation: str) -> str:
        """Standardize GDPR article references."""
        if not regulation:
            return "Unknown Article"
        
        # Clean up common variations
        regulation = regulation.strip()
        
        # Handle various formats: "Article 5", "Art. 5", "GDPR Article 5", etc.
        article_match = re.search(r'(?:Article|Art\.?)\s*(\d+(?:\([^)]+\))*)', regulation, re.IGNORECASE)
        if article_match:
            article_num = article_match.group(1)
            return f"Article {article_num}"
        
        # If it already looks like "Article X", keep it
        if regulation.startswith("Article"):
            return regulation
        
        # If just a number, add "Article"
        if re.match(r'^\d+', regulation):
            return f"Article {regulation}"
        
        return regulation
    
    def _fallback_array_parsing(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Fallback parsing using regex if JSON parsing fails."""
        result = {"issues": []}
        
        if self.debug:
            print("DEBUG: Using fallback regex parsing...")
        
        # Look for array-like patterns in the text
        patterns = [
            # ["text", "Article X", "quote"]
            r'\[\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"\s*\]',
            # ['text', 'Article X', 'quote']  
            r"\[\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\s*\]",
            # Mixed quotes
            r'\[\s*"([^"]*)",\s*"([^"]*)",\s*\'([^\']*)\'\s*\]'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                if len(match) == 3 and len(match[0].strip()) > 5:
                    result["issues"].append({
                        "issue": match[0].strip(),
                        "regulation": self._standardize_regulation(match[1].strip()),
                        "citation": f'"{match[2].strip()}"'
                    })
                    
                    if self.debug:
                        print(f"  Fallback found: {match[0][:40]}...")
        
        return result