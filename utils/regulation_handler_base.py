# utils/regulation_handler_base.py

import re
from typing import Dict, Any, List, Optional

class RegulationHandlerBase:
    """Base class with common functionality for all regulation handlers."""
    
    def __init__(self, debug=False):
        """Initialize the regulation handler."""
        self.debug = debug
    
    def extract_content_indicators(self, text: str) -> Dict[str, str]:
        """Extract content indicators from text. Override for regulation-specific terms."""
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
        """Extract potential violation patterns from text. Override for regulation-specific patterns."""
        if not patterns_text:
            return []
        
        violations = []
        
        # Parse pattern blocks from common_patterns.txt
        pattern_blocks = patterns_text.split('\n\n')
        for block in pattern_blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
            
            pattern_name, description, indicators, related_refs = self._parse_pattern_block(lines)
            
            if pattern_name and indicators:
                for indicator in indicators:
                    if indicator.lower() in text.lower():
                        violations.append({
                            "pattern": pattern_name,
                            "description": description,
                            "indicator": indicator,
                            "context": self._get_context(text, indicator),
                            "related_refs": related_refs
                        })
        
        return violations
    
    def validate_citation_against_document(self, citation: str, document_text: str) -> bool:
        """Enhanced validation that citation actually appears in the document text."""
        if not citation or not document_text:
            return False
        
        # Clean citation (remove quotes)
        clean_citation = citation.strip('"').strip("'").strip()
        
        if len(clean_citation) < 10:
            return False
        
        # Check if citation appears in document (with some flexibility for minor differences)
        document_lower = document_text.lower()
        citation_lower = clean_citation.lower()
        
        # Direct match
        if citation_lower in document_lower:
            return True
        
        # Check for partial matches (at least 80% of citation should match)
        words = citation_lower.split()
        if len(words) >= 3:
            # Check if most words appear near each other in the document
            word_positions = []
            for word in words:
                if word in document_lower:
                    word_positions.append(document_lower.find(word))
                else:
                    return False  # If any word is missing, it's not a valid citation
            
            # Check if words appear in reasonable proximity (within 200 characters)
            if word_positions:
                min_pos, max_pos = min(word_positions), max(word_positions)
                if max_pos - min_pos <= 200:
                    return True
        
        return False
    
    def _get_framework_regulation_phrases(self) -> List[str]:
        """Get framework-specific regulation phrases. Override in subclasses."""
        return []
    
    def _get_framework_business_indicators(self) -> List[str]:
        """Get framework-specific business terms. Override in subclasses."""
        return [
            # Generic business terms
            "project", "team", "develop", "implement", "company", "business",
            "revenue", "marketing", "product", "service", "feature",
            "system", "platform", "database", "application", "software",
            "month", "year", "budget", "timeline", "deployment", "launch"
        ]
        
    def _is_document_citation(self, citation: str) -> bool:
        """Check if citation looks like document text rather than regulation text."""
        if not citation or len(citation.strip()) < 10:
            return False
        
        text = citation.lower().strip('"').strip("'")
        
        # GENERIC regulation language detection (framework-agnostic)
        regulation_phrases = [
            # Generic legal phrases
            "shall be", "shall have", "shall not", "in accordance with",
            "pursuant to", "notwithstanding", "whereas", "hereby",
            "aforementioned", "hereinafter", "heretofore",
            
            # Generic regulation structure words
            "article", "paragraph", "subsection", "regulation",
            "directive", "compliance with", "in respect of",
            "appropriate measures", "technical and organisational measures"
        ]
        
        # Check for regulation language
        for phrase in regulation_phrases:
            if phrase in text:
                if self.debug:
                    print(f"Rejected citation (regulation language): '{phrase}' in '{text[:50]}...'")
                return False
        
        # Check for framework-specific regulation phrases (override in subclasses)
        framework_phrases = self._get_framework_regulation_phrases()
        for phrase in framework_phrases:
            if phrase in text:
                if self.debug:
                    print(f"Rejected citation (framework-specific regulation language): '{phrase}' in '{text[:50]}...'")
                return False
        
        # Check for business/technical language (good indicators)
        business_indicators = self._get_framework_business_indicators()
        
        has_business_language = any(indicator in text for indicator in business_indicators)
        
        # Reject if it looks too legal and has no business language
        legal_structure_count = sum(1 for phrase in ["shall", "must", "required", "obligation"] if phrase in text)
        if legal_structure_count >= 2 and not has_business_language:
            if self.debug:
                print(f"Rejected citation (too legal, no business language): '{text[:50]}...'")
            return False
        
        return True
    
    def _extract_citation_improved(self, text: str, document_text: str = "") -> str:
        """Extract citation with improved validation against document text."""
        # Look for text in quotes - be more flexible about quote types
        quote_patterns = [
            r'"([^"]+)"',                    # Double quotes
            r"'([^']+)'",                    # Single quotes  
            r'["""]([^"""]+)["""]',          # Smart double quotes
            r'['']([^'']+)['']',             # Smart single quotes
        ]
        
        for pattern in quote_patterns:
            try:
                quote_match = re.search(pattern, text)
                if quote_match:
                    citation = quote_match.group(1).strip()
                    
                    # First check: does it look like document text?
                    if not self._is_document_citation(citation):
                        continue
                    
                    # Second check: does it actually appear in the document?
                    if document_text and not self.validate_citation_against_document(f'"{citation}"', document_text):
                        if self.debug:
                            print(f"Rejected citation (not found in document): '{citation[:50]}...'")
                        continue
                    
                    # Third check: framework-specific validation (override in subclasses)
                    if not self._validate_citation_framework_specific(citation, document_text):
                        if self.debug:
                            print(f"Rejected citation (framework-specific validation): '{citation[:50]}...'")
                        continue
                    
                    return f'"{citation}"'
            except Exception as e:
                if self.debug:
                    print(f"Error in quote pattern {pattern}: {e}")
                continue
        
        # If no valid citation found, try to find supporting text from document
        if document_text:
            return self._find_supporting_quote(text, document_text)
        
        return ""
    
    def _validate_citation_framework_specific(self, citation: str, document_text: str) -> bool:
        """Framework-specific citation validation. Override in subclasses."""
        return True  # Base implementation accepts all citations that pass generic checks
    
    def _find_supporting_quote(self, issue_text: str, document_text: str) -> str:
        """Find supporting text from document when direct quote isn't found."""
        if not document_text:
            return "No specific quote provided."
        
        # Look for key phrases from the issue in the document
        sentences = document_text.split('.')
        
        # Extract key terms from the issue description
        key_terms = re.findall(r'\b(indefinite|retain|consent|security|encrypt|data|user|collect|store|process|automatic|manual|privacy|specialist|design|compliance)\w*\b', 
                              issue_text.lower())
        
        best_sentence = ""
        best_score = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
                
            score = sum(1 for term in key_terms if term in sentence.lower())
            if score > best_score and score >= 2:  # Need at least 2 matching terms
                best_score = score
                best_sentence = sentence
        
        if best_sentence:
            # Clean up the sentence
            best_sentence = best_sentence.strip()
            if not best_sentence.endswith('.'):
                best_sentence += '.'
            return f'"{best_sentence}"'
        
        return "No specific quote provided."
    
    def parse_llm_response(self, response: str, document_text: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """Parse LLM response into structured issues and compliance points with document validation."""
        if self.debug:
            print(f"Parsing LLM response with document validation...")
        
        result = {"issues": [], "compliance_points": []}
        
        # Clean up response first
        response = self._clean_response(response)
        
        # Parse issues
        if "NO COMPLIANCE ISSUES DETECTED" not in response:
            issues_match = re.search(r'COMPLIANCE\s+ISSUES:?\s*\n(.*?)(?:COMPLIANCE\s+POINTS:|$)', 
                                   response, re.DOTALL | re.IGNORECASE)
            if issues_match:
                issues_text = issues_match.group(1).strip()
                result["issues"] = self._parse_numbered_items_improved(issues_text, "issue", document_text)
        
        # Parse compliance points
        if "NO COMPLIANCE POINTS DETECTED" not in response:
            points_match = re.search(r'COMPLIANCE\s+POINTS:?\s*\n(.*?)$', 
                                   response, re.DOTALL | re.IGNORECASE)
            if points_match:
                points_text = points_match.group(1).strip()
                # Clean out any stray "NO COMPLIANCE" text that got mixed in
                points_text = re.sub(r'NO COMPLIANCE \w+ DETECTED\.?', '', points_text, flags=re.IGNORECASE)
                result["compliance_points"] = self._parse_numbered_items_improved(points_text, "point", document_text)
        
        if self.debug:
            print(f"Parsed {len(result['issues'])} issues and {len(result['compliance_points'])} compliance points")
        
        return result
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str,
                              content_indicators: Optional[Dict[str, str]] = None,
                              potential_violations: Optional[List[Dict[str, Any]]] = None,
                              regulation_framework: str = "",
                              risk_level: str = "unknown") -> str:
        """Create a regulation-specific prompt for analysis. Override for custom prompts."""
        
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
            violations_text = f"PRE-IDENTIFIED {regulation_framework.upper()} CONCERNS:\n"
            for i, violation in enumerate(potential_violations[:3]):  # Limit to top 3
                violations_text += f"{i+1}. {violation['pattern']}: '{violation['indicator']}'\n"
            violations_text += "\n"
        
        # Create default structured prompt
        return f"""You are an expert regulatory compliance auditor. Analyze this document section for {regulation_framework.upper()} violations and compliance strengths.

SECTION: {section}
TEXT:
{text}

RELEVANT REGULATIONS:
{regulations}

CONTENT ANALYSIS:
{indicators_text}

{violations_text}

TASK: Identify both compliance issues AND compliance strengths in this section.

REQUIRED FORMAT:
COMPLIANCE ISSUES:
1. [Issue description explaining why it violates regulations] "[Direct quote from document]"
2. [Another issue if found] "[Quote]"

COMPLIANCE POINTS:
1. [Compliance strength description] "[Supporting quote from document]"

RULES:
- Use numbered lists (1., 2., etc.)
- Include regulation references in descriptions (e.g., "violating Article 5")
- Always include direct quotes from the document text
- Write "NO COMPLIANCE ISSUES DETECTED" if no issues found
- Write "NO COMPLIANCE POINTS DETECTED" if no strengths found
- Focus on clear, obvious violations rather than minor technical details

"""
    
    def format_regulations(self, regulations: List[Dict[str, Any]], 
                         regulation_context: str = "", regulation_patterns: str = "") -> str:
        """Format regulations for inclusion in prompts."""
        formatted_regs = []
        
        # Add regulation context if available
        if regulation_context:
            formatted_regs.append(f"REGULATION CONTEXT:\n{regulation_context}")
        
        # Add specific regulations
        for i, reg in enumerate(regulations):
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", f"Regulation {i+1}")
            reg_title = reg.get("title", "")
            
            formatted_reg = f"REGULATION {i+1}: {reg_id}"
            if reg_title:
                formatted_reg += f" - {reg_title}"
            formatted_reg += f"\n{reg_text}"
            
            formatted_regs.append(formatted_reg)
        
        return "\n\n".join(formatted_regs)
    
    def _clean_response(self, response: str) -> str:
        """Enhanced response cleaning to remove formatting artifacts."""
        # Remove code blocks and markdown
        response = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
        response = re.sub(r'`([^`]+)`', r'\1', response)  # Remove inline code
        
        # Remove instruction blocks and artifacts
        response = re.sub(r'🚨.*?🚨[^\n]*\n?', '', response, flags=re.DOTALL)
        response = re.sub(r'CITATION EXAMPLES.*?❌[^\n]*\n?', '', response, flags=re.DOTALL)
        response = re.sub(r'\*+', '', response)  # Remove asterisks
        response = re.sub(r'#+\s*', '', response)  # Remove markdown headers
        
        # Normalize spacing
        response = re.sub(r'\n\s*\n\s*\n+', '\n\n', response)  # Max 2 newlines
        response = re.sub(r' +', ' ', response)  # Multiple spaces to single
        
        # Normalize quotes - FIXED: Use str.replace instead of problematic regex
        response = response.replace('"', '"').replace('"', '"')  # Smart double quotes to regular
        response = response.replace(''', "'").replace(''', "'")  # Smart single quotes to regular
        
        return response.strip()
    
    def _parse_numbered_items_improved(self, text: str, item_type: str, document_text: str = "") -> List[Dict[str, Any]]:
        """Parse numbered items with improved citation validation."""
        items = []
        
        if not text or len(text.strip()) < 10:
            return items
        
        # Pattern for numbered items with more flexible matching
        item_pattern = re.compile(r'(?:^|\n)\s*(\d+)\.\s+(.*?)(?=(?:\n\s*\d+\.)|$)', re.DOTALL)
        
        for match in item_pattern.finditer(text):
            item_number = match.group(1)
            item_text = match.group(2).strip()
            
            # Skip very short items, headers, or noise
            if (len(item_text) < 15 or 
                item_text.lower() in ["compliance issues", "compliance points", "no issues", "no points"] or
                "NO COMPLIANCE" in item_text.upper()):
                continue
            
            # Extract citation with document validation
            citation = self._extract_citation_improved(item_text, document_text)
            
            # If no valid citation found, mark it clearly
            if not citation:
                citation = "No specific quote provided."
            
            # Extract regulation reference with better logic
            regulation = self._extract_regulation_reference_improved(item_text)
            
            # Clean description (remove citation and regulation references)
            description = self._clean_description_improved(item_text, citation, regulation)
            
            # Validate we have meaningful content
            if len(description) < 10:
                continue
            
            # Create item with validation
            item = {
                item_type: description,
                "regulation": regulation,
                "confidence": "Medium",
                "citation": citation
            }
            
            items.append(item)
        
        return items
    
    def _parse_pattern_block(self, lines: List[str]) -> tuple:
        """Parse a pattern block from common_patterns.txt."""
        pattern_name = ""
        description = ""
        indicators = []
        related_refs = []
        
        for line in lines:
            line = line.strip()
            if line.startswith("Pattern:"):
                pattern_name = line.replace("Pattern:", "").strip()
            elif line.startswith("Description:"):
                description = line.replace("Description:", "").strip()
            elif line.startswith("Indicators:"):
                indicator_text = line.replace("Indicators:", "").strip()
                # Extract quoted phrases first
                indicators = re.findall(r'"([^"]*)"', indicator_text)
                if not indicators:
                    # Fall back to comma-separated items
                    indicators = [i.strip() for i in indicator_text.split(',') if i.strip()]
            elif line.startswith("Related"):
                refs_text = line.split(":", 1)[1].strip() if ":" in line else ""
                related_refs = [r.strip() for r in refs_text.split(",") if r.strip()]
        
        return pattern_name, description, indicators, related_refs
    
    def _extract_regulation_reference_improved(self, text: str) -> str:
        """Extract regulation reference with better fallback logic."""
        # First try the specific regulation handler
        regulation = self._extract_regulation_reference(text)
        
        # If we got a meaningful result, use it
        if regulation and regulation != "Unknown Regulation":
            return regulation
        
        # Otherwise, look for common regulation patterns more aggressively
        common_patterns = [
            r'\b(Article|Section|Rule|Standard|Regulation)\s*(\d+(?:\.\d+)?(?:\(\d+\))?(?:\([a-z]\))?)',
            r'violating\s+(Article|Section|Rule)\s*(\d+(?:\.\d+)?)',
            r'(GDPR|Article)\s*(\d+(?:\.\d+)?)',
        ]
        
        for pattern in common_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) >= 2:
                    ref_type = match.group(1)
                    ref_number = match.group(2)
                    return f"{ref_type} {ref_number}"
                elif match.group(1).upper() == "GDPR" and len(match.groups()) >= 2:
                    return f"Article {match.group(2)}"
        
        # Final fallback
        return "Article 5"  # GDPR default
    
    def _extract_regulation_reference(self, text: str) -> str:
        """Extract regulation reference from text. Override for framework-specific formatting."""
        # Generic patterns for any regulation framework
        patterns = [
            r'\((?:(Article|Section|Rule|Standard|Requirement|Regulation|Part|Chapter)\s*)?(\d+(?:\.\d+)?(?:\(\d+\))?(?:\([a-z]\))?)\)',
            r'\b(Article|Section|Rule|Standard|Requirement|Regulation|Part|Chapter)\s*(\d+(?:\.\d+)?(?:\(\d+\))?(?:\([a-z]\))?)\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ref_type = match.group(1) if match.group(1) else "Section"
                ref_number = match.group(2)
                return f"{ref_type} {ref_number}"
        
        return "Unknown Regulation"
    
    def _clean_description_improved(self, text: str, citation: str, regulation: str) -> str:
        """Enhanced description cleaning with better artifact removal."""
        # Remove citation from description
        if citation and citation != "No specific quote provided.":
            # Remove the citation and its quotes
            citation_clean = citation.strip('"').strip("'")
            text = text.replace(citation, "").replace(citation_clean, "")
        
        # Remove standalone regulation references
        reg_patterns = [
            r'\s*\([Aa]rticle\s*\d+[^)]*\)\s*',
            r'\s*violating\s*[Aa]rticle\s*\d+[^.]*\.\s*$',
            r'\s*-\s*[Aa]rticle\s*\d+[^.]*$',
        ]
        
        for pattern in reg_patterns:
            text = re.sub(pattern, '', text)
        
        # Clean up sentence structure
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'\.+', '.', text)  # Multiple periods to single
        text = re.sub(r'^\W+', '', text)  # Remove leading punctuation
        text = re.sub(r'\s+\.', '.', text)  # Remove space before period
        
        # Remove redundant phrases
        redundant_phrases = [
            r'This issue violates.*?because',
            r'This violation is supported by.*?\.',
            r'NO COMPLIANCE \w+ DETECTED\.?',
            r'Note:.*?$',
            r'This issue violates regulation because.*?\.',
            r'This issue violates.*?regulation.*?\.',
        ]
        
        for phrase in redundant_phrases:
            text = re.sub(phrase, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up sentence structure again
        text = re.sub(r'\.\s*\.', '.', text)  # Remove double periods
        text = re.sub(r'^\W+', '', text)      # Remove leading non-word chars
        text = re.sub(r'\s+\.', '.', text)    # Remove space before period
        
        # Ensure proper sentence ending
        text = text.strip()
        if text and not text.endswith('.'):
            text += '.'
        
        return text
    
    def _get_context(self, text: str, indicator: str) -> str:
        """Get context around an indicator match."""
        try:
            if not text or not indicator:
                return indicator or ""
            
            match_idx = text.lower().find(indicator.lower())
            if match_idx == -1:
                return indicator
            
            start = max(0, match_idx - 50)
            end = min(len(text), match_idx + len(indicator) + 50)
            return text[start:end]
        except Exception as e:
            if self.debug:
                print(f"Error getting context for '{indicator}': {e}")
            return indicator or ""