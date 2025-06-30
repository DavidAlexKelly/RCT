import yaml
from typing import Dict, Any, List
from pathlib import Path
import sys

# Import base handler
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.regulation_handler_base import RegulationHandlerBase

class RegulationHandler(RegulationHandlerBase):
    """HIPAA specialist with semantic reasoning and principle-based analysis."""
    
    def __init__(self, debug=False):
        super().__init__(debug)
        self.name = "HIPAA"
        self.framework_dir = Path(__file__).parent
        
        # Load regulated topics from classification file
        with open(self.framework_dir / "classification.yaml", 'r') as f:
            self.classification = yaml.safe_load(f)
        
        self.regulated_topics = self.classification.get('regulated_topics', {})
        self.analysis_threshold = self.classification.get('analysis_threshold', 2)
        
        if self.debug:
            print(f"HIPAA Handler: Loaded {len(self.regulated_topics)} topic categories")
    
    def _infer_regulation_from_issue(self, issue: str) -> str:
        """HIPAA-specific regulation inference from issue content."""
        issue_lower = issue.lower()
        
        # HIPAA-specific patterns for different regulation types
        patterns = {
            "authorization": "§164.508",
            "without authorization": "§164.508",
            "consent": "§164.508", 
            "permission": "§164.508",
            "business associate": "§164.314",
            "baa": "§164.314",
            "contractor": "§164.314",
            "vendor": "§164.314",
            "third party": "§164.314",
            "safeguards": "§164.308",
            "administrative": "§164.308",
            "physical safeguards": "§164.310",
            "technical safeguards": "§164.312",
            "encryption": "§164.312",
            "security": "§164.308",
            "access control": "§164.312",
            "authentication": "§164.312",
            "audit": "§164.312",
            "breach notification": "§164.404",
            "breach": "§164.404",
            "60 days": "§164.404",
            "90 days": "§164.404",
            "notification": "§164.404",
            "privacy officer": "§164.530",
            "security officer": "§164.308",
            "training": "§164.308",
            "workforce": "§164.308",
            "phi": "§164.502",
            "protected health": "§164.502",
            "minimum necessary": "§164.502",
            "marketing": "§164.508",
            "research": "§164.508",
            "access": "§164.524",
            "amendment": "§164.526",
            "accounting": "§164.528",
            "notice": "§164.520"
        }
        
        for keyword, regulation in patterns.items():
            if keyword in issue_lower:
                return regulation
        
        return "§164.502"  # Clean fallback
    
    def create_prompt(self, text: str, section: str, regulations: List[Dict[str, Any]]) -> str:
        """Create HIPAA-specific analysis prompt focusing on semantic reasoning and regulatory principles."""
        
        # Format regulations for prompt
        formatted_regs = []
        for reg in regulations:
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", "Unknown")
            if len(reg_text) > 400:
                reg_text = reg_text[:400] + "..."
            formatted_regs.append(f"{reg_id}:\n{reg_text}")
        
        regulations_text = "\n\n".join(formatted_regs)
        
        return f"""You are a HIPAA compliance expert. Analyze this SINGLE document section for HIPAA violations.

DOCUMENT SECTION: {section}
DOCUMENT TEXT:
{text}

RELEVANT HIPAA SECTIONS:
{regulations_text}

TASK: Identify any clear HIPAA violations you can see in this document section.

ANALYSIS STEPS:
1. Read the document text carefully
2. Compare it against the HIPAA sections provided above
3. Look for practices or statements that you believe violate the HIPAA requirements provided
4. Only report violations where you can find direct supporting evidence in the text
5. If the section appears compliant or you're unsure, report no violations

USE ONLY THE HIPAA SECTIONS PROVIDED ABOVE:
- Base your analysis solely on the regulations provided in the "RELEVANT HIPAA SECTIONS" section
- Do not reference sections not provided in the regulations list
- Focus on clear violations of the specific HIPAA requirements given to you

STRICT REQUIREMENTS:

1. ONLY REPORT CLEAR VIOLATIONS
   - Report violations only when you believe you can see them in the document text
   - Each violation must have strong supporting evidence from the document
   - If you're unsure don't report it

2. QUOTE IS MANDATORY:
   - Extract up to 40 words directly from the document text above
   - Quote must prove the violation exists
   - NO GENERIC QUOTES allowed
   - If you cannot find a supporting quote, report no violations

3. REGULATION FORMAT:
   - Use the exact section reference from the regulations provided above
   - Match the format used in the "RELEVANT HIPAA SECTIONS" section
   - No extra words, descriptions, or punctuation

4. ISSUE FORMAT:
   - State violation in up to 20 words
   - Be specific about what HIPAA requirement is violated

RESPONSE FORMAT:
{{
    "violations": [
        {{
            "issue": "Specific violation in up to 15 words",
            "regulation": "Section reference from list above",
            "quote": "up to 40 word quote from document text"
        }},
        {{
            "issue": "Another specific violation in up to 15 words", 
            "regulation": "Different section reference from list above",
            "quote": "up to 40 word quote from document text"
        }}
    ]
}}

VALIDATION CHECKLIST:
- [ ] All quotes are up to 40 words from the actual document text above
- [ ] All regulation formats match ones from the "RELEVANT HIPAA SECTIONS" section
- [ ] Each violation is demonstrated by the quoted text
- [ ] Only reporting violations that are present in the document
- [ ] If uncertain about a violation, it was NOT reported

If no clear violations with supporting quotes: {{"violations": []}}

Response must be valid JSON only.

IMPORTANT: Be conservative in your analysis. Only report violations that are clearly and obviously present in the document text. It's better to miss a borderline violation than to report something that isn't clearly there."""