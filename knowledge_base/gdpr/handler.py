import yaml
from typing import Dict, Any, List
from pathlib import Path
import sys

# Import base handler
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.regulation_handler_base import RegulationHandlerBase

class RegulationHandler(RegulationHandlerBase):
    """GDPR specialist with semantic reasoning and principle-based analysis."""
    
    def __init__(self, debug=False):
        super().__init__(debug)
        self.name = "GDPR"
        self.framework_dir = Path(__file__).parent
        
        # Load regulated topics from classification file
        with open(self.framework_dir / "classification.yaml", 'r') as f:
            self.classification = yaml.safe_load(f)
        
        self.regulated_topics = self.classification.get('regulated_topics', {})
        self.analysis_threshold = self.classification.get('analysis_threshold', 2)
        
        if self.debug:
            print(f"GDPR Handler: Loaded {len(self.regulated_topics)} topic categories")
    
    def _infer_regulation_from_issue(self, issue: str) -> str:
        """GDPR-specific regulation inference from issue content."""
        issue_lower = issue.lower()
        
        # GDPR-specific patterns for different regulation types
        patterns = {
            "consent": "Article 7",
            "indefinite": "Article 5(1)(e)",
            "retention": "Article 5(1)(e)", 
            "storage": "Article 5(1)(e)",
            "forever": "Article 5(1)(e)",
            "permanently": "Article 5(1)(e)",
            "security": "Article 32",
            "encryption": "Article 32",
            "access": "Article 15",
            "deletion": "Article 17",
            "transparency": "Article 5(1)(a)",
            "legal basis": "Article 6",
            "data protection by": "Article 25",
            "data minimization": "Article 5(1)(c)",
            "purpose limitation": "Article 5(1)(b)",
            "accuracy": "Article 5(1)(d)",
            "automated": "Article 22",
            "profiling": "Article 22",
            "withdraw": "Article 7(3)",
            "portability": "Article 20",
            "rectification": "Article 16",
            "breach": "Article 33"
        }
        
        for keyword, regulation in patterns.items():
            if keyword in issue_lower:
                return regulation
        
        return "Article 6"  # Clean fallback
    
    def create_prompt(self, text: str, section: str, regulations: List[Dict[str, Any]]) -> str:
        """Create GDPR-specific analysis prompt focusing on semantic reasoning and regulatory principles."""
        
        # Format regulations for prompt
        formatted_regs = []
        for reg in regulations:
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", "Unknown")
            if len(reg_text) > 400:
                reg_text = reg_text[:400] + "..."
            formatted_regs.append(f"{reg_id}:\n{reg_text}")
        
        regulations_text = "\n\n".join(formatted_regs)
        
        return f"""You are a GDPR compliance expert. Analyze this SINGLE document section for GDPR violations.

DOCUMENT SECTION: {section}
DOCUMENT TEXT:
{text}

RELEVANT GDPR ARTICLES:
{regulations_text}

TASK: Identify any clear GDPR violations you can see in this document section.

ANALYSIS STEPS:
1. Read the document text carefully
2. Compare it against the GDPR articles provided above
3. Look for practices or statements that you believe violate the GDPR requirements provided
4. Only report violations where you can find direct supporting evidence in the text
5. If the section appears compliant or you're unsure, report no violations

USE ONLY THE GDPR ARTICLES PROVIDED ABOVE:
- Base your analysis solely on the regulations provided in the "RELEVANT GDPR ARTICLES" section
- Do not reference articles not provided in the regulations list
- Focus on clear violations of the specific GDPR requirements given to you

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
   - Use the exact article reference from the regulations provided above
   - Match the format used in the "RELEVANT GDPR ARTICLES" section
   - No extra words, descriptions, or punctuation

4. ISSUE FORMAT:
   - State violation in up to 20 words
   - Be specific about what GDPR principle is violated

RESPONSE FORMAT:
{{
    "violations": [
        {{
            "issue": "Specific violation in up to 15 words",
            "regulation": "Regulation reference from list above",
            "quote": "up to 40 word quote from document text"
        }},
        {{
            "issue": "Another specific violation in up to 15 words",
            "regulation": "Different regulation reference from list above", 
            "quote": "up to 40 word quote from document text"
        }}
    ]
}}

VALIDATION CHECKLIST:
- [ ] All quotes are up to 40 words from the actual document text above
- [ ] All regulation formats match ones from the "RELEVANT GDPR ARTICLES" section
- [ ] Each violation is demonstrated by the quoted text
- [ ] Only reporting violations that are present in the document
- [ ] If uncertain about a violation, it was NOT reported

If no clear violations with supporting quotes: {{"violations": []}}

Response must be valid JSON only.

IMPORTANT: Be conservative in your analysis. Only report violations that are obviously present in the document text. It's better to miss a borderline violation than to report something that isn't clearly there."""