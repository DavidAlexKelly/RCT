import json
import yaml
import re
from typing import Dict, Any, List
from pathlib import Path

class RegulationHandler:
    """HIPAA specialist using topic-based flagging approach."""
    
    def __init__(self, debug=False):
        self.debug = debug
        self.name = "HIPAA"
        self.framework_dir = Path(__file__).parent
        
        # Load regulated topics from classification file
        with open(self.framework_dir / "classification.yaml", 'r') as f:
            self.classification = yaml.safe_load(f)
        
        self.regulated_topics = self.classification.get('regulated_topics', {})
        self.analysis_threshold = self.classification.get('analysis_threshold', 2)
        
        if self.debug:
            print(f"HIPAA Handler: Loaded {len(self.regulated_topics)} topic categories")
    
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
            print(f"\n=== HIPAA TOPIC ANALYSIS ===")
            print(f"Text preview: {text[:200]}...")
            print(f"Topics found: {list(topics_found.keys())}")
            print(f"Topic count: {score}")
            print(f"Threshold: {self.analysis_threshold}")
            print("=" * 40)
        
        return score
    
    def should_analyze(self, text: str) -> bool:
        """Analyze if text deals with multiple regulated topics."""
        topic_count = self.calculate_risk_score(text)
        return topic_count >= self.analysis_threshold
    
    def create_prompt(self, text: str, section: str, regulations: List[Dict[str, Any]]) -> str:
        """Create HIPAA-specific analysis prompt."""
        
        # Format regulations for prompt
        formatted_regs = []
        for reg in regulations:
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", "Unknown")
            if len(reg_text) > 300:
                reg_text = reg_text[:300] + "..."
            formatted_regs.append(f"{reg_id}:\n{reg_text}")
        
        regulations_text = "\n\n".join(formatted_regs)
        
        return f"""You are a HIPAA compliance expert analyzing healthcare data protection violations.

🏥 DOCUMENT SECTION: {section}

📄 DOCUMENT TEXT:
{text}

📋 RELEVANT HIPAA SECTIONS:
{regulations_text}

🎯 ANALYSIS TASK:
Find clear HIPAA violations in the document text. Focus on these key areas:

1. PHI AUTHORIZATION VIOLATIONS:
   - Sharing PHI without authorization ("without authorization", "no authorization required")
   - Unauthorized access to PHI ("unlimited access", "vendor access")
   - Automatic PHI sharing ("automatic sharing", "share with anyone")

2. BUSINESS ASSOCIATE VIOLATIONS:
   - Third parties accessing PHI without BAAs ("no business associate agreement", "contractor access")
   - Vendor access without proper agreements ("outsourced without")

3. SAFEGUARDS VIOLATIONS:
   - Inadequate security measures ("basic security", "no encryption", "minimal security")
   - Poor physical safeguards ("disposed in trash", "thrown in trash")
   - Missing technical safeguards ("unencrypted phi", "plain text", "weak passwords")
   - No administrative safeguards ("untrained staff", "no training")

4. BREACH NOTIFICATION FAILURES:
   - Delayed notification ("90 days" - should be 60 for HIPAA)
   - Missing notifications ("no breach notification", "hidden breach")
   - Unreported incidents ("not reported")

5. MISSING REQUIRED ROLES:
   - No privacy officer ("no privacy officer")
   - No security officer ("no security officer")

6. IMPROPER PHI USE:
   - Marketing without authorization ("marketing use", "sell patient data")
   - Research without proper authorization ("research without consent")

CRITICAL INSTRUCTION: Return ONLY the JSON object below, with no additional text, explanations, or formatting:

{{
    "violations": [
        {{
            "issue": "Clear description of the HIPAA violation",
            "regulation": "Specific HIPAA Section (e.g., §164.502)",
            "quote": "Exact text from document that shows the violation"
        }}
    ]
}}

If no clear violations are found: {{"violations": []}}

IMPORTANT: Do not include any text before or after the JSON. Start your response with {{ and end with }}.

Base your analysis ONLY on the HIPAA sections provided above. Only flag clear, obvious violations with direct textual evidence."""
    
    def parse_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response with robust JSON extraction and fallbacks."""
        
        if self.debug:
            print(f"\n=== HIPAA RESPONSE PARSING DEBUG ===")
            print(f"Full LLM response ({len(response)} chars):")
            print(f"'{response}'")
            print("=" * 50)
        
        try:
            # Method 1: Try to extract and parse JSON
            violations = self._extract_json_violations(response)
            if violations:
                if self.debug:
                    print(f"SUCCESS: Extracted {len(violations)} violations via JSON parsing")
                return violations
            
            # Method 2: Check for explicit "no violations" response
            if self._is_no_violations_response(response):
                if self.debug:
                    print("SUCCESS: LLM indicated no violations found")
                return []
            
            # Method 3: Try regex extraction for common patterns
            violations = self._extract_violations_with_regex(response)
            if violations:
                if self.debug:
                    print(f"SUCCESS: Extracted {len(violations)} violations via regex")
                return violations
            
            # Method 4: Try to find any violation-like text
            violations = self._extract_violations_with_keywords(response)
            if violations:
                if self.debug:
                    print(f"SUCCESS: Extracted {len(violations)} violations via keyword matching")
                return violations
            
            # If all methods fail, provide detailed error
            error_msg = f"Could not parse any violations from LLM response. Response preview: {response[:300]}..."
            if self.debug:
                print(f"FAILED: {error_msg}")
            raise ValueError(error_msg)
            
        except Exception as e:
            if self.debug:
                print(f"PARSING EXCEPTION: {e}")
                print(f"Full response: {response}")
            raise ValueError(f"Failed to parse HIPAA response: {e}")
    
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
            json_methods = [
                self._extract_complete_json_object,
                self._extract_violations_array,
                self._parse_direct_json
            ]
            
            for method in json_methods:
                try:
                    violations = method(cleaned)
                    if violations:
                        return self._format_violations(violations)
                except:
                    continue
            
            return []
            
        except Exception:
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
        # Look for array pattern
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
    
    def _parse_direct_json(self, text: str) -> List[Dict]:
        """Try parsing the text directly as JSON."""
        return json.loads(text).get("violations", [])
    
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
        """Extract violations using regex patterns."""
        violations = []
        
        # Pattern for structured violation blocks
        violation_pattern = r'(?:VIOLATION|Issue|Problem).*?:\s*([^\n]+).*?(?:Regulation|Section).*?:\s*([^\n]+).*?(?:Citation|Quote).*?:\s*["\']?([^"\'\n]+)["\']?'
        
        matches = re.findall(violation_pattern, response, re.DOTALL | re.IGNORECASE)
        for match in matches:
            if len(match) >= 3 and len(match[0].strip()) > 10:
                violations.append({
                    "issue": match[0].strip(),
                    "regulation": match[1].strip(),
                    "quote": match[2].strip()
                })
        
        return violations
    
    def _extract_violations_with_keywords(self, response: str) -> List[Dict[str, Any]]:
        """Extract violations by looking for violation keywords."""
        violations = []
        
        # Look for common violation indicators
        violation_keywords = ["violat", "breach", "non-compliant", "illegal", "unauthorized", "inadequate"]
        
        sentences = response.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and any(keyword in sentence.lower() for keyword in violation_keywords):
                violations.append({
                    "issue": sentence[:100] + "..." if len(sentence) > 100 else sentence,
                    "regulation": "Unknown section", 
                    "quote": sentence[:50] + "..." if len(sentence) > 50 else sentence
                })
        
        return violations[:3]  # Limit to 3 violations to avoid spam
    
    def _format_violations(self, violations: List[Dict]) -> List[Dict[str, Any]]:
        """Format violations to standard format."""
        formatted = []
        
        for violation in violations:
            if not isinstance(violation, dict):
                continue
            
            # Handle different possible field names
            issue = violation.get("issue") or violation.get("problem") or violation.get("violation", "")
            regulation = violation.get("regulation") or violation.get("section") or violation.get("rule", "")
            quote = violation.get("quote") or violation.get("citation") or violation.get("text", "")
            
            if issue and issue.strip():
                formatted.append({
                    "issue": str(issue).strip(),
                    "regulation": str(regulation).strip() if regulation else "Unknown",
                    "citation": f'"{str(quote).strip()}"' if quote else '""'
                })
        
        return formatted