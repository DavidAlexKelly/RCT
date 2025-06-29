# knowledge_base/gdpr/handler.py

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from utils.regulation_handler_base import RegulationHandlerBase

class RegulationHandler(RegulationHandlerBase):
    """GDPR handler - loads from required YAML files."""
    
    def __init__(self, debug=False):
        super().__init__(debug)
        self.framework_dir = Path(__file__).parent
        
        # Load required files
        with open(self.framework_dir / "classification.yaml", 'r') as f:
            self.classification = yaml.safe_load(f)
        
        with open(self.framework_dir / "context.yaml", 'r') as f:
            self.context = yaml.safe_load(f)
    
    def get_classification_terms(self, term_type: str) -> List[str]:
        """Get classification terms for progressive analysis."""
        return self.classification.get(term_type, [])
    
    def get_violation_patterns(self) -> List[Dict[str, Any]]:
        """Get violation patterns for pre-scanning."""
        return self.classification.get('violation_patterns', [])
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str,
                              content_indicators: Optional[Dict[str, str]] = None,
                              potential_violations: Optional[List[Dict[str, Any]]] = None,
                              regulation_framework: str = "gdpr",
                              risk_level: str = "unknown") -> str:
        """Create GDPR-specific analysis prompt."""
        
        risk_guidance = ""
        if risk_level == "high":
            risk_guidance = "IMPORTANT: This section is HIGH RISK. Be thorough in finding violations."
        elif risk_level == "low":
            risk_guidance = "IMPORTANT: This section is LOW RISK. Only flag clear, obvious violations."
        
        return f"""Find GDPR violations in this document section.

DOCUMENT SECTION: {section}
DOCUMENT TEXT:
{text}

RELEVANT GDPR ARTICLES:
{regulations}

{risk_guidance}

TASK: Find statements that clearly violate GDPR requirements.

IGNORE these (NOT violations):
    - "We implement [security measure]" 
    - "Users can [delete/access] their data"
    - "We obtain consent"

ONLY FLAG these (actual violations):
    - "Data stored indefinitely without purpose"
    - "No consent required" 
    - "Users cannot delete data"

RESPONSE FORMAT - Return ONLY a JSON array:
[
["Clear violation description", "Article X", "Exact quote showing violation"],
["Another violation", "Article Y", "Another exact quote"]
]

RULES:
- Only flag BAD practices
- Use exact quotes from document
- If no clear violations found, return: []
"""