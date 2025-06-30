import yaml
from typing import Dict, Any, List
from pathlib import Path
import sys

# Import base handler
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.regulation_handler_base import RegulationHandlerBase

class RegulationHandler(RegulationHandlerBase):
    """HIPAA specialist with balanced detection and validation."""
    
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
            "business associate": "§164.314",
            "baa": "§164.314",
            "safeguards": "§164.308",
            "administrative safeguards": "§164.308",
            "physical safeguards": "§164.310",
            "technical safeguards": "§164.312",
            "encryption": "§164.312",
            "security": "§164.308",
            "breach notification": "§164.404",
            "60 days": "§164.404",
            "90 days": "§164.404",
            "privacy officer": "§164.530",
            "security officer": "§164.530",
            "training": "§164.308",
            "phi": "§164.502",
            "minimum necessary": "§164.502",
            "marketing": "§164.508",
            "research": "§164.508"
        }
        
        for keyword, regulation in patterns.items():
            if keyword in issue_lower:
                return regulation
        
        return "Relevant HIPAA Section"  # HIPAA-specific fallback
    
    def create_prompt(self, text: str, section: str, regulations: List[Dict[str, Any]]) -> str:
        """Create HIPAA-specific analysis prompt with balanced requirements."""
        
        # Format regulations for prompt
        formatted_regs = []
        for reg in regulations:
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", "Unknown")
            if len(reg_text) > 400:
                reg_text = reg_text[:400] + "..."
            formatted_regs.append(f"{reg_id}:\n{reg_text}")
        
        regulations_text = "\n\n".join(formatted_regs)
        
        return f"""You are a HIPAA compliance expert. Analyse this document section for violations.

DOCUMENT SECTION: {section}

DOCUMENT TEXT:
{text}

RELEVANT HIPAA SECTIONS:
{regulations_text}

INSTRUCTIONS:
Find clear HIPAA violations in the document text. Look for these common violation patterns:

PHI AUTHORIZATION VIOLATIONS (§164.508):
- Sharing without authorization: "without authorization", "no authorization required"
- Automatic sharing: "automatic sharing", "share with anyone"
- Unauthorized access: "unlimited access", "vendor access"

BUSINESS ASSOCIATE VIOLATIONS (§164.314):
- No BAA: "no business associate agreement", "contractor access"
- Third party access without proper agreements
- Outsourcing without contracts

SAFEGUARDS VIOLATIONS:
- Administrative (§164.308): "no training", "untrained staff", "no privacy officer"
- Physical (§164.310): "disposed in trash", "thrown away", poor physical controls
- Technical (§164.312): "no encryption", "unencrypted PHI", "plain text", "weak passwords"

BREACH NOTIFICATION VIOLATIONS (§164.404):
- Delayed notification: periods over 60 days ("90 days" for HIPAA)
- No notification: "no breach notification", "hidden breach" 
- Unreported incidents: "not reported"

MISSING REQUIRED ROLES (§164.530):
- No privacy officer, no security officer
- No designated compliance roles

IMPROPER PHI USE (§164.502):
- Marketing without authorization: "marketing use", "sell patient data"
- Research without consent: "research without authorization"
- Minimum necessary not followed

RESPONSE FORMAT:
Respond ONLY in this JSON format with no additional text:

{{
    "violations": [
        {{
            "issue": "Description of the HIPAA violation found",
            "regulation": "HIPAA Section reference (e.g., §164.502)",
            "quote": "Relevant text from document showing the issue"
        }}
    ]
}}

GUIDELINES:
- Focus on finding real violations rather than perfect quotes
- Use the most relevant HIPAA section from the list above
- Quote should be representative of the issue (doesn't need to be perfect)
- If you find violations, include them even if quotes aren't exact word-for-word
- Only skip violations if you're genuinely unsure they violate HIPAA

If no violations found: {{"violations": []}}

Remember: Response must start with {{ and end with }}. No other text."""