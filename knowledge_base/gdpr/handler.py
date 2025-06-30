import yaml
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

class RegulationHandler:
    """Simplified GDPR handler with flexible structured output."""
    
    def __init__(self, debug=False):
        self.debug = debug
        self.framework_dir = Path(__file__).parent
        
        # Load GDPR files (same as before)
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
                              regulation_framework: str = "gdpr",
                              risk_level: str = "unknown") -> str:
        """
        Create GDPR analysis prompt with flexible structured output format.
        """
        
        # Same GDPR expertise as before
        risk_guidance = ""
        if risk_level == "high":
            risk_guidance = "🔒 HIGH PRIORITY: This section involves personal data processing - apply strict EU privacy law scrutiny."
        elif risk_level == "low":  
            risk_guidance = "📋 LOW PRIORITY: This section appears non-data related - flag only obvious violations."
        
        return f"""Analyze this document section for GDPR compliance violations under EU privacy law.

🇪🇺 EU PRIVACY DOCUMENT SECTION: {section}

📄 DOCUMENT TEXT:
{text}

📋 RELEVANT GDPR ARTICLES:
{regulations}

🇪🇺 GDPR EU PRIVACY LAW FRAMEWORK:

KEY DEFINITIONS:
• Personal Data: Any information relating to an identified/identifiable natural person
• Data Subject: The individual whose personal data is being processed
• Controller: Entity determining purposes and means of processing
• Processor: Entity processing data on behalf of controller
• Special Categories: Sensitive data (health, biometric, genetic, etc.)

CORE PRINCIPLES (Article 5):
• Lawfulness, Fairness, Transparency
• Purpose Limitation
• Data Minimisation
• Accuracy
• Storage Limitation
• Integrity and Confidentiality
• Accountability

DATA SUBJECT RIGHTS (Articles 15-22):
• Access, Rectification, Erasure, Restriction, Portability, Objection

{risk_guidance}

🎯 EU PRIVACY LAW ANALYSIS:

You are a GDPR compliance expert analyzing this document under EU privacy law.
Apply the principles-based approach of GDPR focusing on individual rights and data protection.

🔍 GDPR VIOLATION ASSESSMENT:

1. LAWFULNESS (Article 6): Does the document describe processing without valid legal basis?
   - Look for: "no legal basis", "process without consent", "automatic processing"
   
2. TRANSPARENCY (Article 5): Is processing unfair or non-transparent to data subjects?
   - Look for: "hidden processing", "unclear purposes", "deceptive practices"
   
3. PURPOSE LIMITATION (Article 5): Is data used beyond original specified purposes?
   - Look for: "any purpose", "future uses", "secondary processing", "different purposes"
   
4. DATA MINIMISATION (Article 5): Is excessive data being collected/processed?
   - Look for: "all data", "maximum collection", "everything", "comprehensive data"
   
5. STORAGE LIMITATION (Article 5): Is data kept longer than necessary?
   - Look for: "indefinitely", "permanently", "forever", "no deletion"
   
6. CONSENT (Article 7): Is consent invalid (forced, bundled, unclear)?
   - Look for: "required consent", "bundled consent", "implied consent", "automatic opt-in"
   
7. DATA SUBJECT RIGHTS (Articles 15-22): Are individuals denied their rights?
   - Look for: "cannot access", "no deletion", "restricted rights", "no portability"

🇪🇺 EU PRIVACY REASONING PROCESS:

For each statement in the document:
1. Identify if it involves personal data processing
2. Check against specific GDPR article provided above
3. Apply EU privacy principles to determine compliance
4. Consider data subject rights and freedoms
5. Flag only clear violations with textual evidence

📋 RESPONSE FORMAT - Use this natural but structured format:

If you find violations, list them like this:

VIOLATION 1:
Issue: [Clear description of the violation]
Regulation: [Specific GDPR Article]
Citation: "[Exact quote from document]"
Explanation: [Brief explanation of why this violates GDPR]

VIOLATION 2:
Issue: [Another violation description]
Regulation: [Another GDPR Article]
Citation: "[Another exact quote]"
Explanation: [Why this is a violation]

If no clear violations are found, respond with:
NO VIOLATIONS FOUND

🇪🇺 EU PRIVACY EXAMPLES:
✅ GOOD: 
VIOLATION 1:
Issue: Data stored without time limit
Regulation: Article 5(1)(e)
Citation: "data retained indefinitely"
Explanation: Storage limitation principle requires data to be kept only as long as necessary

❌ BAD: Flagging compliant statements like "We respect privacy" or "GDPR compliance maintained"

🎯 FINAL INSTRUCTION:
Base your analysis ONLY on the GDPR articles provided above. Consider the rights and freedoms of data subjects. Use the structured format above for any violations found.
"""
    
    def parse_llm_response(self, response: str, document_text: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse LLM response using the new flexible structured format.
        """
        
        if self.debug:
            print(f"GDPR Handler: Parsing response of length {len(response)}")
        
        result = {"issues": []}
        
        # Check for no violations
        if "NO VIOLATIONS FOUND" in response.upper() or "no clear violations" in response.lower():
            if self.debug:
                print("GDPR Handler: No violations found")
            return result
        
        # Parse structured violations
        violations = self._parse_structured_violations(response)
        
        if self.debug:
            print(f"GDPR Handler: Found {len(violations)} violations")
        
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
                r'Article:\s*([^\n]+)',
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
        
        # Last resort: try to find any article references with nearby text
        if not violations:
            violations = self._extract_article_references(response)
        
        return violations
    
    def _extract_article_references(self, response: str) -> List[Dict[str, Any]]:
        """Extract article references as a last resort."""
        violations = []
        
        # Look for Article references with surrounding context
        article_pattern = r'(Article\s+\d+[^.]*?)\.([^.]+\.)'
        matches = re.findall(article_pattern, response, re.IGNORECASE)
        
        for article_ref, context in matches:
            if len(context.strip()) > 10:  # Only meaningful context
                violation = {
                    'issue': context.strip()[:100],  # First 100 chars as issue
                    'regulation': article_ref.strip(),
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
            reg_id = reg.get("id", f"GDPR Regulation {i+1}")
            
            # Basic truncation
            if len(reg_text) > 400:
                reg_text = reg_text[:400] + "..."
            
            formatted_regs.append(f"📋 {reg_id}:\n{reg_text}")
        
        return "\n\n".join(formatted_regs)