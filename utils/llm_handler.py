from typing import List, Dict, Any
import json
import re

# Import configuration
from config import MODELS, DEFAULT_MODEL

# Import Ollama
from langchain_ollama import OllamaLLM as Ollama

class LLMHandler:
    def __init__(self, model_key=DEFAULT_MODEL, debug=False):
        """
        Initialize the LLM handler with a model from the configuration.
        
        Args:
            model_key: Key from the MODELS dict ('small', 'medium', 'large') or full model name
            debug: Whether to print detailed debug information
        """
        self.debug = debug
        
        # Find the correct model key
        self.model_key = model_key
        
        if model_key not in MODELS:
            for key, model_config in MODELS.items():
                if model_config["name"] == model_key:
                    self.model_key = key
                    break
        
        # Get model configuration or use default if not found
        self.model_config = MODELS.get(self.model_key, MODELS[DEFAULT_MODEL])
        
        # Initialize the model
        self.llm = Ollama(
            model=self.model_config["name"],
            temperature=self.model_config.get("temperature", 0.1)
        )
        print(f"Initialized LLM with model: {self.model_config['name']} ({self.model_key})")
        
        # Add context fields
        self.regulation_context = ""
        self.regulation_patterns = ""
        self.regulation_framework = None
    
    def set_regulation_context(self, context_text, patterns_text, regulation_framework=None):
        """Set regulation-specific context information."""
        self.regulation_context = context_text.strip() if context_text else ""
        self.regulation_patterns = patterns_text.strip() if patterns_text else ""
        self.regulation_framework = regulation_framework
    
    def get_batch_size(self):
        """Return the recommended batch size for this model."""
        return self.model_config.get("batch_size", 1)
    
    def extract_json_from_response(self, response):
        """Extract JSON from an LLM response with improved reliability."""
        # First try to parse the entire response as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to find a JSON array or object
        json_patterns = [
            # Look for JSON arrays
            (r'\[\s*\{.*\}\s*\]', False),
            # Look for JSON arrays with single quotes
            (r'\[\s*\{.*\}\s*\]', True),
            # Look for JSON objects
            (r'\{\s*".*"\s*:.*\}', False),
            # Look for JSON objects with single quotes
            (r'\{\s*\'.*\'\s*:.*\}', True)
        ]
        
        for pattern, replace_quotes in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                json_str = match.group(0)
                if replace_quotes:
                    json_str = json_str.replace("'", '"')
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
        
        # If we can't find valid JSON, extract structured data
        issues = self._extract_structured_issues(response)
        if issues:
            return {"issues": issues}
        
        # If all else fails, return an empty dict
        return {"issues": []}
    
    def _extract_structured_issues(self, text):
        """Extract issues from structured text using regex patterns."""
        issues = []
        
        # Look for patterns like "Issue: Description" or "Issue 1: Description"
        issue_pattern = re.compile(r'(?:Issue\s*\d*|Finding\s*\d*|Problem\s*\d*):\s*(.*?)(?:\n|$).*?(?:Regulation|Article):\s*(.*?)(?:\n|$).*?(?:Confidence|Severity):\s*(.*?)(?:\n|$).*?(?:Explanation|Reason|Description):\s*(.*?)(?:\n\s*\n|$)', re.DOTALL)
        
        matches = issue_pattern.finditer(text)
        for match in matches:
            issue = {
                "issue": match.group(1).strip(),
                "regulation": match.group(2).strip(),
                "confidence": match.group(3).strip(),
                "explanation": match.group(4).strip()
            }
            issues.append(issue)
        
        return issues
    
    def analyze_compliance_with_metadata(self, document_chunk: Dict[str, Any], regulations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze document chunk for compliance issues with simplified metadata.
        
        Args:
            document_chunk: Dictionary containing the chunk text and metadata
            regulations: List of relevant regulations to check against
            
        Returns:
            Dictionary with issues found
        """
        # Extract the document text and chunk info
        doc_text = document_chunk.get("text", "")
        chunk_position = document_chunk.get("position", "Unknown")
        
        if self.debug:
            print(f"\nAnalyzing chunk: '{chunk_position}'")
            print(f"Text (first 50 chars): '{doc_text[:50]}...'")
        
        # Format regulations for the prompt
        reg_texts = self._format_regulations(regulations)
        
        # Generate prompt
        prompt = self._create_analysis_prompt(doc_text, chunk_position, reg_texts)
        
        # Get response from LLM
        response = self.llm.invoke(prompt)
        
        if self.debug:
            print(f"LLM Response (first 200 chars): {response[:200]}...")
        
        # Process the response to extract issues and metadata
        result = self.extract_json_from_response(response)
        
        # Ensure we have the expected structure
        if not isinstance(result, dict):
            result = {"issues": []}
        
        if "issues" not in result:
            result["issues"] = []
            
        # Add position information to the result
        result["position"] = chunk_position
        result["text"] = doc_text
        
        # Add section information to each issue
        for issue in result.get("issues", []):
            issue["section"] = chunk_position
        
        return result
    
    def _create_analysis_prompt(self, text, section, regulations):
        """Create a prompt for compliance analysis."""
        # Simple prompt
        prompt = f"""You are an expert in regulatory compliance analysis. Analyze this section for compliance issues.

SECTION: {section}
TEXT:
{text}

RELEVANT REGULATIONS:
{regulations}

ANALYSIS GUIDELINES:
1. Focus on CLEAR compliance issues based on the provided regulations
2. Check for missing required information
3. Identify inconsistencies with regulatory requirements
4. Note vague language that could create compliance risks
5. Flag potential policy contradictions

Return your findings as JSON with this format:
{{
  "issues": [
    {{
      "issue": "Description of the compliance issue",
      "regulation": "Specific regulation violated (e.g., 'Article 5(1)(e)')",
      "confidence": "High/Medium/Low",
      "explanation": "Why this violates the regulation"
    }}
  ]
}}

If no issues are found, return an empty issues array.
"""
        return prompt
    
    def _format_regulations(self, regulations: List[Dict]) -> str:
        """Format regulations with additional context for inclusion in the prompt."""
        formatted_regs = []
        
        # Add general regulation context if available
        if self.regulation_context:
            formatted_regs.append(f"REGULATION FRAMEWORK CONTEXT:\n{self.regulation_context}")
        
        # Add common patterns if available
        if self.regulation_patterns:
            formatted_regs.append(f"COMMON COMPLIANCE PATTERNS:\n{self.regulation_patterns}")
        
        # Add specific regulations
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