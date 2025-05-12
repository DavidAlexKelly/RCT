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
    
    def create_analysis_prompt(self, text, section, regulations, content_indicators, potential_violations, regulation_framework):
        """Create a GDPR-specific prompt for compliance analysis with a two-stage approach that focuses on actual violations."""
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
            
        # Stage 1: Fair analysis prompt
        analysis_prompt = f"""You are an expert GDPR compliance analyst. Analyze the following text and identify any GDPR compliance issues that are explicitly present.

    SECTION: {section}
    TEXT:
    {text}

    IMPORTANT: This is a section of a document, not a complete privacy policy. Focus your analysis on what is actually stated in the text.

    RELEVANT GDPR REGULATIONS:
    {regulations}

    CONTENT INDICATORS:
    {content_indicators_text}

    {potential_violations_text if potential_violations else ""}

    IMPORTANT ANALYSIS GUIDELINES:
    1. ONLY identify issues based on what is actually stated in the text
    2. DO NOT flag the mere absence of information as an issue unless the document type requires that information
    3. Focus on statements or practices that would actually violate GDPR principles
    4. Be fair and contextual in your analysis
    5. Only flag genuine compliance concerns, not missing details that would be reasonable to include elsewhere
    6. Consider the nature and purpose of this section when determining if something is truly a violation

    Specific examples of what to flag:
    - "Data will be stored indefinitely" - This explicitly violates storage limitation
    - "Users must accept all data collection to use the service" - This explicitly violates consent requirements
    - "We won't implement data encryption at rest" - This explicitly violates security requirements

    Do NOT flag these types of issues unless this is a dedicated privacy policy or compliance document:
    - "The document doesn't mention a DPO" - Not every document needs to mention a DPO
    - "No information is provided about breach notification" - Not every document needs this detail
    - "The section doesn't specify the legal basis" - Not every section needs to cover this

    Please provide a thoughtful analysis of ACTUAL GDPR compliance issues in this text. Think step by step about what statements would genuinely be problematic from a GDPR compliance perspective.
    """
        
        return analysis_prompt
    
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
    
    def extract_structured_issues(self, analysis_response):
        """
        Process the LLM's analysis and ask it to structure only genuine findings.
        This two-stage approach focuses on actual violations rather than missing information.
        """
        from langchain_ollama import OllamaLLM as Ollama
        
        # Create the structuring prompt based on the initial analysis
        structuring_prompt = f"""Based on your previous GDPR compliance analysis:

    {analysis_response}

    Please organize your findings into a clear list of ONLY the genuine GDPR compliance issues. For each issue:

    1. Focus only on statements or claims that ACTUALLY violate GDPR principles
    2. Do not include issues about "missing information" unless the document type clearly requires that information
    3. Be fair and contextual in your assessment

    Format your answer as a list of numbered issues. For example:

    ISSUE 1: Indefinite Data Storage
    Article: 5(1)(e)
    Confidence: High
    Explanation: The document explicitly states they will keep user data indefinitely, which violates GDPR's storage limitation principle.
    Citation: "All customer data will be stored indefinitely"

    ISSUE 2: Forced Consent Mechanism
    Article: 7(4)
    Confidence: High
    Explanation: The document states users must accept all data collection to use the app, which violates GDPR's requirement that consent be freely given.
    Citation: "Users will be required to accept all data collection to use the app"

    Only include issues where there is a clear statement or practice that would violate GDPR. If a section contains no actual violations, return an empty list rather than trying to find issues based on missing information.
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
                
            # Now parse the structured response into issues
            return self._parse_structured_issues(structured_response)
            
        except Exception as e:
            if self.debug:
                print(f"Error getting structured response: {e}")
                import traceback
                traceback.print_exc()
            
            # Fallback to direct parsing of the analysis
            return self._extract_issues_directly(analysis_response)

    def _parse_structured_issues(self, structured_response):
        """Parse the structured response into a dictionary of issues."""
        issues = []
        
        # Pattern to match numbered issues with fields
        issue_pattern = re.compile(
            r'(?:ISSUE|Issue)\s*\d+:\s*(.+?)\s*\n'
            r'(?:Article|ARTICLE):\s*(.+?)\s*\n'
            r'(?:Confidence|CONFIDENCE):\s*(High|Medium|Low)\s*\n'
            r'(?:Explanation|EXPLANATION):\s*(.+?)\s*\n'
            r'(?:(?:Citation|CITATION):\s*(?:"(.+?)"|(.+?)))?(?:\n\n|\n(?:ISSUE|Issue)|\Z)',
            re.DOTALL
        )
        
        matches = issue_pattern.finditer(structured_response)
        for match in matches:
            # Extract issue details
            issue = {
                "issue": match.group(1).strip(),
                "regulation": self._format_article(match.group(2).strip()),
                "confidence": match.group(3).strip(),
                "explanation": match.group(4).strip()
            }
            
            # Add citation if present
            citation = match.group(5) or match.group(6)
            if citation:
                issue["citation"] = citation.strip()
            
            issues.append(issue)
        
        # If no issues found, try a simpler pattern
        if not issues:
            # Look for patterns like "1. [Issue Title] - violates Article X"
            simple_pattern = re.compile(
                r'(?:\d+\.|\*)\s*(.+?)(?:(?:violates|breaches|against)\s+(?:Article|GDPR)\s*(.+?))?(?:-|\(|:)\s*(.+?)(?:\n|$)', 
                re.DOTALL
            )
            
            matches = simple_pattern.finditer(structured_response)
            for match in matches:
                issue_title = match.group(1).strip()
                
                # Skip if it's too short or likely not an issue
                if len(issue_title) < 5 or issue_title.lower() in ["summary", "conclusion", "overview"]:
                    continue
                    
                # Extract the article if available
                article = match.group(2).strip() if match.group(2) else "Unknown Article"
                
                # Extract explanation
                explanation = match.group(3).strip() if match.group(3) else ""
                
                issues.append({
                    "issue": issue_title,
                    "regulation": self._format_article(article),
                    "confidence": "Medium",  # Default when not specified
                    "explanation": explanation
                })
        
        # If still no issues, try scanning for article mentions
        if not issues:
            # Look for GDPR articles in the text
            article_pattern = re.compile(r'Article\s+(\d+(?:\(\d+\))?(?:\([a-z]\))?)', re.IGNORECASE)
            article_matches = article_pattern.findall(structured_response)
            
            for article in set(article_matches):
                # Find nearby text that might be an issue description
                context_pattern = re.compile(
                    r'([^.!?\n]{10,100}(?:Article\s+' + re.escape(article) + r')[^.!?\n]{10,100})', 
                    re.DOTALL
                )
                context_matches = context_pattern.findall(structured_response)
                
                if context_matches:
                    for context in context_matches:
                        issues.append({
                            "issue": f"Violation of Article {article}",
                            "regulation": self._format_article(article),
                            "confidence": "Medium",
                            "explanation": context.strip()
                        })
        
        # Return a dictionary with the issues
        return {"issues": issues}
    
    def _extract_issues_directly(self, analysis_response):
        """Fallback method to extract issues directly from the analysis."""
        issues = []
        
        # Look for mentions of GDPR articles
        article_mentions = re.finditer(
            r'(?:Article|Art\.)\s+(\d+(?:\(\d+\))?(?:\([a-z]\))?)',
            analysis_response,
            re.IGNORECASE
        )
        
        for match in article_mentions:
            article_num = match.group(1)
            article_pos = match.start()
            
            # Look for a sentence or paragraph around this article mention
            context_start = max(0, article_pos - 200)
            context_end = min(len(analysis_response), article_pos + 200)
            context = analysis_response[context_start:context_end]
            
            # Try to extract the violation from context
            violation_match = re.search(
                r'([^.!?\n]{10,100}' + re.escape(match.group(0)) + r'[^.!?\n]{10,100})',
                context,
                re.DOTALL
            )
            
            if violation_match:
                issues.append({
                    "issue": f"Violation of {match.group(0)}",
                    "regulation": self._format_article(article_num),
                    "confidence": "Medium",
                    "explanation": violation_match.group(1).strip()
                })
        
        # Look for key GDPR concepts
        concepts = [
            "consent", "purpose limitation", "data minimization", "storage limitation",
            "data subject rights", "security", "accountability", "transparency",
            "automated decision making", "special category data"
        ]
        
        for concept in concepts:
            concept_matches = re.finditer(
                r'([^.!?\n]{0,50}' + re.escape(concept) + r'[^.!?\n]{10,100}[.!?])',
                analysis_response,
                re.IGNORECASE | re.DOTALL
            )
            
            for match in concept_matches:
                if any(issue["explanation"] == match.group(1).strip() for issue in issues):
                    # Skip if we already have this exact explanation
                    continue
                    
                issues.append({
                    "issue": f"Potential {concept} issue",
                    "regulation": self._map_concept_to_article(concept),
                    "confidence": "Low",
                    "explanation": match.group(1).strip()
                })
        
        # Return a dictionary with the issues
        return {"issues": issues}
    
    def _format_article(self, article_text):
        """Format article references consistently."""
        # If it's just a number, add "Article" prefix
        if re.match(r'^\d+$', article_text):
            return f"Article {article_text}"
            
        # If it already includes "Article", format it consistently
        article_match = re.match(r'(?:Article|Art\.)\s*(\d+(?:\(\d+\))?(?:\([a-z]\))?)', article_text, re.IGNORECASE)
        if article_match:
            return f"Article {article_match.group(1)}"
            
        return article_text
    
    def _map_concept_to_article(self, concept):
        """Map GDPR concepts to specific articles."""
        concept_map = {
            "consent": "Article 7",
            "purpose limitation": "Article 5(1)(b)",
            "data minimization": "Article 5(1)(c)",
            "storage limitation": "Article 5(1)(e)",
            "data subject rights": "Articles 15-22",
            "security": "Article 32",
            "accountability": "Article 5(2)",
            "transparency": "Article 12",
            "automated decision making": "Article 22",
            "special category data": "Article 9",
            "transfer": "Article 44",
            "breach": "Article 33"
        }
        
        # Check for concept in the map
        for key, article in concept_map.items():
            if key in concept.lower():
                return article
                
        # Default for unknown concepts
        return "Unknown Article"