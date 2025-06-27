"""
GDPR Regulation Handler

Provides GDPR-specific processing logic for compliance analysis.
Implements array-based response parsing for reliable violation detection.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional

from utils.regulation_handler_base import RegulationHandlerBase

logger = logging.getLogger(__name__)


class RegulationHandler(RegulationHandlerBase):
    """
    GDPR-specific handler with array-based response system.
    
    Provides enhanced prompt generation and response parsing specifically 
    optimized for GDPR compliance analysis.
    """
    
    def __init__(self, debug: bool = False) -> None:
        """
        Initialize the GDPR handler.
        
        Args:
            debug: Enable debug logging (deprecated, use logging configuration)
        """
        super().__init__(debug)
        logger.info("GDPR RegulationHandler initialized")
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str, 
                              content_indicators: Optional[Dict[str, str]] = None,
                              potential_violations: Optional[List[Dict[str, Any]]] = None,
                              regulation_framework: str = "gdpr",
                              risk_level: str = "unknown") -> str:
        """
        Create GDPR-specific analysis prompt focused on violations only.
        
        Args:
            text: Document text to analyze
            section: Section identifier
            regulations: Formatted regulation text
            content_indicators: Content analysis indicators (optional)
            potential_violations: Pre-identified potential violations (optional) 
            regulation_framework: Framework name (should be "gdpr")
            risk_level: Risk level assessment (optional)
            
        Returns:
            Formatted prompt for LLM analysis
        """
        logger.debug(f"Creating GDPR analysis prompt for section: {section}")
        
        return f"""Find GDPR violations in this document section.

DOCUMENT SECTION: {section}
DOCUMENT TEXT:
{text}

RELEVANT GDPR ARTICLES:
{regulations}

TASK: Find statements that clearly violate GDPR requirements.

IGNORE these types of statements (they are NOT violations):
    - "We implement [security measure]" 
    - "The system provides [user right]"
    - "Data is [protected/encrypted/minimized]"
    - "Users can [delete/access/export] their data"
    - "We obtain [consent/permission]"
    - "Privacy notices are provided"

ONLY FLAG these types of statements (actual violations):
    - "Data is stored indefinitely without purpose"
    - "No consent is required" 
    - "Users cannot delete their data"
    - "No security measures are used"
    - "We don't provide privacy information"
    - "Data is shared without user knowledge"

EXAMPLES:
    ❌ VIOLATION: "Customer data will be retained indefinitely for business value"
    ✅ NOT A VIOLATION: "Data retention policies limit storage to necessary periods"

    ❌ VIOLATION: "No user consent required for data processing"  
    ✅ NOT A VIOLATION: "Explicit user consent is obtained before processing"

    ❌ VIOLATION: "Basic password protection only, no encryption"
    ✅ NOT A VIOLATION: "AES-256 encryption protects all stored data"

RESPONSE FORMAT - Return ONLY a JSON array:
    [
    ["Clear violation description", "Article X", "Exact quote showing the violation"],
    ["Another violation", "Article Y", "Another exact quote"]
    ]

RULES:
    - Only flag statements that describe BAD practices or clear violations
    - Ignore all statements that describe GOOD practices or compliance measures
    - Use exact quotes from the document
    - If unsure whether something is a violation, don't include it
    - If no clear violations found, return: []
"""

    def parse_llm_response(self, response: str, document_text: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse array-based LLM response for GDPR violations.
        
        Args:
            response: Raw LLM response text
            document_text: Original document text (optional)
            
        Returns:
            Dictionary with 'issues' key containing list of violations
        """
        logger.debug(f"Parsing GDPR LLM response (length: {len(response)})")
        
        result = {"issues": []}
        
        try:
            # Extract the JSON array from the response
            clean_array = self._extract_json_array(response)
            
            if not clean_array:
                logger.debug("No JSON array found in response")
                return result
            
            # Parse the JSON array
            violations_array = json.loads(clean_array)
            
            logger.debug(f"Parsed {len(violations_array)} violations from array")
            
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
                    
                    logger.debug(f"Added violation {i+1}: {issue_desc[:50]}...")
                else:
                    logger.debug(f"Skipping invalid violation format: {violation}")
            
        except json.JSONDecodeError as e:
            logger.debug(f"JSON parse failed: {e}, attempting fallback parsing")
            result = self._fallback_array_parsing(response)
        except Exception as e:
            logger.error(f"Unexpected parsing error: {e}")
            result = {"issues": []}
        
        logger.debug(f"Final result: {len(result['issues'])} GDPR violations found")
        return result
    
    def _extract_json_array(self, response: str) -> str:
        """
        Extract the JSON array from the LLM response.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Extracted JSON array as string, or empty string if not found
        """
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
    
    def _is_valid_violation_array(self, violation: Any) -> bool:
        """
        Check if the violation array has the correct format.
        
        Args:
            violation: Violation data to validate
            
        Returns:
            True if violation is valid, False otherwise
        """
        return (
            isinstance(violation, list) and 
            len(violation) >= 3 and
            len(str(violation[0]).strip()) > 5 and  # Meaningful description
            len(str(violation[1]).strip()) > 0      # Some regulation reference
        )
    
    def _standardize_regulation(self, regulation: str) -> str:
        """
        Standardize GDPR article references.
        
        Args:
            regulation: Raw regulation reference
            
        Returns:
            Standardized regulation reference
        """
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
        """
        Fallback parsing using regex if JSON parsing fails.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Dictionary with parsed violations
        """
        result = {"issues": []}
        
        logger.debug("Using fallback regex parsing")
        
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
                    
                    logger.debug(f"Fallback found: {match[0][:40]}...")
        
        return result