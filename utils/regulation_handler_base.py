# utils/regulation_handler_base.py

import re
from typing import Dict, Any, List, Optional

class RegulationHandlerBase:
    """Framework-agnostic base class with flexible structured parsing."""
    
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
        """Create a truly framework-agnostic analysis prompt with flexible output format."""
        
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

RESPONSE FORMAT - Use this natural but structured format:

If you find violations, list them like this:

VIOLATION 1:
Issue: [Clear violation description]
Regulation: [Specific regulation reference]
Citation: "[Exact quote from document showing violation]"

VIOLATION 2:
Issue: [Another violation description]
Regulation: [Another regulation reference]
Citation: "[Another exact quote]"

If no clear violations are found, respond with:
NO VIOLATIONS FOUND

EXAMPLES OF GOOD FINDINGS:
VIOLATION 1:
Issue: Data stored without time limits
Regulation: Regulation X requiring retention limits
Citation: "data will be retained indefinitely"

VIOLATION 2:
Issue: Required consent not obtained
Regulation: Regulation Y mandating consent
Citation: "no user authorization needed"

RULES:
- Each violation must cite a specific regulation from those provided above
- Each quote must appear exactly in the document text
- If uncertain about a potential violation, don't include it
- Use the structured format above for any violations found
- Let the regulations guide your analysis, not preconceptions"""
    
    def parse_llm_response(self, response: str, document_text: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """Parse flexible structured LLM response - framework agnostic."""
        
        if self.debug:
            print("=" * 50)
            print("DEBUG: Base Handler Flexible Parser")
            print(f"Response length: {len(response)}")
            print(f"Response preview: {response[:200]}...")
            print("=" * 50)
        
        result = {"issues": []}
        
        # Check for no violations first
        if "NO VIOLATIONS FOUND" in response.upper() or "no clear violations" in response.lower():
            if self.debug:
                print("DEBUG: No violations found")
            return result
        
        # Parse structured format - no JSON fallback needed!
        violations = self._parse_structured_violations(response)
        result["issues"] = violations
        
        if self.debug:
            print(f"DEBUG: Base handler found {len(violations)} violations")
        
        return result
    
    def _parse_structured_violations(self, response: str) -> List[Dict[str, Any]]:
        """Parse structured violation format (VIOLATION X: format)."""
        violations = []
        
        # Split response into potential violation blocks
        violation_pattern = r'VIOLATION\s+\d+:'
        blocks = re.split(violation_pattern, response, flags=re.IGNORECASE)
        
        # Skip the first block (it's before the first violation)
        for block in blocks[1:]:
            violation = self._parse_single_violation_block(block.strip())
            if violation:
                violations.append(violation)
        
        # Fallback: if no VIOLATION blocks found, try other structured patterns
        if not violations:
            violations = self._parse_alternative_structured_formats(response)
        
        return violations
    
    def _parse_single_violation_block(self, block: str) -> Optional[Dict[str, Any]]:
        """Parse a single violation block."""
        if not block.strip():
            return None
        
        violation = {}
        
        # Extract fields using regex patterns
        patterns = {
            'issue': [
                r'Issue:\s*([^\n]+)',
                r'Problem:\s*([^\n]+)',
                r'Violation:\s*([^\n]+)'
            ],
            'regulation': [
                r'Regulation:\s*([^\n]+)',
                r'Article:\s*([^\n]+)',
                r'Section:\s*([^\n]+)',
                r'Rule:\s*([^\n]+)'
            ],
            'citation': [
                r'Citation:\s*["\']([^"\']+)["\']',
                r'Citation:\s*"([^"]+)"',
                r'Citation:\s*\'([^\']+)\'',
                r'Citation:\s*([^\n]+)',
                r'Quote:\s*["\']([^"\']+)["\']',
                r'Text:\s*["\']([^"\']+)["\']'
            ],
            'explanation': [
                r'Explanation:\s*([^\n]+(?:\n(?!Issue:|Regulation:|Citation:|Explanation:)[^\n]+)*)',
                r'Reason:\s*([^\n]+(?:\n(?!Issue:|Regulation:|Citation:|Reason:)[^\n]+)*)'
            ]
        }
        
        # Extract each field
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, block, re.IGNORECASE | re.DOTALL)
                if match:
                    value = match.group(1).strip()
                    if value:
                        violation[field] = value
                        break
        
        # Validate minimum required fields
        if violation.get('issue') and violation.get('regulation'):
            # Clean up the citation (remove extra quotes if needed)
            citation = violation.get('citation', '')
            if citation and not (citation.startswith('"') or citation.startswith("'")):
                violation['citation'] = f'"{citation}"'
            elif not citation:
                violation['citation'] = 'No specific quote provided'
            
            return violation
        
        return None
    
    def _parse_alternative_structured_formats(self, response: str) -> List[Dict[str, Any]]:
        """Try to parse alternative structured formats."""
        violations = []
        
        # Try bullet point format
        bullet_patterns = [
            r'[-•*]\s*([^:]+):\s*([^,]+),\s*([^,]+),\s*["\']([^"\']+)["\']',
            r'[-•*]\s*([^:]+):\s*([^,]+),\s*([^,]+),\s*(.+)',
        ]
        
        for pattern in bullet_patterns:
            matches = re.findall(pattern, response, re.MULTILINE)
            for match in matches:
                if len(match) >= 3:
                    violation = {
                        'issue': match[0].strip(),
                        'regulation': match[1].strip(),
                        'citation': f'"{match[2].strip()}"' if len(match) > 2 else 'No quote provided'
                    }
                    if len(match) > 3:
                        violation['explanation'] = match[3].strip()
                    violations.append(violation)
        
        # Try simple line-by-line format
        if not violations:
            violations = self._parse_simple_lines(response)
        
        return violations
    
    def _parse_simple_lines(self, response: str) -> List[Dict[str, Any]]:
        """Parse simple line format as last resort."""
        violations = []
        lines = response.split('\n')
        
        current_violation = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for field patterns
            if line.lower().startswith(('issue:', 'problem:', 'violation:')):
                if current_violation.get('issue') and current_violation.get('regulation'):
                    violations.append(current_violation)
                current_violation = {'issue': line.split(':', 1)[1].strip()}
            elif line.lower().startswith(('regulation:', 'article:', 'section:')):
                current_violation['regulation'] = line.split(':', 1)[1].strip()
            elif line.lower().startswith(('citation:', 'quote:')):
                citation = line.split(':', 1)[1].strip()
                if not (citation.startswith('"') or citation.startswith("'")):
                    citation = f'"{citation}"'
                current_violation['citation'] = citation
        
        # Add final violation
        if current_violation.get('issue') and current_violation.get('regulation'):
            violations.append(current_violation)
        
        return violations
    
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