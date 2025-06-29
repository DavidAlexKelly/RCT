# knowledge_base/gdpr/handler.py

import re
import json
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from utils.regulation_handler_base import RegulationHandlerBase

class RegulationHandler(RegulationHandlerBase):
    """GDPR-specific handler implementing standardized interface."""
    
    def __init__(self, debug=False):
        """Initialize the GDPR handler."""
        super().__init__(debug)
        self.framework = "gdpr"
        self.classification_data = None
        self.context_data = None
        self._load_framework_data()
    
    def _load_framework_data(self):
        """Load classification and context data for this framework."""
        try:
            # Get the framework directory
            handler_path = Path(__file__).parent
            
            # Load classification data
            classification_path = handler_path / "classification.yaml"
            if classification_path.exists():
                with open(classification_path, 'r', encoding='utf-8') as f:
                    self.classification_data = yaml.safe_load(f)
            
            # Load context data
            context_path = handler_path / "context.yaml"
            if context_path.exists():
                with open(context_path, 'r', encoding='utf-8') as f:
                    self.context_data = yaml.safe_load(f)
                    
            if self.debug:
                print(f"Loaded GDPR framework data: classification={self.classification_data is not None}, context={self.context_data is not None}")
                
        except Exception as e:
            if self.debug:
                print(f"Error loading GDPR framework data: {e}")
            self.classification_data = {}
            self.context_data = {}
    
    def get_classification_terms(self, term_type: str) -> List[str]:
        """Get classification terms for progressive analysis."""
        if not self.classification_data:
            return []
        return self.classification_data.get(term_type, [])
    
    def get_violation_patterns(self) -> List[Dict[str, Any]]:
        """Get violation patterns for pre-scanning."""
        if not self.classification_data:
            return []
        return self.classification_data.get('violation_patterns', [])
    
    def validate_framework_data(self) -> Dict[str, Any]:
        """Validate that all required framework data is present."""
        validation = {
            "framework": self.framework,
            "valid": True,
            "missing_files": [],
            "missing_fields": [],
            "warnings": []
        }
        
        # Check required files
        handler_path = Path(__file__).parent
        required_files = ["articles.txt", "classification.yaml", "context.yaml"]
        
        for filename in required_files:
            if not (handler_path / filename).exists():
                validation["missing_files"].append(filename)
                validation["valid"] = False
        
        # Check required fields in classification.yaml
        if self.classification_data:
            required_classification_fields = [
                "data_terms", "regulatory_keywords", "high_risk_patterns", 
                "priority_keywords", "violation_patterns"
            ]
            for field in required_classification_fields:
                if field not in self.classification_data:
                    validation["missing_fields"].append(f"classification.yaml:{field}")
                    validation["valid"] = False
        
        # Check required fields in context.yaml
        if self.context_data:
            required_context_fields = ["framework", "name", "key_principles", "data_subject_rights"]
            for field in required_context_fields:
                if field not in self.context_data:
                    validation["missing_fields"].append(f"context.yaml:{field}")
                    validation["warnings"].append(f"Missing context field: {field}")
        
        return validation
    
    def extract_content_indicators(self, text: str) -> Dict[str, str]:
        """Extract GDPR-specific content indicators from text."""
        indicators = {}
        
        # Use loaded terms if available, otherwise fallback to hardcoded
        data_terms = self.get_classification_terms("data_terms")
        if not data_terms:
            data_terms = ["personal data", "data subject", "information", "email", "profile"]
        
        regulatory_terms = self.get_classification_terms("regulatory_keywords") 
        if not regulatory_terms:
            regulatory_terms = ["gdpr", "privacy", "consent", "rights", "compliance"]
        
        # Check for various indicators
        indicators["has_personal_data"] = "Yes" if any(
            re.search(rf'\b{re.escape(term)}\b', text, re.I) for term in data_terms[:10]
        ) else "No"
        
        indicators["has_data_collection"] = "Yes" if re.search(
            r'\b(collect|gather|obtain|capture|record|store)\b', text, re.I
        ) else "No"
        
        indicators["has_data_sharing"] = "Yes" if re.search(
            r'\b(share|transfer|disclose|send|provide|third party)\b', text, re.I
        ) else "No"
        
        indicators["has_retention"] = "Yes" if re.search(
            r'\b(retain|store|keep|save|archive|delete|period)\b', text, re.I
        ) else "No"
        
        indicators["has_consent"] = "Yes" if re.search(
            r'\b(consent|agree|accept|approve|opt-in|opt-out)\b', text, re.I
        ) else "No"
        
        indicators["has_rights"] = "Yes" if re.search(
            r'\b(right|access|rectification|erasure|restriction|portability|object)\b', text, re.I
        ) else "No"
        
        indicators["has_automated"] = "Yes" if re.search(
            r'\b(automated|automatic|algorithm|profiling|AI|machine learning)\b', text, re.I
        ) else "No"
        
        indicators["has_sensitive"] = "Yes" if re.search(
            r'\b(sensitive|biometric|health|race|political|religion)\b', text, re.I
        ) else "No"
        
        return indicators
    
    def extract_potential_violations(self, text: str, patterns_text: str = "") -> List[Dict[str, Any]]:
        """Extract potential GDPR violations using loaded patterns."""
        violations = []
        
        # Use loaded violation patterns
        violation_patterns = self.get_violation_patterns()
        
        for pattern_data in violation_patterns:
            pattern_name = pattern_data.get("pattern", "")
            description = pattern_data.get("description", "")
            indicators = pattern_data.get("indicators", [])
            related_articles = pattern_data.get("related_articles", [])
            
            # Check text for these indicators
            for indicator in indicators:
                if indicator.lower() in text.lower():
                    # Find context around the match
                    match_idx = text.lower().find(indicator.lower())
                    start_context = max(0, match_idx - 50)
                    end_context = min(len(text), match_idx + len(indicator) + 50)
                    context = text[start_context:end_context]
                    
                    violations.append({
                        "pattern": pattern_name,
                        "description": description,
                        "indicator": indicator,
                        "context": context,
                        "related_refs": related_articles
                    })
        
        return violations
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str,
                              content_indicators: Optional[Dict[str, str]] = None,
                              potential_violations: Optional[List[Dict[str, Any]]] = None,
                              regulation_framework: str = "gdpr",
                              risk_level: str = "unknown") -> str:
        """Create GDPR-specific analysis prompt focusing only on violations."""
        
        # Format content indicators
        content_indicators_text = ""
        if content_indicators:
            content_indicators_text = "\n".join([
                f"- Contains {k.replace('has_', '')} references: {v}"
                for k, v in content_indicators.items()
            ])
        
        # Format potential violations if available
        potential_violations_text = ""
        if potential_violations:
            potential_violations_text = "PRE-SCAN DETECTED POTENTIAL VIOLATIONS:\n"
            for i, violation in enumerate(potential_violations[:3]):  # Limit to top 3
                potential_violations_text += f"{i+1}. {violation['pattern']}: {violation['indicator']}\n"
        
        # Adjust analysis based on risk level
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

