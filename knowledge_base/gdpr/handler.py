# knowledge_base/gdpr/handler.py

import re
from typing import Dict, Any, List, Optional
from utils.regulation_handler_base import RegulationHandlerBase

class RegulationHandler(RegulationHandlerBase):
    """GDPR-specific implementation - simplified and focused."""
    
    def __init__(self, debug=False):
        """Initialize the GDPR handler."""
        super().__init__(debug)
    
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
        """Create GDPR-specific analysis prompt with better structure."""
        
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
        
        # IMPROVED GDPR-specific structured prompt
        return f"""You are an expert GDPR compliance auditor. Analyze this document section for GDPR violations and compliance strengths.

SECTION: {section}
TEXT:
{text}

GDPR REGULATIONS:
{regulations}

CONTENT ANALYSIS:
{indicators_text}

{violations_text}

TASK: Identify both GDPR compliance issues AND compliance strengths in this section.

CRITICAL FORMATTING REQUIREMENTS:
- Always reference specific GDPR Articles (e.g., "Article 5", "Article 13", "Article 32")
- Use concise, clear descriptions (under 50 words)
- Include only direct quotes from the document text
- Use exact numbering format shown below

REQUIRED FORMAT:
COMPLIANCE ISSUES:
1. [Concise issue description] violating [GDPR Article X]. "[Direct quote from document]"
2. [Another issue] violating [GDPR Article Y]. "[Direct quote]"

COMPLIANCE POINTS:
1. [Compliance strength] supporting [GDPR Article X]. "[Supporting quote]"

RULES:
- Use numbered lists starting with "1."
- Always include GDPR Article references (Article 5, Article 13, Article 32, etc.)
- Keep descriptions under 50 words
- Always include direct quotes from the document text in quotation marks
- Write "NO COMPLIANCE ISSUES DETECTED" if no violations found
- Write "NO COMPLIANCE POINTS DETECTED" if no strengths found
- Focus on clear, obvious violations only
- Do not repeat explanations or add redundant text

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