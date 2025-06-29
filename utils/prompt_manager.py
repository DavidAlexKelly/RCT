# utils/prompt_manager.py - Proper error handling without fallbacks

import os
import importlib.util
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

class PromptManager:
    """Prompt manager with proper error handling and validation."""
    
    def __init__(self, regulation_framework=None, regulation_context=None, regulation_patterns=None):
        """Initialize prompt manager with comprehensive validation."""
        
        # Validate inputs
        if not regulation_framework:
            raise ValueError("regulation_framework cannot be empty")
        
        if not isinstance(regulation_framework, str):
            raise ValueError("regulation_framework must be a string")
        
        self.regulation_framework = regulation_framework.strip()
        self.regulation_context = regulation_context or ""
        self.regulation_patterns = regulation_patterns or ""
        
        # Load regulation handler with proper error handling
        self.regulation_handler = self._load_regulation_handler(self.regulation_framework)
        
        # Validate handler was loaded successfully
        if not self.regulation_handler:
            raise RuntimeError(f"Failed to load regulation handler for {self.regulation_framework}")
        
        # Validate handler has required methods
        required_methods = [
            'create_analysis_prompt',
            'format_regulations',
            'get_classification_terms'
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(self.regulation_handler, method):
                missing_methods.append(method)
        
        if missing_methods:
            raise ValueError(
                f"Regulation handler for {self.regulation_framework} missing required methods: {missing_methods}"
            )
    
    def _load_regulation_handler(self, regulation_framework: str):
        """Load regulation handler with comprehensive error handling."""
        
        # Validate framework name
        if not regulation_framework.replace('_', '').replace('-', '').isalnum():
            raise ValueError(f"Invalid regulation framework name: {regulation_framework}")
        
        # Construct handler path
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        knowledge_base_dir = os.path.join(script_dir, "knowledge_base")
        framework_dir = os.path.join(knowledge_base_dir, regulation_framework)
        handler_path = os.path.join(framework_dir, "handler.py")
        
        # Validate paths exist
        if not os.path.exists(knowledge_base_dir):
            raise FileNotFoundError(f"Knowledge base directory not found: {knowledge_base_dir}")
        
        if not os.path.exists(framework_dir):
            available_frameworks = [
                d for d in os.listdir(knowledge_base_dir) 
                if os.path.isdir(os.path.join(knowledge_base_dir, d)) and d != "__pycache__"
            ]
            raise FileNotFoundError(
                f"Framework directory not found: {framework_dir}\n"
                f"Available frameworks: {available_frameworks}"
            )
        
        if not os.path.exists(handler_path):
            raise FileNotFoundError(f"Handler file not found: {handler_path}")
        
        # Validate handler file is not empty
        if os.path.getsize(handler_path) == 0:
            raise ValueError(f"Handler file is empty: {handler_path}")
        
        try:
            # Import the handler module with validation
            module_name = f"knowledge_base.{regulation_framework}.handler"
            
            # Check if module is already loaded (avoid conflicts)
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            spec = importlib.util.spec_from_file_location(module_name, handler_path)
            if not spec:
                raise ImportError(f"Failed to create module spec for {handler_path}")
            
            if not spec.loader:
                raise ImportError(f"No loader available for {handler_path}")
            
            module = importlib.util.module_from_spec(spec)
            if not module:
                raise ImportError(f"Failed to create module from spec for {handler_path}")
            
            # Execute the module
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Validate the module has RegulationHandler class
            if not hasattr(module, 'RegulationHandler'):
                raise ImportError(f"Handler file missing RegulationHandler class: {handler_path}")
            
            handler_class = getattr(module, 'RegulationHandler')
            
            # Validate it's actually a class
            if not isinstance(handler_class, type):
                raise ImportError(f"RegulationHandler is not a class in {handler_path}")
            
            # Initialize the handler with error handling
            try:
                handler_instance = handler_class(debug=False)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize RegulationHandler: {e}")
            
            # Validate handler instance
            if not handler_instance:
                raise RuntimeError("RegulationHandler initialization returned None")
            
            return handler_instance
            
        except ImportError as e:
            raise ImportError(f"Failed to import regulation handler for {regulation_framework}: {e}")
        except SyntaxError as e:
            raise SyntaxError(f"Syntax error in handler file {handler_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error loading handler for {regulation_framework}: {e}")
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str, 
                             content_indicators: Optional[Dict] = None, 
                             potential_violations: Optional[List] = None,
                             risk_level: str = "unknown") -> str:
        """Create analysis prompt with validation."""
        
        # Validate inputs
        if not text:
            raise ValueError("text cannot be empty")
        
        if not text.strip():
            raise ValueError("text cannot be just whitespace")
        
        if not section:
            raise ValueError("section cannot be empty")
        
        if not regulations:
            raise ValueError("regulations cannot be empty")
        
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        
        if not isinstance(section, str):
            raise ValueError("section must be a string")
        
        if not isinstance(regulations, str):
            raise ValueError("regulations must be a string")
        
        # Validate optional parameters
        if content_indicators is not None and not isinstance(content_indicators, dict):
            raise ValueError("content_indicators must be a dictionary or None")
        
        if potential_violations is not None and not isinstance(potential_violations, list):
            raise ValueError("potential_violations must be a list or None")
        
        if risk_level not in ["unknown", "low", "medium", "high"]:
            raise ValueError("risk_level must be one of: unknown, low, medium, high")
        
        # Validate text length is reasonable
        if len(text) > 50000:  # 50KB limit for individual chunks
            raise ValueError(f"Text too long for analysis: {len(text)} characters (max 50000)")
        
        try:
            prompt = self.regulation_handler.create_analysis_prompt(
                text, section, regulations, content_indicators,
                potential_violations, self.regulation_framework, risk_level
            )
            
            # Validate prompt was created successfully
            if not prompt:
                raise RuntimeError("Handler returned empty prompt")
            
            if not isinstance(prompt, str):
                raise RuntimeError(f"Handler returned invalid prompt type: {type(prompt)}")
            
            if len(prompt.strip()) < 50:
                raise RuntimeError("Handler returned suspiciously short prompt")
            
            return prompt
            
        except Exception as e:
            raise RuntimeError(f"Failed to create analysis prompt: {e}")
    
    def format_regulations(self, regulations: List[Dict[str, Any]]) -> str:
        """Format regulations with validation."""
        
        # Validate input
        if not regulations:
            raise ValueError("regulations list cannot be empty")
        
        if not isinstance(regulations, list):
            raise ValueError("regulations must be a list")
        
        # Validate each regulation
        for i, regulation in enumerate(regulations):
            if not isinstance(regulation, dict):
                raise ValueError(f"Regulation {i+1} must be a dictionary")
            
            # Check for required fields
            if not regulation.get("text", "").strip():
                raise ValueError(f"Regulation {i+1} missing text content")
            
            # Validate text length is reasonable
            reg_text = regulation.get("text", "")
            if len(reg_text) > 10000:  # 10KB limit per regulation
                print(f"Warning: Regulation {i+1} is very long ({len(reg_text)} chars), may be truncated")
        
        try:
            formatted = self.regulation_handler.format_regulations(
                regulations, self.regulation_context, self.regulation_patterns
            )
            
            # Validate formatting result
            if not formatted:
                raise RuntimeError("Handler returned empty formatted regulations")
            
            if not isinstance(formatted, str):
                raise RuntimeError(f"Handler returned invalid format type: {type(formatted)}")
            
            if len(formatted.strip()) < 20:
                raise RuntimeError("Handler returned suspiciously short formatted regulations")
            
            return formatted
            
        except Exception as e:
            raise RuntimeError(f"Failed to format regulations: {e}")
    
    def get_classification_terms(self, term_type: str) -> List[str]:
        """Get classification terms with validation."""
        
        # Validate input
        if not term_type:
            raise ValueError("term_type cannot be empty")
        
        if not isinstance(term_type, str):
            raise ValueError("term_type must be a string")
        
        valid_term_types = [
            "data_terms", 
            "regulatory_keywords", 
            "high_risk_patterns", 
            "priority_keywords"
        ]
        
        if term_type not in valid_term_types:
            raise ValueError(f"Invalid term_type '{term_type}'. Valid types: {valid_term_types}")
        
        # Check if handler has the method
        if not hasattr(self.regulation_handler, 'get_classification_terms'):
            raise RuntimeError("Handler missing get_classification_terms method")
        
        try:
            terms = self.regulation_handler.get_classification_terms(term_type)
            
            # Validate result
            if terms is None:
                raise RuntimeError(f"Handler returned None for term_type '{term_type}'")
            
            if not isinstance(terms, list):
                raise RuntimeError(f"Handler returned invalid type for terms: {type(terms)}")
            
            # Filter out empty terms
            valid_terms = [term for term in terms if term and isinstance(term, str) and term.strip()]
            
            if not valid_terms:
                raise ValueError(f"No valid {term_type} found for framework {self.regulation_framework}")
            
            return valid_terms
            
        except Exception as e:
            raise RuntimeError(f"Failed to get classification terms for '{term_type}': {e}")
    
    def validate_handler(self) -> Dict[str, Any]:
        """Validate the loaded handler comprehensively."""
        
        validation_result = {
            "framework": self.regulation_framework,
            "handler_loaded": self.regulation_handler is not None,
            "required_methods": [],
            "missing_methods": [],
            "term_types": {},
            "errors": [],
            "warnings": []
        }
        
        if not self.regulation_handler:
            validation_result["errors"].append("No handler loaded")
            return validation_result
        
        # Check required methods
        required_methods = [
            'create_analysis_prompt',
            'format_regulations', 
            'get_classification_terms',
            'extract_content_indicators'
        ]
        
        for method in required_methods:
            if hasattr(self.regulation_handler, method):
                validation_result["required_methods"].append(method)
            else:
                validation_result["missing_methods"].append(method)
        
        # Test classification terms
        term_types = ["data_terms", "regulatory_keywords", "high_risk_patterns", "priority_keywords"]
        
        for term_type in term_types:
            try:
                terms = self.get_classification_terms(term_type)
                validation_result["term_types"][term_type] = {
                    "count": len(terms),
                    "sample": terms[:3] if terms else []
                }
            except Exception as e:
                validation_result["term_types"][term_type] = {
                    "error": str(e)
                }
                validation_result["errors"].append(f"Failed to load {term_type}: {e}")
        
        # Test prompt creation (basic test)
        try:
            test_prompt = self.create_analysis_prompt(
                "Test document text", 
                "Test section", 
                "Test regulation: Sample regulation text"
            )
            if len(test_prompt) < 100:
                validation_result["warnings"].append("Test prompt seems too short")
        except Exception as e:
            validation_result["errors"].append(f"Prompt creation test failed: {e}")
        
        return validation_result