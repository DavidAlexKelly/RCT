# knowledge_base/gdpr/handler.py

import re

class RegulationHandler:
    """GDPR-specific implementation of regulation handler functions."""
    
    def __init__(self, debug=False):
        """Initialize the GDPR handler."""
        self.debug = debug
    
    def extract_content_indicators(self, text):
        """Extract GDPR-specific content indicators from text."""
        indicators = {
            "has_personal_data": "Yes" if re.search(r'\b(personal data|email|name|address|phone|profile)\b', text, re.I) else "No",
            "has_data_collection": "Yes" if re.search(r'\b(collect|gather|obtain|capture|record)\b', text, re.I) else "No",
            "has_data_sharing": "Yes" if re.search(r'\b(share|transfer|disclose|send|provide|third party)\b', text, re.I) else "No",
            "has_retention": "Yes" if re.search(r'\b(retain|store|keep|save|archive|delete|period)\b', text, re.I) else "No",
            "has_consent": "Yes" if re.search(r'\b(consent|agree|accept|approve|opt-in|opt-out)\b', text, re.I) else "No",
            "has_rights": "Yes" if re.search(r'\b(right|access|rectification|erasure|restriction|portability|object)\b', text, re.I) else "No",
            "has_automated": "Yes" if re.search(r'\b(automated|automatic|algorithm|profiling|AI|machine learning)\b', text, re.I) else "No",
            "has_sensitive": "Yes" if re.search(r'\b(sensitive|genetic|biometric|health|race|political|religion|union|orientation)\b', text, re.I) else "No"
        }
        return indicators
    
    def extract_potential_violations(self, text, patterns_text):
        """Extract GDPR-specific violation patterns from text."""
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
            related_articles = []
            
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
                elif line.startswith("Related Articles:"):
                    article_text = line.replace("Related Articles:", "").strip()
                    related_articles = [a.strip() for a in article_text.split(',')]
            
            # Check text for these indicators
            if pattern_name and indicators:
                for indicator in indicators:
                    if indicator.lower() in text.lower():
                        # Find the actual match context
                        match_idx = text.lower().find(indicator.lower())
                        start_context = max(0, match_idx - 50)
                        end_context = min(len(text), match_idx + len(indicator) + 50)
                        context = text[start_context:end_context]
                        
                        potential_violations.append({
                            "pattern": pattern_name,
                            "description": pattern_description,
                            "indicator": indicator,
                            "context": context,
                            "related_refs": related_articles
                        })
        
        return potential_violations
    
    # knowledge_base/gdpr/handler.py (continued)

    def extract_structured_issues(self, text):
        """Extract GDPR-specific structured issues from text."""
        issues = []
        
        # Look for GDPR-specific patterns
        gdpr_pattern = re.compile(r'(?:Issue\s*\d*|Finding\s*\d*):\s*(.*?)(?:\n|$).*?Article:\s*(.*?)(?:\n|$).*?Confidence:\s*(.*?)(?:\n|$).*?Explanation:\s*(.*?)(?:\n|$)', re.DOTALL)
        
        # Look for citations
        citation_pattern = re.compile(r'(?:Issue\s*\d*|Finding\s*\d*):\s*(.*?)(?:\n|$).*?Article:\s*(.*?)(?:\n|$).*?Confidence:\s*(.*?)(?:\n|$).*?Explanation:\s*(.*?)(?:\n|$).*?Citation:\s*"(.*?)"', re.DOTALL)
        
        # Try the citation pattern first
        citation_matches = citation_pattern.finditer(text)
        for match in citation_matches:
            issue = {
                "issue": match.group(1).strip(),
                "regulation": match.group(2).strip(),
                "confidence": match.group(3).strip(),
                "explanation": match.group(4).strip(),
                "citation": match.group(5).strip()
            }
            issues.append(issue)
        
        # If no citation matches, try the regular pattern
        if not issues:
            matches = gdpr_pattern.finditer(text)
            for match in matches:
                issue = {
                    "issue": match.group(1).strip(),
                    "regulation": match.group(2).strip(),
                    "confidence": match.group(3).strip(),
                    "explanation": match.group(4).strip()
                }
                issues.append(issue)
        
        # If still no matches, try a more relaxed pattern for GDPR
        if not issues:
            # Look for patterns like "1. Description - Article 5(1)(e) - High"
            simple_pattern = re.compile(r'(?:\d+\.\s*)(.*?)(?:\s*-\s*)(Article\s*\d+(?:\(\d+\))*(?:\([a-z]\))*)(?:\s*-\s*)(High|Medium|Low)(?:\s*-\s*)(.*?)(?:\n\n|\n\d+\.|\Z)', re.DOTALL)
            matches = simple_pattern.finditer(text)
            for match in matches:
                issue = {
                    "issue": match.group(1).strip(),
                    "regulation": match.group(2).strip(),
                    "confidence": match.group(3).strip(),
                    "explanation": match.group(4).strip()
                }
                issues.append(issue)
        
        return issues
    
    def create_analysis_prompt(self, text, section, regulations, content_indicators, potential_violations, regulation_framework):
        """Create a GDPR-specific prompt for compliance analysis."""
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
            potential_violations_text = "PRE-SCAN DETECTED POTENTIAL GDPR VIOLATIONS:\n"
            for i, violation in enumerate(potential_violations[:5]):  # Limit to top 5
                potential_violations_text += f"{i+1}. Potential '{violation['pattern']}' pattern detected\n"
                if violation.get('description'):
                    potential_violations_text += f"   Description: {violation['description']}\n"
                potential_violations_text += f"   Indicator: '{violation['indicator']}'\n"
                potential_violations_text += f"   Context: \"...{violation['context']}...\"\n"
                if violation.get('related_refs'):
                    potential_violations_text += f"   Related articles: {', '.join(violation['related_refs'])}\n"
                potential_violations_text += "\n"
        
        # Use GDPR-specific prompt if available
        from config.prompts import get_prompt_for_regulation
        prompt_template = get_prompt_for_regulation("gdpr", "analyze_compliance")
        
        if prompt_template:
            # Format using the GDPR template
            prompt = prompt_template.format(
                section=section,
                text=text,
                regulations=regulations,
                has_personal_data=content_indicators.get("has_personal_data", "No"),
                has_data_collection=content_indicators.get("has_data_collection", "No"),
                has_data_sharing=content_indicators.get("has_data_sharing", "No"),
                has_retention=content_indicators.get("has_retention", "No"),
                has_consent=content_indicators.get("has_consent", "No"),
                has_rights=content_indicators.get("has_rights", "No"),
                has_automated=content_indicators.get("has_automated", "No"),
                has_sensitive=content_indicators.get("has_sensitive", "No")
            )
            
            # Add potential violations if available
            if potential_violations:
                # Insert before Analysis Guidelines
                guidelines_pos = prompt.find("ANALYSIS GUIDELINES")
                if guidelines_pos > 0:
                    prompt = prompt[:guidelines_pos] + potential_violations_text + "\n" + prompt[guidelines_pos:]
                else:
                    # Add at the end if Analysis Guidelines not found
                    prompt += "\n\n" + potential_violations_text
        else:
            # Create a custom GDPR prompt
            prompt = f"""You are a GDPR compliance auditor with expertise in identifying non-compliant practices. Analyze this section for compliance with European data protection regulations.

SECTION: {section}
TEXT:
{text}

APPLICABLE REGULATIONS:
{regulations}

CONTENT INDICATORS:
{content_indicators_text}

{potential_violations_text}

ANALYSIS GUIDELINES:
1. Focus on GDPR core principles: lawfulness, fairness, transparency, purpose limitation, data minimization, accuracy, storage limitation, integrity, confidentiality, and accountability
2. Identify issues related to consent mechanisms (must be freely given, specific, informed, unambiguous)
3. Check for proper implementation of data subject rights (access, rectification, erasure, etc.)
4. Look for proper security measures and data protection safeguards
5. Evaluate data retention policies against necessity principle
6. Identify any processing of special categories of data without appropriate safeguards

Return your findings as JSON with this format:
{{
  "issues": [
    {{
      "issue": "Description of the compliance issue",
      "regulation": "Article reference (e.g., 'Article 5(1)(e)')",
      "confidence": "High/Medium/Low",
      "explanation": "Why this violates the regulation",
      "citation": "Direct quote from text showing the violation"
    }}
  ],
  "topic_tags": ["data_retention", "consent", "data_sharing", "etc"]
}}

If no issues are found, return an empty issues array: {{ "issues": [] }}
"""
        
        return prompt
    
    def format_regulations(self, regulations, regulation_context, regulation_patterns):
        """Format regulations for GDPR-specific prompt."""
        formatted_regs = []
        
        # Add GDPR context if available
        if regulation_context:
            formatted_regs.append(f"GDPR CONTEXT:\n{regulation_context}")
        
        # Add common patterns if available (brief summary)
        if regulation_patterns:
            pattern_count = regulation_patterns.count("Pattern:")
            if pattern_count > 0:
                formatted_regs.append(f"GDPR VIOLATION PATTERNS: {pattern_count} patterns available")
        
        # Add specific regulations
        for i, reg in enumerate(regulations):
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", f"Article {i+1}")
            reg_title = reg.get("title", "")
            related_concepts = reg.get("related_concepts", [])
            
            # Include regulation ID and title if available
            formatted_reg = f"ARTICLE {i+1}: {reg_id}"
            if reg_title:
                formatted_reg += f" - {reg_title}"
                
            if related_concepts:
                formatted_reg += f"\nRELATED CONCEPTS: {', '.join(related_concepts)}"
                
            formatted_reg += f"\n{reg_text}"
            
            formatted_regs.append(formatted_reg)
            
        return "\n\n".join(formatted_regs)