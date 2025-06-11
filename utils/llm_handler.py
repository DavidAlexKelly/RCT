# utils/llm_handler.py

from typing import List, Dict, Any, Optional
import re
import importlib
from pathlib import Path
import os

class LLMHandler:
    def __init__(self, model_config=None, prompt_manager=None, debug=False):
        """
        Initialize the LLM handler with model configuration.
        
        Args:
            model_config: Dictionary with model configuration
            prompt_manager: PromptManager instance for generating prompts
            debug: Whether to print detailed debug information
        """
        self.debug = debug
        
        # Use default configuration if none provided
        if model_config is None:
            from config.models import MODELS, DEFAULT_MODEL
            self.model_config = MODELS[DEFAULT_MODEL]
            self.model_key = DEFAULT_MODEL
        else:
            self.model_config = model_config
            self.model_key = model_config.get("key", "custom")
        
        # Initialize the model
        from langchain_ollama import OllamaLLM as Ollama
        self.llm = Ollama(
            model=self.model_config["name"],
            temperature=self.model_config.get("temperature", 0.1)
        )
        print(f"Initialized LLM with model: {self.model_config['name']} ({self.model_key})")
        
        # Set prompt manager
        self.prompt_manager = prompt_manager
    
    def get_batch_size(self) -> int:
        """Return the recommended batch size for this model."""
        return self.model_config.get("batch_size", 1)
    
    def invoke(self, prompt: str) -> str:
        """Direct LLM invocation method."""
        return self.llm.invoke(prompt)
    
    def analyze_compliance(self, document_chunk: Dict[str, Any], 
                           regulations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze document chunk for compliance issues and compliance points.
        
        Args:
            document_chunk: Dictionary containing chunk text and metadata
            regulations: List of relevant regulations
            
        Returns:
            Dictionary with issues and compliance points
        """
        # Extract text and metadata
        doc_text = document_chunk.get("text", "")
        chunk_position = document_chunk.get("position", "Unknown")
        should_analyze = document_chunk.get("should_analyze", True)
        detected_patterns = document_chunk.get("detected_patterns", [])
        
        if self.debug:
            print(f"\nAnalyzing chunk: '{chunk_position}' (Analyze: {should_analyze})")
            print(f"Text (first 50 chars): '{doc_text[:50]}...'")
            if detected_patterns:
                print(f"Detected patterns: {detected_patterns[:3]}")
        
        # Skip LLM for chunks marked as low-priority
        if not should_analyze:
            return {
                "issues": [],
                "compliance_points": [],
                "position": chunk_position,
                "text": doc_text,
                "should_analyze": False
            }
        
        # Extract content indicators if prompt manager has associated regulation handler
        content_indicators = {}
        potential_violations = []
        
        if self.prompt_manager and hasattr(self.prompt_manager, 'regulation_handler'):
            handler = self.prompt_manager.regulation_handler
            
            # Extract content indicators
            if hasattr(handler, 'extract_content_indicators'):
                content_indicators = handler.extract_content_indicators(doc_text)
            
            # Extract potential violations
            if hasattr(handler, 'extract_potential_violations'):
                regulation_patterns = getattr(self.prompt_manager, 'regulation_patterns', '')
                potential_violations = handler.extract_potential_violations(
                    doc_text, regulation_patterns
                )
            
            # If we have detected patterns from progressive analysis, convert them
            if detected_patterns:
                # Add them to potential violations for more comprehensive analysis
                for pattern in detected_patterns:
                    # Extract pattern name and indicator from the pattern string
                    if ":" in pattern:
                        parts = pattern.split(":", 1)
                        pattern_type = parts[0].strip()
                        indicator = parts[1].strip().strip("'")
                        
                        potential_violations.append({
                            "pattern": pattern_type,
                            "indicator": indicator,
                            "context": f"...{indicator}...",  # Simplified context
                            "related_refs": []  # No refs available from pattern matching
                        })
        
        # Format regulations using prompt manager
        formatted_regulations = ""
        if self.prompt_manager:
            # Use top regulations for analysis
            regs_to_use = regulations[:5]  # Limit to top 5 relevant regulations
            formatted_regulations = self.prompt_manager.format_regulations(regs_to_use)
        else:
            # Simple formatting if no prompt manager
            formatted_regulations = "\n\n".join(
                [f"REGULATION {i+1}: {reg.get('id', '')}\n{reg.get('text', '')}" 
                 for i, reg in enumerate(regulations)]
            )
        
        # Generate the analysis prompt
        prompt = ""
        if self.prompt_manager:
            prompt = self.prompt_manager.create_analysis_prompt(
                doc_text, 
                chunk_position, 
                formatted_regulations, 
                content_indicators,
                potential_violations
            )
        else:
            # Create a minimal prompt if no manager
            prompt = self._create_default_prompt(doc_text, chunk_position, formatted_regulations)
        
        # Get response from LLM
        response = self.llm.invoke(prompt)
        
        if self.debug:
            print(f"LLM response (first 200 chars): {response[:200]}...")
        
        # Extract structured data from response
        result = self._extract_issues_and_points(response, doc_text)
        
        # Add metadata to result
        result["position"] = chunk_position
        result["text"] = doc_text
        result["should_analyze"] = True
        
        # Add section info to issues and compliance points
        for issue in result.get("issues", []):
            issue["section"] = chunk_position
            
        for point in result.get("compliance_points", []):
            point["section"] = chunk_position
        
        return result
    
    def _create_default_prompt(self, text: str, section: str, regulations: str) -> str:
        """Create a default analysis prompt when no prompt manager is available."""
        return f"""You are an expert regulatory compliance auditor. Your task is to analyze this text section for compliance issues and points.

SECTION: {section}
TEXT:
{text}

RELEVANT REGULATIONS:
{regulations}

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
Users cannot refuse to share data, violating consent requirements. "Users will be required to accept all data collection to use the app."

COMPLIANCE POINTS:

The document provides clear user notification about data usage. "Our implementation will use a simple banner stating 'By using this site, you accept our terms'."


If no issues are found, write "NO COMPLIANCE ISSUES DETECTED."
If no compliance points are found, write "NO COMPLIANCE POINTS DETECTED."
"""
    
    def _extract_issues_and_points(self, response, doc_text):
        """Extract compliance issues and points from response with simplified field structure."""
        # For debugging
        if self.debug:
            print(f"Raw LLM response:\n{response[:500]}...\n[truncated]")
        
        # Default empty structure    
        result = {
            "issues": [],
            "compliance_points": []
        }
        
        # Remove any code blocks or markdown formatting
        response = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
        
        # Check for "NO COMPLIANCE ISSUES DETECTED"
        if "NO COMPLIANCE ISSUES DETECTED" in response:
            # No issues to process
            pass
        else:
            # Try to find issues section
            issues_section = ""
            issues_match = re.search(r'COMPLIANCE\s+ISSUES:?\s*\n(.*?)(?:COMPLIANCE\s+POINTS:|$)', response, re.DOTALL | re.IGNORECASE)
            if issues_match:
                issues_section = issues_match.group(1).strip()
                
                # Process numbered issues (1. Description... "Quote")
                issue_pattern = re.compile(r'(?:^|\n)\s*\d+\.\s+(.*?)(?=(?:\n\s*\d+\.)|$)', re.DOTALL)
                for match in issue_pattern.finditer(issues_section):
                    issue_text = match.group(1).strip()
                    
                    # Skip if too short or just a header
                    if len(issue_text) < 10 or issue_text.lower() in ["compliance issues", "no issues"]:
                        continue
                    
                    # Extract quote if present
                    quote = ""
                    quote_match = re.search(r'"([^"]+)"', issue_text)
                    if quote_match:
                        quote = quote_match.group(0)
                        
                    # Extract regulation if present - framework-agnostic extraction
                    regulation = "Unknown Regulation"
                    
                    # Try multiple regulation formats (Article, Section, Rule, Standard, etc.)
                    reg_patterns = [
                        r'\((?:(Article|Section|Rule|Standard|Requirement|Regulation|Part|Chapter)\s*)?(\d+(?:\.\d+)?(?:\(\d+\))?(?:\([a-z]\))?)\)',
                        r'\b(Article|Section|Rule|Standard|Requirement|Regulation|Part|Chapter)\s*(\d+(?:\.\d+)?(?:\(\d+\))?(?:\([a-z]\))?)\b'
                    ]
                    
                    for pattern in reg_patterns:
                        reg_match = re.search(pattern, issue_text, re.IGNORECASE)
                        if reg_match:
                            ref_type = reg_match.group(1) if reg_match.group(1) else "Section"
                            ref_number = reg_match.group(2)
                            regulation = f"{ref_type} {ref_number}"
                            break
                    
                    # Combine any explanation with the main issue for a comprehensive description
                    full_issue_description = issue_text
                    if "EXPLANATION:" in issue_text.upper():
                        parts = re.split(r'EXPLANATION:', issue_text, flags=re.IGNORECASE, maxsplit=1)
                        issue_part = parts[0].strip()
                        explanation_part = parts[1].strip() if len(parts) > 1 else ""
                        
                        # Remove the citation from the issue part if present
                        if quote and quote in issue_part:
                            issue_part = issue_part.split(quote)[0].strip()
                        
                        # Combine for a comprehensive description
                        full_issue_description = issue_part
                        if explanation_part and not explanation_part.startswith("This violates") and not issue_part.endswith("."):
                            full_issue_description += ". " + explanation_part
                    else:
                        # If no explicit explanation, just use the issue text without the citation
                        if quote:
                            full_issue_description = issue_text.split(quote)[0].strip()
                        
                    # Create issue
                    issue = {
                        "issue": full_issue_description,
                        "regulation": regulation,
                        "confidence": "Medium",
                        "citation": quote if quote else ""
                    }
                    
                    result["issues"].append(issue)
        
        # Check for "NO COMPLIANCE POINTS DETECTED"
        if "NO COMPLIANCE POINTS DETECTED" in response:
            # No points to process
            pass
        else:
            # Try to find compliance points section
            points_section = ""
            points_match = re.search(r'COMPLIANCE\s+POINTS:?\s*\n(.*?)$', response, re.DOTALL | re.IGNORECASE)
            if points_match:
                points_section = points_match.group(1).strip()
                
                # Process numbered points (1. Description... "Quote")
                point_pattern = re.compile(r'(?:^|\n)\s*\d+\.\s+(.*?)(?=(?:\n\s*\d+\.)|$)', re.DOTALL)
                for match in point_pattern.finditer(points_section):
                    point_text = match.group(1).strip()
                    
                    # Skip if too short or just a header
                    if len(point_text) < 10 or point_text.lower() in ["compliance points", "no points"]:
                        continue
                    
                    # Extract quote if present
                    quote = ""
                    quote_match = re.search(r'"([^"]+)"', point_text)
                    if quote_match:
                        quote = quote_match.group(0)
                        
                    # Extract regulation if present - framework-agnostic extraction
                    regulation = "Unknown Regulation"
                    
                    # Try multiple regulation formats (Article, Section, Rule, Standard, etc.)
                    reg_patterns = [
                        r'\((?:(Article|Section|Rule|Standard|Requirement|Regulation|Part|Chapter)\s*)?(\d+(?:\.\d+)?(?:\(\d+\))?(?:\([a-z]\))?)\)',
                        r'\b(Article|Section|Rule|Standard|Requirement|Regulation|Part|Chapter)\s*(\d+(?:\.\d+)?(?:\(\d+\))?(?:\([a-z]\))?)\b'
                    ]
                    
                    for pattern in reg_patterns:
                        reg_match = re.search(pattern, point_text, re.IGNORECASE)
                        if reg_match:
                            ref_type = reg_match.group(1) if reg_match.group(1) else "Section"
                            ref_number = reg_match.group(2)
                            regulation = f"{ref_type} {ref_number}"
                            break
                    
                    # Combine any explanation with the main point for a comprehensive description
                    full_point_description = point_text
                    if "EXPLANATION:" in point_text.upper():
                        parts = re.split(r'EXPLANATION:', point_text, flags=re.IGNORECASE, maxsplit=1)
                        point_part = parts[0].strip()
                        explanation_part = parts[1].strip() if len(parts) > 1 else ""
                        
                        # Remove the citation from the point part if present
                        if quote and quote in point_part:
                            point_part = point_part.split(quote)[0].strip()
                        
                        # Combine for a comprehensive description
                        full_point_description = point_part
                        if explanation_part and not explanation_part.startswith("This supports") and not point_part.endswith("."):
                            full_point_description += ". " + explanation_part
                    else:
                        # If no explicit explanation, just use the point text without the citation
                        if quote:
                            full_point_description = point_text.split(quote)[0].strip()
                    
                    # Create point
                    point = {
                        "point": full_point_description,
                        "regulation": regulation,
                        "confidence": "Medium",
                        "citation": quote if quote else ""
                    }
                    
                    result["compliance_points"].append(point)
        
        return result