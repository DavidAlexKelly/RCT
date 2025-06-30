import os
import sys
import importlib.util
from pathlib import Path
from typing import Dict, Any

class PromptManager:
    """Simplified prompt manager that loads framework handlers."""
    
    def __init__(self, regulation_framework=None):
        """Initialize prompt manager and load framework handler."""
        
        assert regulation_framework, "regulation_framework required"
        
        self.regulation_framework = regulation_framework.strip()
        
        # Load regulation handler
        self.handler = self._load_regulation_handler(self.regulation_framework)
        assert self.handler, f"Failed to load handler for {self.regulation_framework}"
    
    def _load_regulation_handler(self, regulation_framework: str):
        """Load framework-specific handler module."""
        
        # Construct paths
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        handler_path = os.path.join(script_dir, "knowledge_base", regulation_framework, "handler.py")
        
        if not os.path.exists(handler_path):
            raise FileNotFoundError(f"Handler not found: {handler_path}")
        
        if os.path.getsize(handler_path) == 0:
            raise ValueError(f"Empty handler file: {handler_path}")
        
        try:
            # Import handler module
            module_name = f"knowledge_base.{regulation_framework}.handler"
            
            # Remove if already loaded to avoid conflicts
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            spec = importlib.util.spec_from_file_location(module_name, handler_path)
            if not spec or not spec.loader:
                raise ImportError(f"Failed to create spec for {handler_path}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Get handler class
            if not hasattr(module, 'RegulationHandler'):
                raise AttributeError(f"No RegulationHandler class in {handler_path}")
            
            handler_class = getattr(module, 'RegulationHandler')
            if not isinstance(handler_class, type):
                raise TypeError("RegulationHandler must be a class")
            
            # Initialize handler
            return handler_class(debug=False)
            
        except Exception as e:
            raise RuntimeError(f"Failed to load handler for {regulation_framework}: {e}")
    
    def validate_handler(self) -> Dict[str, Any]:
        """Validate loaded handler has required methods."""
        
        result = {
            "framework": self.regulation_framework,
            "handler_loaded": self.handler is not None,
            "errors": [],
            "warnings": []
        }
        
        if not self.handler:
            result["errors"].append("No handler loaded")
            return result
        
        # Check required methods
        required_methods = [
            'calculate_risk_score',
            'should_analyze', 
            'create_prompt',
            'parse_response'
        ]
        
        for method_name in required_methods:
            if not hasattr(self.handler, method_name):
                result["errors"].append(f"Missing method: {method_name}")
            elif not callable(getattr(self.handler, method_name)):
                result["errors"].append(f"Method not callable: {method_name}")
        
        # Check handler properties
        if not hasattr(self.handler, 'risk_keywords'):
            result["errors"].append("Missing risk_keywords attribute")
        elif not isinstance(self.handler.risk_keywords, list):
            result["errors"].append("risk_keywords must be a list")
        elif len(self.handler.risk_keywords) == 0:
            result["warnings"].append("No risk keywords defined")
        
        if not hasattr(self.handler, 'name'):
            result["warnings"].append("Handler has no name attribute")
        
        # Test basic functionality
        try:
            test_score = self.handler.calculate_risk_score("test text")
            if not isinstance(test_score, (int, float)):
                result["errors"].append("calculate_risk_score must return a number")
        except Exception as e:
            result["errors"].append(f"calculate_risk_score test failed: {e}")
        
        try:
            test_should = self.handler.should_analyze("test text")
            if not isinstance(test_should, bool):
                result["errors"].append("should_analyze must return a boolean")
        except Exception as e:
            result["errors"].append(f"should_analyze test failed: {e}")
        
        return result