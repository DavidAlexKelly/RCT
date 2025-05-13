# knowledge_base/[regulation_framework]/handler.py

import re
from typing import Dict, Any, List, Optional
from utils.regulation_handler_base import RegulationHandlerBase

class RegulationHandler(RegulationHandlerBase):
    """Regulation-specific implementation of handler functions."""
    
    def __init__(self, debug=False):
        """Initialize the regulation handler."""
        super().__init__(debug)
    
    def extract_content_indicators(self, text: str) -> Dict[str, str]:
        """Extract content indicators from text."""
        indicators = {
            "has_personal_data": "Yes" if re.search(r'\b(personal data|information|email|name|address|phone|profile)\b', text, re.I) else "No",
            "has_data_collection": "Yes" if re.search(r'\b(collect|gather|obtain|capture|record)\b', text, re.I) else "No",
            "has_data_sharing": "Yes" if re.search(r'\b(share|transfer|disclose|send|provide|third party)\b', text, re.I) else "No",
            "has_retention": "Yes" if re.search(r'\b(retain|store|keep|save|archive|delete|period)\b', text, re.I) else "No",
            "has_consent": "Yes" if re.search(r'\b(consent|agree|accept|approve|opt-in|opt-out)\b', text, re.I) else "No",
            "has_rights": "Yes" if re.search(r'\b(right|access|rectification|erasure|restriction|portability|object)\b', text, re.I) else "No",
            "has_automated": "Yes" if re.search(r'\b(automated|automatic|algorithm|profiling|AI|machine learning)\b', text, re.I) else "No",
            "has_sensitive": "Yes" if re.search(r'\b(sensitive|biometric|health|race|political|religion)\b', text, re.I) else "No"
        }
        return indicators
    
    def extract_potential_violations(self, text: str, patterns_text: str) -> List[Dict[str, Any]]:
        """Extract potential violation patterns from text."""
        if not patterns_text:
            return []
        
        potential_violations = []
        
        # Parse the patterns file to extract indicators
        pattern_blocks = patterns_text.split('\n\n')
        for block in pattern_blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:  # Need Pattern, Description, and Indicators
                continue
                
            pattern_name = None
            pattern_description = None
            indicators = []
            related_refs = []
            
            for line in lines:
                if line.startswith("Pattern:"):
                    pattern_name = line.replace("Pattern:", "").strip()
                elif line.startswith("Description:"):
                    pattern_description = line.replace("Description:", "").strip()
                elif line.startswith("Indicators:"):
                    indicator_text = line.replace("Indicators:", "").strip()
                    # Extract quoted phrases or comma-separated items
                    if '"' in indicator_text:
                        # Extract quoted phrases
                        quoted_indicators = re.findall(r'"([^"]*)"', indicator_text)
                        indicators.extend(quoted_indicators)
                    else:
                        # Split by commas
                        comma_indicators = [i.strip() for i in indicator_text.split(',')]
                        indicators.extend(comma_indicators)
                elif line.startswith("Related"):
                    refs_text = line.split(":", 1)[1].strip() if ":" in line else ""
                    related_refs = [r.strip() for r in refs_text.split(",")]
            
            # Check text for these indicators
            if pattern_name and indicators:
                for indicator in indicators:
                    indicator_lower = indicator.lower()
                    text_lower = text.lower()
                    if indicator_lower in text_lower:
                        # Find the actual match context
                        match_idx = text_lower.find(indicator_lower)
                        start_context = max(0, match_idx - 50)
                        end_context = min(len(text), match_idx + len(indicator) + 50)
                        context = text[start_context:end_context]
                        
                        potential_violations.append({
                            "pattern": pattern_name,
                            "description": pattern_description,
                            "indicator": indicator,
                            "context": context,
                            "related_refs": related_refs
                        })
        
        return potential_violations
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str,
                              content_indicators: Optional[Dict[str, str]] = None,
                              potential_violations: Optional[List[Dict[str, Any]]] = None,
                              regulation_framework: str = "",
                              risk_level: str = "unknown") -> str:
        """Create a regulation-specific prompt for analysis."""
        if content_indicators is None:
            content_indicators = {}
                
        # Format content indicators
        content_indicators_text = "\n".join([
            f"- Contains {k.replace('has_', '')} references: {v}"
            for k, v in content_indicators.items()
        ])
            
        # Format potential violations if available
        potential_violations_text = ""
        if potential_violations:
            potential_violations_text = "PRE-SCAN DETECTED POTENTIAL VIOLATIONS:\n"
            for i, violation in enumerate(potential_violations[:5]):  # Limit to top 5
                potential_violations_text += f"{i+1}. Potential '{violation['pattern']}' pattern detected\n"
                if violation.get('description'):
                    potential_violations_text += f"   Description: {violation['description']}\n"
                potential_violations_text += f"   Indicator: '{violation['indicator']}'\n"
                potential_violations_text += f"   Context: \"...{violation['context']}...\"\n"
                if violation.get('related_refs'):
                    potential_violations_text += f"   Related references: {', '.join(violation['related_refs'])}\n"
                potential_violations_text += "\n"
            
        # Adjust analysis depth based on risk level
        risk_guidance = ""
        if risk_level == "high":
            risk_guidance = """IMPORTANT: This section has been identified as HIGH RISK. 
    Be thorough in your analysis and identify all potential compliance issues. 
    Look carefully for any violations, even subtle ones.
    """
        elif risk_level == "medium":
            risk_guidance = """IMPORTANT: This section has been identified as MEDIUM RISK.
    Focus on the most significant compliance issues and be reasonably thorough in your analysis.
    """
        elif risk_level == "low":
            risk_guidance = """IMPORTANT: This section has been identified as LOW RISK.
    Be conservative in flagging issues - only note clear, obvious violations.
    Focus on ensuring there are no major compliance gaps.
    """
    
        # Create the prompt
        analysis_prompt = f"""You are an expert compliance auditor. Your task is to analyze this text section for compliance issues and points.

SECTION: {section}
TEXT:
{text}

RELEVANT REGULATIONS:
{regulations}

RISK LEVEL: {risk_level.upper()}

{risk_guidance}

CONTENT INDICATORS:
{content_indicators_text}

{potential_violations_text if potential_violations else ""}

INSTRUCTIONS:
1. Analyze this section for clear compliance issues based on the regulations provided.
2. For each issue, include a direct quote from the document text.
3. Format your response EXACTLY as shown in the example below.
4. DO NOT format issues as "Issue:", "Regulation:", etc. Just follow the example format.
5. DO NOT include placeholders like "See document text" - always use an actual quote from the text.
6. Focus on clear violations rather than small technical details.

EXAMPLE REQUIRED FORMAT:
COMPLIANCE ISSUES:

The document states it will retain data indefinitely, violating storage limitation principles. "Retain all customer data indefinitely for long-term trend analysis."
Users cannot refuse data collection, violating consent requirements. "Users will be required to accept all data collection to use the app."

COMPLIANCE POINTS:

The document provides clear user notification about data usage. "Our implementation will use a simple banner stating 'By using this site, you accept our terms'."


If no issues are found, write "NO COMPLIANCE ISSUES DETECTED."
If no compliance points are found, write "NO COMPLIANCE POINTS DETECTED."
"""
    
        return analysis_prompt
    
    def format_regulations(self, regulations: List[Dict[str, Any]], 
                         regulation_context: str = "",
                         regulation_patterns: str = "") -> str:
        """Format regulations for inclusion in a prompt."""
        try:
            formatted_regs = []
            
            # Add regulation context if available
            if regulation_context:
                formatted_regs.append(f"REGULATION CONTEXT:\n{regulation_context}")
            
            # Add common patterns if available (brief summary)
            if regulation_patterns:
                pattern_count = regulation_patterns.count("Pattern:")
                if pattern_count > 0:
                    formatted_regs.append(f"VIOLATION PATTERNS: {pattern_count} patterns available")
            
            # Add specific regulations with more context
            for i, reg in enumerate(regulations):
                reg_text = reg.get("text", "")
                reg_id = reg.get("id", f"Regulation {i+1}")
                reg_title = reg.get("title", "")
                related_concepts = reg.get("related_concepts", [])
                
                # Include regulation ID and title if available
                formatted_reg = f"REGULATION {i+1}: {reg_id}"
                if reg_title:
                    formatted_reg += f" - {reg_title}"
                    
                if related_concepts:
                    formatted_reg += f"\nRELATED CONCEPTS: {', '.join(related_concepts)}"
                    
                formatted_reg += f"\n{reg_text}"
                
                formatted_regs.append(formatted_reg)
                
            return "\n\n".join(formatted_regs)
            
        except Exception as e:
            print(f"Error in handler's format_regulations: {e}")
            # Provide a basic fallback format
            return "\n\n".join([f"Regulation: {reg.get('id', 'Unknown')}\n{reg.get('text', '')}" for reg in regulations])