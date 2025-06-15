# knowledge_base/gdpr/handler.py

import re
from typing import Dict, Any, List, Optional
from utils.regulation_handler_base import RegulationHandlerBase

class RegulationHandler(RegulationHandlerBase):
    """GDPR-specific implementation with enhanced citation control."""
    
    def __init__(self, debug=False):
        """Initialize the GDPR handler."""
        super().__init__(debug)
    
    def _get_framework_regulation_phrases(self) -> List[str]:
        """Get GDPR-specific regulation phrases that should not appear in citations."""
        return [
            # GDPR-specific controller/data subject language
            "the controller shall", "data subject", "personal data shall",
            "processing shall be", "the data subject shall", "where personal data",
            "controller shall provide", "data subjects have the right",
            "personal data are", "processing of personal data",
            "lawfully, fairly and", "appropriate technical and",
            "without undue delay", "supervisory authority",
            
            # GDPR Article 13 specific phrases (the problematic ones we saw)
            "the period for which the personal data will be stored",
            "the criteria used to determine that period",
            "at the time when personal data are obtained",
            "the existence of the right to request",
            "the right to withdraw consent",
            "the right to lodge a complaint",
            "access to and rectification or erasure",
            "restriction of processing concerning",
            
            # GDPR procedural language
            "when entrusting a processor with processing activities",
            "providing sufficient guarantees",
            "implement appropriate technical and organisational measures",
            "ensure a level of security appropriate to the risk"
        ]
    
    def _validate_citation_framework_specific(self, citation: str, document_text: str) -> bool:
        """GDPR-specific citation validation."""
        citation_lower = citation.lower()
        
        # Additional GDPR-specific checks
        gdpr_red_flags = [
            "controller",
            "data subject", 
            "supervisory authority",
            "member state",
            "union law"
        ]
        
        # If citation contains multiple GDPR red flags, it's likely regulation text
        red_flag_count = sum(1 for flag in gdpr_red_flags if flag in citation_lower)
        if red_flag_count >= 2:
            if self.debug:
                print(f"Rejected citation (multiple GDPR red flags): {red_flag_count} flags in '{citation[:50]}...'")
            return False
        
        return True
       
    def _get_framework_business_indicators(self) -> List[str]:
        """Get GDPR/privacy domain-specific business terms."""
        # Start with base generic terms
        base_terms = super()._get_framework_business_indicators()
        
        # Add privacy/data domain-specific terms
        privacy_terms = [
            # Data processing terms
            "data", "information", "user", "customer", "profile", "record",
            "collect", "store", "process", "analyze", "track", "monitor",
            
            # Technology terms common in privacy contexts
            "database", "system", "platform", "app", "website", "API", "SDK",
            "algorithm", "analytics", "encryption", "security", "access",
            
            # Business terms in data/privacy context
            "project", "team", "develop", "implement", "company", "business",
            "revenue", "marketing", "product", "service", "feature",
            
            # Time/planning terms
            "month", "year", "budget", "timeline", "deployment", "launch"
        ]
        
        return base_terms + privacy_terms
    
    def extract_content_indicators(self, text: str) -> Dict[str, str]:
        """Extract GDPR-specific content indicators."""
        # Start with base indicators
        indicators = super().extract_content_indicators(text)
        
        # Add GDPR-specific indicators
        indicators.update({
            "has_sensitive": "Yes" if re.search(r'\b(sensitive|genetic|biometric|health|race|political|religion|union|orientation)\b', text, re.I) else "No"
        })
        
        return indicators
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str, 
                             content_indicators: Optional[Dict[str, str]] = None,
                             potential_violations: Optional[List[Dict[str, Any]]] = None,
                             regulation_framework: str = "gdpr",
                             risk_level: str = "unknown") -> str:
        """Create GDPR-specific analysis prompt with strict citation controls."""
        
        # Format content indicators
        indicators_text = ""
        if content_indicators:
            indicators_text = "\n".join([
                f"- Contains {k.replace('has_', '')} references: {v}"
                for k, v in content_indicators.items()
            ])
        
        # Format potential violations
        violations_text = ""
        if potential_violations:
            violations_text = "PRE-IDENTIFIED GDPR CONCERNS:\n"
            for i, violation in enumerate(potential_violations[:3]):  # Limit to top 3
                violations_text += f"{i+1}. {violation['pattern']}: '{violation['indicator']}'\n"
            violations_text += "\n"
        
        # ENHANCED prompt with strict citation rules
        return f"""You are an expert GDPR compliance auditor. Analyze this document section for GDPR violations and compliance strengths.

DOCUMENT SECTION: {section}
DOCUMENT TEXT TO ANALYZE:
{text}

GDPR REGULATIONS FOR REFERENCE:
{regulations}

CONTENT ANALYSIS:
{indicators_text}

{violations_text}

🚨 CRITICAL CITATION RULES 🚨
- CITATIONS MUST ONLY QUOTE FROM THE DOCUMENT TEXT ABOVE, NEVER FROM GDPR REGULATIONS
- DO NOT quote phrases like "the controller shall", "data subject", "personal data shall be"
- DO NOT quote "the period for which personal data will be stored" or similar GDPR article text
- DO NOT quote any regulation text - only quote the business document being analyzed
- Citations should sound like business/technical language, not legal language

TASK: Identify GDPR violations and compliance strengths in the DOCUMENT TEXT.

REQUIRED FORMAT:
COMPLIANCE ISSUES:
1. [Issue description] violating [GDPR Article]. "[Quote from DOCUMENT TEXT only]"
2. [Another issue] violating [GDPR Article]. "[Quote from DOCUMENT TEXT only]"

COMPLIANCE POINTS:
1. [Compliance strength] supporting [GDPR Article]. "[Quote from DOCUMENT TEXT only]"

CITATION EXAMPLES (what TO do - business document quotes):
✅ "User data retained indefinitely to maximize business value"
✅ "Rapid development will prioritize capabilities over compliance"
✅ "Basic encryption for the most sensitive data fields only"
✅ "No dedicated privacy or security specialists required"
✅ "Data will be collected for all current and potential future business purposes"

CITATION EXAMPLES (what NOT to do - GDPR regulation quotes):
❌ "The controller shall provide data subjects with information"
❌ "Personal data shall be processed lawfully"
❌ "The period for which the personal data will be stored"
❌ "The data subject shall have the right to access"
❌ "The controller shall implement appropriate measures"

RULES:
- Use numbered lists starting with "1."
- Always include GDPR Article references (Article 5, Article 13, Article 32, etc.)
- Keep descriptions under 50 words
- ONLY quote from the DOCUMENT TEXT, never from GDPR regulations
- Write "NO COMPLIANCE ISSUES DETECTED" if no violations found
- Write "NO COMPLIANCE POINTS DETECTED" if no strengths found
- Focus on clear, obvious violations only

"""
    
    def _extract_regulation_reference(self, text: str) -> str:
        """Extract GDPR article references specifically - IMPROVED VERSION."""
        
        # GDPR-specific patterns (more comprehensive)
        gdpr_patterns = [
            # Direct article references with various formats
            r'\bArticle\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)\b',
            r'\(Article\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)\)',
            # GDPR Article with specific formatting
            r'GDPR\s*Article\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)',
            # Article in violation context
            r'violating\s*(?:GDPR\s*)?Article\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)',
            r'Article\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)\s*(?:violation|requirement|principle)',
            # Supporting context
            r'supporting\s*(?:GDPR\s*)?Article\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)',
        ]
        
        # Try GDPR-specific patterns first
        for pattern in gdpr_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                article_num = match.group(1)
                return f"Article {article_num}"
        
        # Look for common GDPR articles by context/principles
        article_mapping = {
            # Article 5 principles
            r'\b(lawfulness|fairness|transparency)\b': "Article 5(1)(a)",
            r'\b(purpose\s+limitation)\b': "Article 5(1)(b)", 
            r'\b(data\s+minimization|minimisation)\b': "Article 5(1)(c)",
            r'\b(accuracy)\b.*\b(data|personal)\b': "Article 5(1)(d)",
            r'\b(storage\s+limitation|retention)\b': "Article 5(1)(e)",
            r'\b(integrity|confidentiality)\b.*\b(security|data)\b': "Article 5(1)(f)",
            r'\b(accountability)\b': "Article 5(2)",
            
            # Consent and rights
            r'\b(consent)\b.*\b(freely|specific|informed|unambiguous)\b': "Article 7",
            r'\b(withdraw.*consent|consent.*withdraw)\b': "Article 7(3)",
            r'\b(information.*provided.*data.*collected)\b': "Article 13",
            r'\b(transparency|transparent)\b.*\b(information|processing)\b': "Article 13",
            r'\b(right.*access)\b': "Article 15",
            r'\b(right.*rectification|rectification.*right)\b': "Article 16", 
            r'\b(right.*erasure|right.*forgotten|erasure.*right)\b': "Article 17",
            r'\b(right.*portability|portability.*right)\b': "Article 20",
            
            # Special processing
            r'\b(automated.*decision|profiling)\b.*\b(decision|individual)\b': "Article 22",
            r'\b(special.*categor|sensitive.*data)\b': "Article 9",
            
            # Security and organizational
            r'\b(security.*processing|processing.*security)\b': "Article 32",
            r'\b(data.*protection.*design|privacy.*design)\b': "Article 25",
            r'\b(breach.*notification|notification.*breach)\b': "Article 33",
            r'\b(impact.*assessment|assessment.*impact)\b': "Article 35",
            r'\b(data.*protection.*officer|dpo)\b': "Article 37",
        }
        
        text_lower = text.lower()
        for pattern, article in article_mapping.items():
            if re.search(pattern, text_lower):
                return article
        
        # Check for numbered violations that might indicate articles
        number_patterns = [
            r'violating.*?(\d+)',
            r'article.*?(\d+)',
            r'section.*?(\d+)',
        ]
        
        for pattern in number_patterns:
            match = re.search(pattern, text_lower)
            if match:
                num = match.group(1)
                # Only map to reasonable GDPR article numbers
                if num in ['5', '6', '7', '8', '9', '12', '13', '14', '15', '16', '17', '18', '20', '21', '22', '25', '32', '33', '35', '37']:
                    return f"Article {num}"
        
        # Fall back to parent class generic extraction
        parent_result = super()._extract_regulation_reference(text)
        
        # If parent class found something generic, try to convert to GDPR format
        if parent_result != "Unknown Regulation" and "Article" not in parent_result:
            # Extract numbers and convert to Article format
            numbers = re.findall(r'\d+', parent_result)
            if numbers:
                num = numbers[0]
                if num in ['5', '6', '7', '8', '9', '12', '13', '14', '15', '16', '17', '18', '20', '21', '22', '25', '32', '33', '35', '37']:
                    return f"Article {num}"
        
        # Smart fallback based on common violation types
        if any(term in text_lower for term in ['indefinite', 'storage', 'retention', 'delete']):
            return "Article 5(1)(e)"  # Storage limitation
        elif any(term in text_lower for term in ['consent', 'opt-in', 'opt-out', 'agree']):
            return "Article 7"  # Consent
        elif any(term in text_lower for term in ['security', 'encryption', 'protect']):
            return "Article 32"  # Security
        elif any(term in text_lower for term in ['transparent', 'information', 'notify']):
            return "Article 13"  # Transparency
        else:
            return "Article 5"  # General data protection principles
    
    def format_regulations(self, regulations: List[Dict[str, Any]], 
                         regulation_context: str = "", regulation_patterns: str = "") -> str:
        """Format regulations for GDPR-specific prompt with better context."""
        try:
            formatted_regs = []
            
            # Add GDPR context if available
            if regulation_context:
                formatted_regs.append(f"GDPR CONTEXT:\n{regulation_context}")
            
            # Add specific regulations with GDPR article emphasis
            for i, reg in enumerate(regulations):
                reg_text = reg.get("text", "")
                reg_id = reg.get("id", f"Article {i+1}")
                reg_title = reg.get("title", "")
                
                # Ensure GDPR article format
                if "Article" not in reg_id and re.match(r'^\d+', reg_id):
                    reg_id = f"Article {reg_id}"
                
                # Include regulation with clear GDPR formatting
                formatted_reg = f"GDPR {reg_id}"
                if reg_title:
                    formatted_reg += f" - {reg_title}"
                    
                formatted_reg += f"\n{reg_text}"
                
                formatted_regs.append(formatted_reg)
                
            return "\n\n".join(formatted_regs)
            
        except Exception as e:
            if self.debug:
                print(f"Error in GDPR handler's format_regulations: {e}")
            # Provide a basic fallback format
            return "\n\n".join([f"GDPR Article: {reg.get('id', 'Unknown')}\n{reg.get('text', '')}" for reg in regulations])