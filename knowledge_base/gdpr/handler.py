import yaml
from typing import Dict, Any, List
from pathlib import Path
import sys

# Import base handler
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.regulation_handler_base import RegulationHandlerBase

class RegulationHandler(RegulationHandlerBase):
    """GDPR specialist with balanced detection and validation."""
    
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
            "accuracy": "Article 5(1)(d)"
        }
        
        for keyword, regulation in patterns.items():
            if keyword in issue_lower:
                return regulation
        
        return "Relevant GDPR Article"  # GDPR-specific fallback
    
    def create_prompt(self, text: str, section: str, regulations: List[Dict[str, Any]]) -> str:
        """Create GDPR-specific analysis prompt with balanced requirements."""
        
        # Format regulations for prompt
        formatted_regs = []
        for reg in regulations:
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", "Unknown")
            if len(reg_text) > 400:
                reg_text = reg_text[:400] + "..."
            formatted_regs.append(f"{reg_id}:\n{reg_text}")
        
        regulations_text = "\n\n".join(formatted_regs)
        
        return f"""You are a GDPR compliance expert. Analyse this document section for violations.

DOCUMENT SECTION: {section}

DOCUMENT TEXT:
{text}

RELEVANT GDPR ARTICLES:
{regulations_text}

INSTRUCTIONS:
Find clear GDPR violations in the document text. Look for these common violation patterns:

CONSENT VIOLATIONS (Article 7):
- Forced consent: "must agree", "required to accept", "mandatory consent"
- Bundled consent: single checkbox for multiple purposes  
- Cannot withdraw: "cannot withdraw", "irrevocable consent"
- Pre-checked boxes, automatic opt-in

DATA RETENTION VIOLATIONS (Article 5(1)(e)):
- Indefinite storage: "indefinitely", "permanently", "forever", "retain all data"
- No deletion: "no deletion", "cannot delete", "no automatic deletion"
- Excessive retention periods

INDIVIDUAL RIGHTS VIOLATIONS (Articles 15-17):
- No access: "cannot access", "no access", "restricted access"  
- Delayed responses: mention of periods over 30 days
- No rights information provided

UNLAWFUL PROCESSING (Article 6):
- No legal basis mentioned for data processing
- Sharing without proper basis: "sell data", "share with third parties"
- Comprehensive collection without justification

SECURITY VIOLATIONS (Article 32):
- Inadequate security: "basic security", "minimal protection"
- No encryption: "no encryption", "unencrypted" 
- Budget constraints limiting security

TRANSPARENCY VIOLATIONS (Article 5(1)(a)):
- Hidden sharing: arrangements "not explicitly highlighted"
- Unclear purposes or processing details

RESPONSE FORMAT:
Respond ONLY in this JSON format with no additional text:

{{
    "violations": [
        {{
            "issue": "Description of the GDPR violation found",
            "regulation": "GDPR Article reference (e.g., Article 5(1)(e))",
            "quote": "Relevant text from document showing the issue"
        }}
    ]
}}

GUIDELINES:
- Focus on finding real violations rather than perfect quotes
- Use the most relevant GDPR article from the list above
- Quote should be representative of the issue (doesn't need to be perfect)
- If you find violations, include them even if quotes aren't exact word-for-word
- Only skip violations if you're genuinely unsure they violate GDPR

If no violations found: {{"violations": []}}

Remember: Response must start with {{ and end with }}. No other text."""