from typing import List, Dict, Any
import json
import re

# Import configuration
from config import MODELS, DEFAULT_MODEL, get_prompt_for_regulation

# Try the new import first, fall back to the old one if needed

from langchain_ollama import OllamaLLM as Ollama


class HolisticAnalyzer:
    """
    Second-pass analysis that examines the first-pass findings to detect contradictions.
    """
    
    def __init__(self, model_key=DEFAULT_MODEL, debug=False):
        """Initialize the holistic analyzer."""
        self.debug = debug
        
        # Find the correct model key
        self.model_key = model_key
        
        if model_key not in MODELS:
            for key, config in MODELS.items():
                if config["name"] == model_key:
                    self.model_key = key
                    break
        
        # Get model configuration or use default if not found
        self.model_config = MODELS.get(self.model_key, MODELS[DEFAULT_MODEL])
        
        # Initialize the model
        try:
            self.llm = Ollama(
                model=self.model_config["name"],
                temperature=self.model_config.get("temperature", 0.1)
            )
            if debug:
                print(f"Initialized holistic analyzer with model: {self.model_config['name']} ({self.model_key})")
        except Exception as e:
            # Fall back to default model on memory issues
            if "memory" in str(e).lower():
                print(f"Warning: Falling back to {MODELS[DEFAULT_MODEL]['name']}")
                self.model_key = DEFAULT_MODEL
                self.model_config = MODELS[DEFAULT_MODEL]
                self.llm = Ollama(
                    model=self.model_config["name"],
                    temperature=self.model_config.get("temperature", 0.1)
                )
            else:
                raise
    
    def analyze_document(self, chunk_results: List[Dict], regulation_framework: str) -> List[Dict]:
        """
        Analyze the first-pass findings for contradictions.
        
        Args:
            chunk_results: Results from the first-pass analysis
            regulation_framework: The regulation framework being used
            
        Returns:
            List of contradiction findings
        """
        if not chunk_results:
            return []
        
        # Extract all issues from first-pass results with simplified approach
        all_issues = []
        for chunk in chunk_results:
            section = chunk.get("position", "Unknown")
            
            for issue in chunk.get("issues", []):
                # Add section information to each issue
                issue_copy = {
                    "issue": issue.get("issue", "Unknown issue"),
                    "regulation": issue.get("regulation", "Unknown"),
                    "confidence": issue.get("confidence", "Medium"),
                    "explanation": issue.get("explanation", ""),
                    "section": section
                }
                all_issues.append(issue_copy)
        
        if not all_issues:
            # No issues to analyze
            return []
        
        if self.debug:
            print(f"Analyzing {len(all_issues)} issues for contradictions")
        
        # Create a simple text representation of the issues
        issue_text = self._format_issues_for_analysis(all_issues)
        
        # Get the appropriate prompt for this regulation framework
        prompt_template = get_prompt_for_regulation(regulation_framework, "contradiction_analysis")
        
        # Format the prompt with the issues
        prompt = prompt_template.format(
            issues=issue_text
        )
        
        # Get response from LLM
        if self.debug:
            print("Sending holistic analysis prompt to LLM")
        
        response = self.llm.invoke(prompt)
        
        if self.debug:
            print(f"Received holistic analysis response (first 200 chars): {response[:200]}")
        
        # Extract contradictions from response
        contradictions = self._extract_contradictions(response)
        
        return contradictions
    
    def _format_issues_for_analysis(self, issues):
        """Format issues into a simple text representation."""
        formatted_text = "ISSUES FOUND IN FIRST-PASS ANALYSIS:\n\n"
        
        # Sort issues by section for easier comparison
        issues_by_section = {}
        for issue in issues:
            section = issue.get("section", "Unknown")
            if section not in issues_by_section:
                issues_by_section[section] = []
            issues_by_section[section].append(issue)
        
        # Format each section's issues
        for section, section_issues in issues_by_section.items():
            formatted_text += f"SECTION: {section}\n"
            
            for i, issue in enumerate(section_issues):
                formatted_text += f"  Issue {i+1}: {issue.get('issue', 'Unknown issue')}\n"
                formatted_text += f"    Regulation: {issue.get('regulation', 'Unknown')}\n"
                formatted_text += f"    Confidence: {issue.get('confidence', 'Medium')}\n"
                
                # Include explanation if available (keep it brief)
                explanation = issue.get("explanation", "")
                if explanation:
                    # Truncate long explanations
                    if len(explanation) > 200:
                        explanation = explanation[:197] + "..."
                    formatted_text += f"    Explanation: {explanation}\n"
                
                formatted_text += "\n"
            
            formatted_text += "\n"
        
        return formatted_text
    
    def _extract_contradictions(self, response):
        """Extract contradiction findings from the LLM response with simplified approach."""
        # First, try to parse the entire response as JSON
        try:
            result = json.loads(response)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
        
        # Try to find a JSON array
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                # Try with single quotes replaced
                try:
                    return json.loads(json_match.group(0).replace("'", '"'))
                except json.JSONDecodeError:
                    pass
        
        # If no JSON found, check for structured text
        findings = []
        finding_pattern = re.compile(r'(?:Finding|Contradiction|Issue)\s*\d*:\s*(.*?)(?:\n|$).*?(?:Section|Sections):\s*(.*?)(?:\n|$).*?(?:Confidence|Severity):\s*(.*?)(?:\n|$).*?(?:Explanation|Description):\s*(.*?)(?:\n\s*\n|$)', re.DOTALL)
        
        matches = finding_pattern.finditer(response)
        for match in matches:
            finding = {
                "issue": match.group(1).strip(),
                "section": match.group(2).strip(),
                "confidence": match.group(3).strip(),
                "explanation": match.group(4).strip(),
                "regulation": "Cross-section issue",
                "finding_type": "contradiction"
            }
            findings.append(finding)
        
        return findings