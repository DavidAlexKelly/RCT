# utils/regulation_handler_base.py

import re
import json
from typing import Dict, Any, List, Optional

class RegulationHandlerBase:
    """Framework-agnostic base class with generic analysis approach."""
    
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
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str,
                              content_indicators: Optional[Dict[str, str]] = None,
                              potential_violations: Optional[List[Dict[str, Any]]] = None,
                              regulation_framework: str = "",
                              risk_level: str = "unknown") -> str:
        """Create a truly framework-agnostic analysis prompt that lets LLM reason."""
        
        # Risk-based guidance
        risk_guidance = ""
        if risk_level == "high":
            risk_guidance = "IMPORTANT: This section appears high-risk - be thorough in analysis."
        elif risk_level == "low":  
            risk_guidance = "IMPORTANT: This section appears low-risk - only flag clear, obvious violations."
        
        # Framework context (minimal - just for LLM awareness)
        framework_context = ""
        if regulation_framework:
            framework_context = f"Regulatory Framework: {regulation_framework.upper()}"
        
        return f"""Analyze this document section for regulatory compliance violations.

{framework_context}
DOCUMENT SECTION: {section}

DOCUMENT TEXT:
{text}

RELEVANT REGULATIONS:
{regulations}

{risk_guidance}

TASK: Compare the document text against the regulations provided above. Find any statements that clearly violate the regulatory requirements.

ANALYSIS APPROACH:
1. Read each regulation carefully to understand what it requires or prohibits
2. Examine the document text for statements that contradict these requirements
3. Look for actions described in the document that violate regulatory principles
4. Identify missing required procedures, safeguards, or rights
5. Focus on clear, provable violations with direct textual evidence

WHAT TO FLAG:
- Direct contradictions of regulatory requirements
- Explicit violations of stated compliance obligations  
- Missing mandatory elements specified in regulations
- Prohibited actions or practices described in the document
- Inadequate implementations of required safeguards

WHAT NOT TO FLAG:
- Compliant statements like "We implement security measures" or "Users can access their data"
- Vague language that could be interpreted multiple ways
- Policies that seem reasonable but aren't specifically addressed by the provided regulations
- Minor wording differences that don't affect compliance substance

CRITICAL INSTRUCTIONS:
- Base your analysis ONLY on the specific regulations provided above
- The regulations are your authority - not general assumptions about compliance
- Be precise and conservative - only flag clear violations
- Use exact quotes from the document to support each finding
- Reference specific regulations that are being violated

RESPONSE FORMAT - Return ONLY a JSON array:
[
["Clear violation description", "Specific regulation reference", "Exact quote from document showing violation"],
["Another violation description", "Another regulation reference", "Another exact quote"]
]

EXAMPLES OF GOOD FINDINGS:
["Data stored without time limits", "Regulation X requiring retention limits", "data will be retained indefinitely"]
["Required consent not obtained", "Regulation Y mandating consent", "no user authorization needed"]

RULES:
- Each violation must cite a specific regulation from those provided above
- Each quote must appear exactly in the document text
- If uncertain about a potential violation, don't include it
- If no clear violations are found, return: []
- Let the regulations guide your analysis, not preconceptions"""
    
    def parse_llm_response(self, response: str, document_text: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """Parse array-based LLM response - framework agnostic."""
        
        if self.debug:
            print("=" * 50)
            print("DEBUG: Base Handler Array Parser")
            print(f"Response length: {len(response)}")
            print(f"Response: {response}")
            print("=" * 50)
        
        result = {"issues": []}
        
        try:
            # Extract JSON array from response
            array_text = self._extract_json_array(response)
            
            if not array_text:
                if self.debug:
                    print("DEBUG: No JSON array found in response")
                # Check for explicit "no issues" indicators
                no_issues_phrases = ["no compliance issues", "no violations", "no clear violations", "[]"]
                if any(phrase in response.lower() for phrase in no_issues_phrases):
                    return result
                else:
                    # Try fallback parsing
                    return self._fallback_array_parsing(response)
            
            if self.debug:
                print(f"DEBUG: Extracted array: {array_text}")
            
            # Parse JSON
            violations = json.loads(array_text)
            
            if self.debug:
                print(f"DEBUG: Parsed {len(violations)} violations from array")
            
            # Convert to standard format
            for violation in violations:
                if self._is_valid_violation_array(violation):
                    issue_desc = str(violation[0]).strip()
                    regulation = str(violation[1]).strip()
                    citation = str(violation[2]).strip()
                    
                    # Format citation
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
                        print(f"  Added: {issue_desc[:40]}... [{regulation}]")
                else:
                    if self.debug:
                        print(f"DEBUG: Skipping invalid violation: {violation}")
            
        except json.JSONDecodeError as e:
            if self.debug:
                print(f"DEBUG: JSON parsing failed: {e}")
                print("DEBUG: Attempting fallback parsing...")
            
            result = self._fallback_array_parsing(response)
            
        except Exception as e:
            if self.debug:
                print(f"DEBUG: Unexpected error: {e}")
            result = {"issues": []}
        
        if self.debug:
            print(f"DEBUG: Base handler found {len(result['issues'])} violations")
        
        return result
    
    def _extract_json_array(self, response: str) -> str:
        """Extract JSON array from response text."""
        
        # Find the first opening bracket
        start = response.find('[')
        if start == -1:
            return ""
        
        # Find the matching closing bracket
        bracket_count = 0
        end = -1
        
        for i in range(start, len(response)):
            if response[i] == '[':
                bracket_count += 1
            elif response[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end = i
                    break
        
        if end == -1:
            return ""
        
        # Extract and clean the array
        array_text = response[start:end + 1]
        array_text = array_text.replace('\n', ' ')
        array_text = re.sub(r'\s+', ' ', array_text)
        
        return array_text
    
    def _is_valid_violation_array(self, violation) -> bool:
        """Check if violation array has correct format."""
        return (
            isinstance(violation, list) and 
            len(violation) >= 3 and
            len(str(violation[0]).strip()) > 5 and  # Meaningful description
            len(str(violation[1]).strip()) > 0      # Some regulation reference
        )
    
    def _fallback_array_parsing(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Fallback parsing using regex if JSON fails."""
        result = {"issues": []}
        
        if self.debug:
            print("DEBUG: Using regex fallback parsing...")
        
        # Look for array-like patterns
        patterns = [
            r'\[\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"\s*\]',
            r"\[\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\s*\]",
            r'\[\s*"([^"]*)",\s*"([^"]*)",\s*\'([^\']*)\'\s*\]'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                if len(match) == 3 and len(match[0].strip()) > 5:
                    result["issues"].append({
                        "issue": match[0].strip(),
                        "regulation": match[1].strip(),
                        "citation": f'"{match[2].strip()}"'
                    })
                    
                    if self.debug:
                        print(f"  Fallback found: {match[0][:40]}...")
        
        return result
    
    def format_regulations(self, regulations: List[Dict[str, Any]], 
                         regulation_context: str = "", regulation_patterns: str = "") -> str:
        """Format regulations for prompts."""
        formatted_regs = []
        
        if regulation_context:
            formatted_regs.append(f"CONTEXT:\n{regulation_context[:500]}...")
        
        for i, reg in enumerate(regulations):
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", f"Regulation {i+1}")
            
            # Truncate long texts for better prompt efficiency
            if len(reg_text) > 300:
                reg_text = reg_text[:300] + "..."
            
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