CONTENT INDICATORS:
{content_indicators_text}

{potential_violations_text}

TASK: Find statements that clearly violate GDPR requirements.

IGNORE these types of statements (they are NOT violations):
    - "We implement [security measure]" 
    - "The system provides [user right]"
    - "Data is [protected/encrypted/minimized]"
    - "Users can [delete/access/export] their data"
    - "We obtain [consent/permission]"
    - "Privacy notices are provided"

ONLY FLAG these types of statements (actual violations):
    - "Data is stored indefinitely without purpose"
    - "No consent is required" 
    - "Users cannot delete their data"
    - "No security measures are used"
    - "We don't provide privacy information"
    - "Data is shared without user knowledge"

EXAMPLES:
    ❌ VIOLATION: "Customer data will be retained indefinitely for business value"
    ✅ NOT A VIOLATION: "Data retention policies limit storage to necessary periods"

RESPONSE FORMAT - Return ONLY a JSON array:
[
["Clear violation description", "Article X", "Exact quote showing the violation"],
["Another violation", "Article Y", "Another exact quote"]
]

RULES:
- Only flag statements that describe BAD practices or clear violations
- Ignore all statements that describe GOOD practices or compliance measures
- Use exact quotes from the document
- If unsure whether something is a violation, don't include it
- If no clear violations found, return: []
"""
    
    def format_regulations(self, regulations: List[Dict[str, Any]], 
                         regulation_context: str = "",
                         regulation_patterns: str = "") -> str:
        """Format GDPR regulations with context for inclusion in prompts."""
        formatted_regs = []
        
        # Add context from loaded data if available
        if self.context_data:
            context_summary = f"GDPR Context: {self.context_data.get('description', '')}"
            
            # Add key principles
            principles = self.context_data.get('key_principles', [])
            if principles:
                context_summary += "\nKey Principles: " + ", ".join([
                    p.get('principle', '') for p in principles[:3]
                ])
            
            formatted_regs.append(context_summary)
        
        # Add specific regulation articles
        for i, reg in enumerate(regulations):
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", f"Article {i+1}")
            
            # Truncate long regulation text for better prompt efficiency
            if len(reg_text) > 400:
                reg_text = reg_text[:400] + "..."
            
            formatted_reg = f"{reg_id}:\n{reg_text}"
            formatted_regs.append(formatted_reg)
        
        return "\n\n".join(formatted_regs)