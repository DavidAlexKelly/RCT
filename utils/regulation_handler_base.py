import json
import re
from typing import Dict, Any, List
from pathlib import Path

class RegulationHandlerBase:
    """Base class for all regulation handlers - completely framework-agnostic."""
    
    def __init__(self, debug=False):
        """Initialize the regulation handler."""
        self.debug = debug
        self.name = "Base"
        self.regulated_topics = {}
        self.analysis_threshold = 2
    
    def calculate_risk_score(self, text: str) -> float:
        """Calculate score based on number of regulated topics present."""
        text_lower = text.lower()
        topics_found = {}
        
        # Count which topic categories are present
        for topic_category, keywords in self.regulated_topics.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    topics_found[topic_category] = topics_found.get(topic_category, 0) + 1
                    break  # One keyword per category is enough
        
        # Score = number of different topic categories found
        score = len(topics_found)
        
        if self.debug and score > 0:
            print(f"\n=== {self.name} TOPIC ANALYSIS ===")
            print(f"Text preview: {text[:200]}...")
            print(f"Topics found: {list(topics_found.keys())}")
            print(f"Topic count: {score}")
            print(f"Threshold: {self.analysis_threshold}")
            print("=" * 40)
        
        return score
    
    def should_analyse(self, text: str) -> bool:
        """Analyse if text deals with multiple regulated topics."""
        topic_count = self.calculate_risk_score(text)
        return topic_count >= self.analysis_threshold
    
    def parse_response(self, response: str, document_text: str = "") -> List[Dict[str, Any]]:
        """Parse LLM response with balanced validation - framework agnostic."""
        
        if self.debug:
            print(f"\n=== {self.name} RESPONSE PARSING DEBUG ===")
            print(f"Full LLM response ({len(response)} chars):")
            print(f"'{response[:500]}...'")
            print("=" * 50)
        
        try:
            # Method 1: Try to extract and parse JSON
            violations = self._extract_json_violations(response)
            if violations:
                # Apply framework-agnostic validation and cleaning
                validated_violations = []
                for violation in violations:
                    cleaned_violation = self._clean_and_validate_violation(violation, document_text)
                    if cleaned_violation:
                        validated_violations.append(cleaned_violation)
                
                if self.debug:
                    print(f"SUCCESS: Extracted {len(validated_violations)} violations after cleaning")
                return validated_violations
            
            # Method 2: Check for explicit "no violations" response
            if self._is_no_violations_response(response):
                if self.debug:
                    print("SUCCESS: LLM indicated no violations found")
                return []
            
            # Method 3: Try fallback parsing for non-JSON responses
            violations = self._extract_violations_with_regex(response)
            if violations:
                if self.debug:
                    print(f"SUCCESS: Extracted {len(violations)} violations via regex fallback")
                return violations
            
            # If we get here, return empty rather than crash
            if self.debug:
                print("No violations found or extracted")
            
            return []
            
        except Exception as e:
            if self.debug:
                print(f"PARSING EXCEPTION: {e}")
                print("Returning empty list to prevent crash")
            
            return []
    
    def _clean_and_validate_violation(self, violation: Dict, document_text: str) -> Dict[str, Any]:
        """Clean and validate a violation - framework agnostic."""
        if not isinstance(violation, dict):
            return None
        
        # Extract fields with fallbacks
        issue = violation.get("issue") or violation.get("problem") or violation.get("violation", "")
        regulation = violation.get("regulation") or violation.get("article") or violation.get("section") or violation.get("rule", "")
        quote = violation.get("quote") or violation.get("citation") or violation.get("text", "")
        
        # Clean up issue description
        issue = str(issue).strip()
        if len(issue) < 5:  # Very short issues are likely bad
            if self.debug:
                print(f"REJECTED: Issue too short: '{issue}'")
            return None
        
        # Clean up regulation reference - framework agnostic approach
        regulation = str(regulation).strip()
        if not regulation or regulation.lower() in ["unknown", "unknown section", "unknown article", "unknown rule"]:
            # Framework-specific handlers should override this method for better inference
            regulation = self._infer_regulation_from_issue(issue)
            if self.debug:
                print(f"INFERRED regulation '{regulation}' from issue: '{issue[:50]}...'")
        
        # Clean up citation - be more flexible
        quote = str(quote).strip()
        if not quote or len(quote) < 3:
            # Try to extract a relevant quote from the issue description
            quote = self._generate_fallback_quote(issue, document_text)
            if self.debug:
                print(f"GENERATED fallback quote: '{quote[:50]}...'")
        
        # Ensure citation is properly quoted
        if quote and not quote.startswith('"'):
            quote = f'"{quote}"'
        
        return {
            "issue": issue,
            "regulation": regulation,
            "citation": quote
        }
    
    def _infer_regulation_from_issue(self, issue: str) -> str:
        """Base implementation - framework-specific handlers should override this."""
        # Generic fallback that doesn't assume any specific regulation structure
        return "Relevant Regulation"
    
    def _generate_fallback_quote(self, issue: str, document_text: str) -> str:
        """Generate a reasonable fallback quote for the issue - framework agnostic."""
        # If we have document text, try to find a relevant snippet
        if document_text and len(document_text) > 50:
            issue_words = issue.lower().split()
            
            # Look for sentences in document that contain key words from the issue
            sentences = document_text.split('.')
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20 and len(sentence) < 200:
                    sentence_lower = sentence.lower()
                    # If sentence contains multiple words from the issue, it's probably relevant
                    matches = sum(1 for word in issue_words[:5] if len(word) > 3 and word in sentence_lower)
                    if matches >= 2:
                        return sentence[:150] + "..." if len(sentence) > 150 else sentence
        
        # If no good quote found, use a generic one
        return "See document section for details"
    
    def _extract_json_violations(self, response: str) -> List[Dict[str, Any]]:
        """Try to extract violations from JSON format."""
        try:
            # Clean up response
            cleaned = response.strip()
            
            # Remove common prefixes
            prefixes = ["Here is the JSON output:", "Here's the JSON:", "JSON output:", "```json", "```"]
            for prefix in prefixes:
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):].strip()
            
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
            
            # Try multiple JSON extraction methods
            violations_data = None
            
            # Method 1: Complete JSON object
            try:
                violations_data = self._extract_complete_json_object(cleaned)
            except:
                pass
            
            # Method 2: Direct JSON parsing
            if not violations_data:
                try:
                    data = json.loads(cleaned)
                    violations_data = data.get("violations", [])
                except:
                    pass
            
            # Method 3: Array extraction
            if not violations_data:
                try:
                    violations_data = self._extract_violations_array(cleaned)
                except:
                    pass
            
            return violations_data if violations_data else []
            
        except Exception as e:
            if self.debug:
                print(f"JSON extraction failed: {e}")
            return []
    
    def _extract_complete_json_object(self, text: str) -> List[Dict]:
        """Extract complete JSON object with brace matching."""
        start = text.find('{')
        if start == -1:
            return []
        
        brace_count = 0
        end = -1
        
        for i in range(start, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i
                    break
        
        if end == -1:
            return []
        
        json_text = text[start:end + 1]
        data = json.loads(json_text)
        return data.get("violations", [])
    
    def _extract_violations_array(self, text: str) -> List[Dict]:
        """Extract just the violations array."""
        array_start = text.find('[')
        if array_start == -1:
            return []
        
        bracket_count = 0
        array_end = -1
        
        for i in range(array_start, len(text)):
            if text[i] == '[':
                bracket_count += 1
            elif text[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    array_end = i
                    break
        
        if array_end == -1:
            return []
        
        array_text = text[array_start:array_end + 1]
        return json.loads(array_text)
    
    def _is_no_violations_response(self, response: str) -> bool:
        """Check if response indicates no violations."""
        response_lower = response.lower()
        no_violation_phrases = [
            "no violations found",
            "no clear violations", 
            "no compliance issues",
            '"violations": []',
            '"violations":[]',
            "violations: []"
        ]
        return any(phrase in response_lower for phrase in no_violation_phrases)
    
    def _extract_violations_with_regex(self, response: str) -> List[Dict[str, Any]]:
        """Extract violations using regex patterns as fallback."""
        violations = []
        
        # Pattern for structured violation blocks - framework agnostic
        violation_pattern = r'(?:VIOLATION|Issue|Problem).*?:\s*([^\n]+).*?(?:Regulation|Section|Article|Rule|Standard).*?:\s*([^\n]+).*?(?:Citation|Quote).*?:\s*["\']?([^"\'\n]+)["\']?'
        
        matches = re.findall(violation_pattern, response, re.DOTALL | re.IGNORECASE)
        for match in matches:
            if len(match) >= 3 and len(match[0].strip()) > 5:
                violations.append({
                    "issue": match[0].strip(),
                    "regulation": match[1].strip(),
                    "citation": f'"{match[2].strip()}"'
                })
        
        return violations[:5]  # Limit to prevent spam