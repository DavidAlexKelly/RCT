# utils/llm_handler.py

from typing import List, Dict, Any
import importlib
import os

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
        self.regulation_handler = None
    
    def set_regulation_context(self, context_text, patterns_text, regulation_framework=None):
        """Set regulation-specific context information and load appropriate handler."""
        self.regulation_context = context_text.strip() if context_text else ""
        self.regulation_patterns = patterns_text.strip() if patterns_text else ""
        self.regulation_framework = regulation_framework
        
        # Load regulation-specific handler
        self.regulation_handler = self._load_regulation_handler(regulation_framework)
        
        if self.debug:
            print(f"Set regulation framework to: {regulation_framework}")
            print(f"Regulation context length: {len(self.regulation_context)} chars")
            print(f"Regulation patterns length: {len(self.regulation_patterns)} chars")
            if self.regulation_handler:
                print(f"Loaded regulation-specific handler for: {regulation_framework}")
            else:
                print(f"No regulation-specific handler found for: {regulation_framework}")
    
    def _load_regulation_handler(self, regulation_framework):
        """Load regulation-specific handler."""
        if not regulation_framework:
            return None
        
        # Look for handler module in knowledge_base
        handler_path = f"knowledge_base/{regulation_framework}/handler.py"
        if not os.path.exists(handler_path):
            if self.debug:
                print(f"No handler found at path: {handler_path}")
            return None
        
        try:
            # Dynamically import the module
            module_name = f"knowledge_base.{regulation_framework}.handler"
            module = importlib.import_module(module_name)
            
            # Create handler instance
            if hasattr(module, 'RegulationHandler'):
                handler = module.RegulationHandler(self.debug)
                return handler
            else:
                if self.debug:
                    print(f"Module does not contain RegulationHandler class: {module_name}")
        except Exception as e:
            if self.debug:
                print(f"Error loading regulation handler: {e}")
        
        return None
    
    def get_batch_size(self):
        """Return the recommended batch size for this model."""
        return self.model_config.get("batch_size", 1)
    
    def analyze_compliance_with_metadata(self, document_chunk: Dict[str, Any], regulations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze document chunk for compliance issues with metadata.
        
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
        
        # Extract content indicators using the regulation handler
        content_indicators = {}
        if self.regulation_handler and hasattr(self.regulation_handler, 'extract_content_indicators'):
            content_indicators = self.regulation_handler.extract_content_indicators(doc_text)
        
        # Pre-scan for potential violations using the regulation handler
        potential_violations = []
        if self.regulation_handler and hasattr(self.regulation_handler, 'extract_potential_violations'):
            potential_violations = self.regulation_handler.extract_potential_violations(doc_text, self.regulation_patterns)
            
        if potential_violations and self.debug:
            print(f"Pre-scan found {len(potential_violations)} potential violations")
            for v in potential_violations[:3]:  # Show first 3 examples
                print(f"  - '{v['pattern']}' indicator: '{v['indicator']}'")
        
        # Format regulations for the prompt using the regulation handler
        formatted_regulations = ""
        if self.regulation_handler and hasattr(self.regulation_handler, 'format_regulations'):
            formatted_regulations = self.regulation_handler.format_regulations(
                regulations, self.regulation_context, self.regulation_patterns
            )
        else:
            # Use default regulation formatting if no handler available
            formatted_regulations = self._format_regulations_default(regulations)
        
        # Generate prompt using the regulation handler
        prompt = ""
        if self.regulation_handler and hasattr(self.regulation_handler, 'create_analysis_prompt'):
            prompt = self.regulation_handler.create_analysis_prompt(
                doc_text, 
                chunk_position, 
                formatted_regulations, 
                content_indicators,
                potential_violations,
                self.regulation_framework
            )
        else:
            # Use default prompt creation if no handler available
            from config.prompts import get_prompt_for_regulation
            prompt_template = get_prompt_for_regulation(self.regulation_framework, "analyze_compliance")
            if prompt_template:
                try:
                    prompt = prompt_template.format(
                        section=chunk_position,
                        text=doc_text,
                        regulations=formatted_regulations,
                        **content_indicators
                    )
                except KeyError as e:
                    print(f"Error formatting prompt: {e}")
                    prompt = self._create_default_prompt(doc_text, chunk_position, formatted_regulations)
            else:
                prompt = self._create_default_prompt(doc_text, chunk_position, formatted_regulations)
        
        # Get response from LLM
        response = self.llm.invoke(prompt)
        
        if self.debug:
            print(f"LLM Response (first 200 chars): {response[:200]}...")
        
        # Process the response to extract issues and metadata
        result = {}
        if self.regulation_handler and hasattr(self.regulation_handler, 'extract_json_from_response'):
            result = self.regulation_handler.extract_json_from_response(response)
        else:
            import json
            import re
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # Simple regex extraction
                issues = []
                matches = re.finditer(r'"issue"\s*:\s*"(.*?)"', response)
                for match in matches:
                    issues.append({"issue": match.group(1)})
                result = {"issues": issues}
        
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
    
    def _format_regulations_default(self, regulations: List[Dict]) -> str:
        """Default implementation to format regulations."""
        formatted_regs = []
        
        # Add general regulation context if available
        if self.regulation_context:
            formatted_regs.append(f"REGULATION FRAMEWORK CONTEXT:\n{self.regulation_context}")
        
        # Add common patterns if available
        if self.regulation_patterns:
            formatted_regs.append("COMMON COMPLIANCE PATTERNS AVAILABLE")
        
        # Add specific regulations
        for i, reg in enumerate(regulations):
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", f"Regulation {i+1}")
            reg_title = reg.get("title", "")
            
            # Include regulation ID and title if available
            formatted_reg = f"REGULATION {i+1}: {reg_id}"
            if reg_title:
                formatted_reg += f" - {reg_title}"
                
            formatted_reg += f"\n{reg_text}"
            
            formatted_regs.append(formatted_reg)
            
        return "\n\n".join(formatted_regs)
    
    def _create_default_prompt(self, text, section, regulations):
        """Default prompt creation if no regulation handler is available."""
        return f"""You are an expert in regulatory compliance analysis. Analyze this section for compliance issues.

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
      "regulation": "Specific regulation violated",
      "confidence": "High/Medium/Low",
      "explanation": "Why this violates the regulation",
      "citation": "Direct quote from text showing the violation"
    }}
  ]
}}

If no issues are found, return an empty issues array.
"""