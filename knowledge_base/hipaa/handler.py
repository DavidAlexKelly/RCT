import yaml
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

class RegulationHandler:
    """Simplified HIPAA handler with flexible structured output."""
    
    def __init__(self, debug=False):
        self.debug = debug
        self.framework_dir = Path(__file__).parent
        
        # Load HIPAA files (same as before)
        with open(self.framework_dir / "classification.yaml", 'r') as f:
            self.classification = yaml.safe_load(f)
        
        with open(self.framework_dir / "context.yaml", 'r') as f:
            self.context = yaml.safe_load(f)
    
    def get_classification_terms(self, term_type: str) -> List[str]:
        """Same as before - no change needed."""
        return self.classification.get(term_type, [])
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str,
                              content_indicators: Optional[Dict] = None,
                              potential_violations: Optional[List] = None,
                              regulation_framework: str = "hipaa",
                              risk_level: str = "unknown") -> str:
        """
        Create HIPAA analysis prompt with flexible structured output format.
        """
        
        # Same HIPAA expertise as before
        risk_guidance = ""
        if risk_level == "high":
            risk_guidance = "🏥 HIGH PRIORITY: This section involves healthcare data handling - apply strict HIPAA scrutiny."
        elif risk_level == "low":
            risk_guidance = "📋 LOW PRIORITY: This section appears administrative - flag only obvious violations."
        
        return f"""Analyze this healthcare document section for HIPAA compliance violations.

🏥 HEALTHCARE DOCUMENT SECTION: {section}

📄 DOCUMENT TEXT:
{text}

📋 RELEVANT HIPAA REGULATIONS:
{regulations}

🏥 HIPAA HEALTHCARE COMPLIANCE FRAMEWORK:

KEY DEFINITIONS:
• Protected Health Information (PHI): Any individually identifiable health information
• Covered Entities: Healthcare providers, health plans, clearinghouses
• Business Associates: Third parties handling PHI for covered entities
• Minimum Necessary: Limit PHI to minimum needed for purpose

REQUIRED SAFEGUARDS:
• Administrative: Policies, procedures, and workforce training requirements
• Physical: Protect electronic systems, equipment, and media
• Technical: Technology controls for electronic PHI access

INDIVIDUAL RIGHTS:
• Access to own PHI, amendment requests, restriction requests
• Accounting of disclosures, confidential communications
• Breach notification within 60 days

{risk_guidance}

🎯 HEALTHCARE COMPLIANCE ANALYSIS:

You are a HIPAA compliance expert analyzing this healthcare document. 
Examine how Protected Health Information (PHI) is handled against HIPAA requirements.

🔍 HIPAA VIOLATION ASSESSMENT:

1. PHI AUTHORIZATION: Does the document describe using/disclosing PHI without proper authorization?
   - Look for: "shared without consent", "no authorization required", "automatic sharing"
   
2. BUSINESS ASSOCIATES: Are third parties accessing PHI without Business Associate Agreements?
   - Look for: "vendors access PHI", "no contracts required", "third parties handle data"
   
3. INDIVIDUAL RIGHTS: Are patients denied their HIPAA rights?
   - Look for: "cannot access records", "no amendment allowed", "restricted rights"
   
4. SAFEGUARDS: Are administrative, physical, or technical safeguards inadequate?
   - Look for: "basic security", "no encryption", "minimal protection", "disposed in trash"
   
5. BREACH NOTIFICATION: Are breach procedures inadequate?
   - Look for: "90 days notification" (should be 60), "no patient notification", "optional reporting"
   
6. MINIMUM NECESSARY: Is excessive PHI being used/disclosed?
   - Look for: "entire medical record", "all patient data", "unlimited access"

🏥 HEALTHCARE REASONING PROCESS:

For each statement in the document:
1. Identify if it involves PHI handling
2. Check against specific HIPAA regulation provided above
3. Determine if practice violates HIPAA requirements
4. Consider healthcare context (treatment/payment/operations have different rules)
5. Flag only clear violations with textual evidence

📋 RESPONSE FORMAT - Use this natural but structured format:

If you find violations, list them like this:

VIOLATION 1:
Issue: [Clear description of the HIPAA violation]
Regulation: [Specific HIPAA section (§164.xxx)]
Citation: "[Exact quote from document]"
Explanation: [Brief explanation of why this violates HIPAA]

VIOLATION 2:
Issue: [Another violation description]
Regulation: [Another HIPAA section]
Citation: "[Another exact quote]"
Explanation: [Why this is a violation]

If no clear violations are found, respond with:
NO VIOLATIONS FOUND

🏥 HEALTHCARE EXAMPLES:
✅ GOOD:
VIOLATION 1:
Issue: PHI shared without authorization
Regulation: §164.502
Citation: "patient data shared with companies without consent"
Explanation: HIPAA requires authorization for PHI disclosure outside treatment/payment/operations

❌ BAD: Flagging compliant statements like "We protect patient privacy" or "HIPAA training provided"

🎯 FINAL INSTRUCTION:
Base your analysis ONLY on the HIPAA regulations provided above. Focus on PHI protection, not general healthcare practices. Use the structured format above for any violations found.
"""
    
    def parse_llm_response(self, response: str, document_text: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse LLM response using the new flexible structured format.
        """
        
        if self.debug:
            print(f"HIPAA Handler: Parsing response of length {len(response)}")
        
        result = {"issues": []}
        
        # Check for no violations
        if "NO VIOLATIONS FOUND" in response.upper() or "no clear violations" in response.lower():
            if self.debug:
                print("HIPAA Handler: No violations found")
            return result
        
        # Parse structured violations
        violations = self._parse_structured_violations(response)
        
        if self.debug:
            print(f"HIPAA Handler: Found {len(violations)} violations")
        
        result["issues"] = violations
        return result
    
    def _parse_structured_violations(self, response: str) -> List[Dict[str, Any]]:
        """Parse structured violation format."""
        violations = []
        
        # Split response into potential violation blocks
        # Look for "VIOLATION X:" patterns
        violation_pattern = r'VIOLATION\s+\d+:'
        blocks = re.split(violation_pattern, response, flags=re.IGNORECASE)
        
        # Skip the first block (it's before the first violation)
        for block in blocks[1:]:
            violation = self._parse_single_violation(block.strip())
            if violation:
                violations.append(violation)
        
        # Fallback: if no VIOLATION blocks found, try other patterns
        if not violations:
            violations = self._parse_alternative_formats(response)
        
        return violations
    
    def _parse_single_violation(self, block: str) -> Optional[Dict[str, Any]]:
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
    
    def _parse_alternative_formats(self, response: str) -> List[Dict[str, Any]]:
        """Try to parse alternative formats or fallback patterns."""
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
        
        # Last resort: try to find any section references with nearby text
        if not violations:
            violations = self._extract_section_references(response)
        
        return violations
    
    def _extract_section_references(self, response: str) -> List[Dict[str, Any]]:
        """Extract HIPAA section references as a last resort."""
        violations = []
        
        # Look for HIPAA section references with surrounding context
        section_patterns = [
            r'(§\s*164\.\d+[^.]*?)\.([^.]+\.)',
            r'(Section\s+164\.\d+[^.]*?)\.([^.]+\.)'
        ]
        
        for pattern in section_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for section_ref, context in matches:
                if len(context.strip()) > 10:  # Only meaningful context
                    violation = {
                        'issue': context.strip()[:100],  # First 100 chars as issue
                        'regulation': section_ref.strip(),
                        'citation': 'Context from response'
                    }
                    violations.append(violation)
        
        return violations
    
    def format_regulations(self, regulations: List[Dict[str, Any]], 
                         regulation_context: str = "", regulation_patterns: str = "") -> str:
        """Format regulations for prompts."""
        formatted_regs = []
        
        for i, reg in enumerate(regulations):
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", f"HIPAA Regulation {i+1}")
            
            # Basic truncation
            if len(reg_text) > 400:
                reg_text = reg_text[:400] + "..."
            
            formatted_regs.append(f"📋 {reg_id}:\n{reg_text}")
        
        return "\n\n".join(formatted_regs)