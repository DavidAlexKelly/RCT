# knowledge_base/gdpr/handler.py

import re
import json

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
    
    def create_analysis_prompt(self, text, section, regulations, content_indicators, potential_violations, regulation_framework="gdpr"):
        """Create a GDPR-specific prompt that identifies both compliance and violations."""
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
            
        # The simplified prompt
        analysis_prompt = f"""You are an expert GDPR compliance auditor. Your task is to analyze this text section for GDPR compliance issues and points.

SECTION: {section}
TEXT:
{text}

RELEVANT GDPR REGULATIONS:
{regulations}

CONTENT INDICATORS:
{content_indicators_text}

{potential_violations_text if potential_violations else ""}

INSTRUCTIONS:
1. Analyze this section for clear GDPR compliance issues.
2. For each issue, include a direct quote from the document text.
3. Format your response EXACTLY as shown in the example below.
4. DO NOT format issues as "Issue:", "Regulation:", etc. Just follow the example format.
5. DO NOT include placeholders like "See document text" - always use an actual quote from the text.
6. Focus on clear violations rather than small technical details.

EXAMPLE REQUIRED FORMAT:
```
COMPLIANCE ISSUES:
1. The document states it will retain data indefinitely, violating storage limitation principles (Article 5). "Retain all customer data indefinitely for long-term trend analysis."

2. Users cannot refuse consent for data collection, violating consent requirements (Article 7). "Users will be required to accept all data collection to use the app."

COMPLIANCE POINTS:
1. The document provides clear user notification about cookies, supporting transparency (Article 13). "Our cookie implementation will use a simple banner stating 'By using this site, you accept cookies'."
```

If no issues are found, write "NO COMPLIANCE ISSUES DETECTED."
If no compliance points are found, write "NO COMPLIANCE POINTS DETECTED."
"""
    
        return analysis_prompt
    
    def extract_structured_issues(self, analysis_response):
        """
        Process the LLM's analysis and ask it to structure both compliance issues and points.
        """
        from langchain_ollama import OllamaLLM as Ollama
        
        # Create the structuring prompt based on the initial analysis
        structuring_prompt = f"""Based on your previous GDPR compliance analysis:

{analysis_response}

Please organize your findings into two clear lists:

1. GDPR COMPLIANCE ISSUES - Violations of GDPR principles
2. GDPR COMPLIANCE POINTS - Alignment with GDPR requirements

For each compliance issue:
- Title of the issue
- Specific GDPR article violated
- Confidence level (High/Medium/Low)
- Explanation of why it violates GDPR
- Citation of relevant text

For each compliance point:
- Title of the compliance point 
- Specific GDPR article being followed
- Confidence level (High/Medium/Low)
- Explanation of how this aligns with GDPR
- Citation of relevant text

Format your answer using the following structure:

COMPLIANCE ISSUES:
ISSUE 1: [Title]
Article: [Article number]
Confidence: [High/Medium/Low]
Explanation: [Why this violates GDPR]
Citation: "[Relevant text]"

COMPLIANCE POINTS:
POINT 1: [Title]
Article: [Article number]
Confidence: [High/Medium/Low]
Explanation: [How this aligns with GDPR]
Citation: "[Relevant text]"

If a section contains no compliance issues or points, explicitly state "No compliance issues found" or "No compliance points found".

Only include issues and points where there is a clear statement or practice in the text. If you cannot find any clear compliance issues or points, state that explicitly.
"""
        
        # Get the structured response
        try:
            # Use the same model config as the main handler
            from config import MODELS, DEFAULT_MODEL
            model_config = None
            
            # Try to find the current model configuration
            for key, config in MODELS.items():
                if "llama3" in config["name"].lower():
                    model_config = config
                    break
            
            # If not found, use default
            if not model_config:
                model_config = MODELS[DEFAULT_MODEL]
                
            # Create an LLM instance for the second stage
            llm = Ollama(
                model=model_config["name"],
                temperature=0.1  # Lower temperature for more consistent formatting
            )
            
            structured_response = llm.invoke(structuring_prompt)
            
            if self.debug:
                print(f"Structured response first 200 chars: {structured_response[:200]}...")
                
            # Now parse the structured response into issues and compliance points
            result = self._parse_structured_response(structured_response)
            
            return result
            
        except Exception as e:
            if self.debug:
                print(f"Error getting structured response: {e}")
                import traceback
                traceback.print_exc()
            
            # Fallback to direct parsing of the analysis
            return self._extract_directly(analysis_response)
    
    def _parse_structured_response(self, structured_response):
        """Parse the structured response into a dictionary of issues and compliance points."""
        issues = []
        compliance_points = []
        
        # Check if there's a sections division
        issues_section = None
        compliance_section = None
        
        # Try to extract the major sections
        if "COMPLIANCE ISSUES:" in structured_response:
            parts = structured_response.split("COMPLIANCE ISSUES:")
            if len(parts) > 1:
                pre_issues = parts[0]
                rest = parts[1]
                
                if "COMPLIANCE POINTS:" in rest:
                    parts = rest.split("COMPLIANCE POINTS:")
                    issues_section = parts[0].strip()
                    compliance_section = parts[1].strip()
                else:
                    issues_section = rest.strip()
        elif "COMPLIANCE POINTS:" in structured_response:
            parts = structured_response.split("COMPLIANCE POINTS:")
            compliance_section = parts[1].strip()
        
        # Parse issues if found
        if issues_section:
            # Look for "No compliance issues found" statement
            if "No compliance issues found" in issues_section or "No issues found" in issues_section:
                # No issues to parse
                pass
            else:
                # Pattern to match numbered issues with fields
                issue_pattern = re.compile(
                    r'(?:ISSUE|Issue)\s*\d+:\s*(.+?)\s*\n'
                    r'(?:Article|ARTICLE):\s*(.+?)\s*\n'
                    r'(?:Confidence|CONFIDENCE):\s*(High|Medium|Low)\s*\n'
                    r'(?:Explanation|EXPLANATION):\s*(.+?)\s*\n'
                    r'(?:(?:Citation|CITATION):\s*(?:"(.+?)"|(.+?)))?(?:\n\n|\n(?:ISSUE|Issue)|\Z)',
                    re.DOTALL | re.IGNORECASE
                )
                
                matches = issue_pattern.finditer(issues_section)
                for match in matches:
                    # Extract issue details
                    issue = {
                        "issue": match.group(1).strip(),
                        "regulation": self._format_article(match.group(2).strip()),
                        "confidence": match.group(3).strip(),
                        "explanation": match.group(4).strip()
                    }
                    
                    # Add citation if present and it looks like document text (not regulation text)
                    citation = match.group(5) or match.group(6)
                    if citation and self._is_document_citation(citation.strip()):
                        issue["citation"] = citation.strip()
                    
                    issues.append(issue)
                
                # If no issues found with pattern, try simpler extraction
                if not issues:
                    issues = self._extract_simple_items(issues_section, "issue")
        
        # Parse compliance points if found
        if compliance_section:
            # Look for "No compliance points found" statement
            if "No compliance points found" in compliance_section or "No points found" in compliance_section:
                # No points to parse
                pass
            else:
                # Pattern to match numbered compliance points with fields
                point_pattern = re.compile(
                    r'(?:POINT|Point)\s*\d+:\s*(.+?)\s*\n'
                    r'(?:Article|ARTICLE):\s*(.+?)\s*\n'
                    r'(?:Confidence|CONFIDENCE):\s*(High|Medium|Low)\s*\n'
                    r'(?:Explanation|EXPLANATION):\s*(.+?)\s*\n'
                    r'(?:(?:Citation|CITATION):\s*(?:"(.+?)"|(.+?)))?(?:\n\n|\n(?:POINT|Point)|\Z)',
                    re.DOTALL | re.IGNORECASE
                )
                
                matches = point_pattern.finditer(compliance_section)
                for match in matches:
                    # Extract compliance point details
                    point = {
                        "point": match.group(1).strip(),
                        "regulation": self._format_article(match.group(2).strip()),
                        "confidence": match.group(3).strip(),
                        "explanation": match.group(4).strip()
                    }
                    
                    # Add citation if present and it looks like document text (not regulation text)
                    citation = match.group(5) or match.group(6)
                    if citation and self._is_document_citation(citation.strip()):
                        point["citation"] = citation.strip()
                    
                    compliance_points.append(point)
                
                # If no points found with pattern, try simpler extraction
                if not compliance_points:
                    compliance_points = self._extract_simple_items(compliance_section, "point")
        
        # Return a dictionary with both issues and compliance_points
        return {
            "issues": issues,
            "compliance_points": compliance_points
        }
    
    def _is_document_citation(self, citation_text):
        """Check if citation looks like document text rather than regulation text."""
        # Remove quotes if present
        text = citation_text.strip('"').strip("'")
        
        # Skip very short citations
        if len(text) < 10:
            return False
            
        # Red flags that suggest this is regulation text, not document text
        regulation_indicators = [
            "the controller shall",
            "data subject",
            "personal data shall",
            "where personal data",
            "the data subject shall",
            "processing shall be",
            "article",
            "paragraph",
            "regulation"
        ]
        
        text_lower = text.lower()
        for indicator in regulation_indicators:
            if indicator in text_lower:
                return False
                
        # If it looks like business/technical language, it's probably document text
        business_indicators = [
            "project", "platform", "system", "database", "app", "website",
            "customer", "user", "data", "collect", "store", "process",
            "month", "year", "budget", "team", "develop", "implement"
        ]
        
        for indicator in business_indicators:
            if indicator in text_lower:
                return True
                
        # Default to accepting if no clear regulation language
        return True
    
    def _extract_simple_items(self, text, item_type):
        """Extract items using simpler patterns when the structured format fails."""
        items = []
        
        # Try to extract items line by line
        lines = text.split('\n')
        current_item = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this starts a new item
            if re.match(r'^\d+\.', line) or re.match(r'^[-*•]', line):
                # Save previous item if it exists
                if current_item:
                    items.append(current_item)
                
                # Start new item
                current_item = {
                    item_type: line,
                    "regulation": "Unknown Article",
                    "confidence": "Medium",
                    "explanation": ""
                }
            elif re.match(r'^Article|^GDPR Article', line, re.IGNORECASE):
                if current_item:
                    current_item["regulation"] = line
            elif re.match(r'^Confidence|^CONFIDENCE', line, re.IGNORECASE):
                if current_item:
                    confidence_match = re.search(r'(High|Medium|Low)', line, re.IGNORECASE)
                    if confidence_match:
                        current_item["confidence"] = confidence_match.group(1)
            elif re.match(r'^Explanation|^EXPLANATION', line, re.IGNORECASE):
                if current_item:
                    explanation_parts = line.split(':', 1)
                    if len(explanation_parts) > 1:
                        current_item["explanation"] = explanation_parts[1].strip()
            elif re.match(r'^Citation|^CITATION', line, re.IGNORECASE):
                if current_item:
                    citation_parts = line.split(':', 1)
                    if len(citation_parts) > 1:
                        citation_text = citation_parts[1].strip().strip('"')
                        # Only add citation if it looks like document text
                        if self._is_document_citation(citation_text):
                            current_item["citation"] = citation_text
            elif current_item:
                # Append to the current item's explanation if it doesn't match any field
                current_item["explanation"] += " " + line
        
        # Add the last item if it exists
        if current_item:
            items.append(current_item)
            
        return items
    
    def _extract_directly(self, analysis_response):
        """Fallback method to extract issues and compliance points directly from the analysis."""
        # Try to split into sections
        issues_text = ""
        compliance_text = ""
        
        if "COMPLIANCE ISSUES:" in analysis_response and "COMPLIANCE POINTS:" in analysis_response:
            # Both sections present
            parts = analysis_response.split("COMPLIANCE ISSUES:")
            pre_issues = parts[0]
            rest = parts[1]
            
            if "COMPLIANCE POINTS:" in rest:
                parts = rest.split("COMPLIANCE POINTS:")
                issues_text = parts[0].strip()
                compliance_text = parts[1].strip()
        elif "COMPLIANCE ISSUES:" in analysis_response:
            # Only issues section
            parts = analysis_response.split("COMPLIANCE ISSUES:")
            issues_text = parts[1].strip()
        elif "COMPLIANCE POINTS:" in analysis_response:
            # Only compliance section
            parts = analysis_response.split("COMPLIANCE POINTS:")
            compliance_text = parts[1].strip()
        
        # Extract issues and compliance points
        issues = self._extract_simple_items(issues_text, "issue")
        compliance_points = self._extract_simple_items(compliance_text, "point")
        
        return {
            "issues": issues,
            "compliance_points": compliance_points
        }
    
    def _format_article(self, article_text):
        """Format article references consistently for GDPR (preserves Article format)."""
        if not article_text or article_text in ["Unknown regulation", "Unknown Regulation"]:
            return "Unknown Article"
            
        # Clean up any partial formatting and unwanted characters
        article_text = article_text.strip().rstrip('(').rstrip(':')
        
        # Handle special cases like "voice recognition" that aren't actually articles
        if not re.search(r'\d', article_text):
            return "Unknown Article"
        
        # If it's just a number, add "Article" prefix (GDPR-specific)
        if re.match(r'^\d+$', article_text):
            return f"Article {article_text}"
            
        # If it already includes "Article", format it consistently
        article_match = re.match(r'(?:Article|Art\.)\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)', article_text, re.IGNORECASE)
        if article_match:
            return f"Article {article_match.group(1)}"
        
        # Handle other regulation formats but convert to Article for GDPR consistency
        other_format_match = re.match(r'(?:Section|Rule|Standard|Requirement|Regulation|Part|Chapter)\s*(\d+(?:\.\d+)?(?:\(\d+\))?(?:\([a-z]\))?)', article_text, re.IGNORECASE)
        if other_format_match:
            return f"Article {other_format_match.group(1)}"
        
        # Try to extract just the number part if it's there
        number_match = re.search(r'(\d+(?:\(\d+\))?(?:\([a-z]\))?)', article_text)
        if number_match:
            return f"Article {number_match.group(1)}"
            
        return "Unknown Article"
    
    def format_regulations(self, regulations, regulation_context="", regulation_patterns=""):
        """Format regulations for GDPR-specific prompt with better context."""
        try:
            # Print what we're formatting for debugging
            print(f"Formatting {len(regulations)} GDPR regulations")
            
            formatted_regs = []
            
            # Add GDPR context if available
            if regulation_context:
                formatted_regs.append(f"GDPR CONTEXT:\n{regulation_context}")
            
            # Add common patterns if available (brief summary)
            if regulation_patterns:
                pattern_count = regulation_patterns.count("Pattern:")
                if pattern_count > 0:
                    formatted_regs.append(f"GDPR VIOLATION PATTERNS: {pattern_count} patterns available")
            
            # Add specific regulations with more context
            for i, reg in enumerate(regulations):
                reg_text = reg.get("text", "")
                reg_id = reg.get("id", f"Article {i+1}")
                reg_title = reg.get("title", "")
                related_concepts = reg.get("related_concepts", [])
                
                # Include regulation ID and title if available
                formatted_reg = f"GDPR ARTICLE {i+1}: {reg_id}"
                if reg_title:
                    formatted_reg += f" - {reg_title}"
                    
                if related_concepts:
                    formatted_reg += f"\nRELATED CONCEPTS: {', '.join(related_concepts)}"
                    
                formatted_reg += f"\n{reg_text}"
                
                formatted_regs.append(formatted_reg)
                
            return "\n\n".join(formatted_regs)
            
        except Exception as e:
            print(f"Error in GDPR handler's format_regulations: {e}")
            # Provide a basic fallback format
            return "\n\n".join([f"GDPR Article: {reg.get('id', 'Unknown')}\n{reg.get('text', '')}" for reg in regulations])