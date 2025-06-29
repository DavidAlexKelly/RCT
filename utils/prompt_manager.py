# utils/prompt_manager.py - SIMPLIFIED

import os
import importlib.util
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

class PromptManager:
    """Simple prompt manager that uses regulation handlers."""
    
    def __init__(self, regulation_framework=None, regulation_context=None, regulation_patterns=None):
        self.regulation_framework = regulation_framework
        self.regulation_context = regulation_context or ""
        self.regulation_patterns = regulation_patterns or ""
        
        # Load regulation handler (required)
        self.regulation_handler = self._load_regulation_handler(regulation_framework)
        
    def _load_regulation_handler(self, regulation_framework):
        """Load regulation handler - no fallbacks."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        handler_path = os.path.join(script_dir, "knowledge_base", regulation_framework, "handler.py")
        
        # Import the handler module
        module_name = f"knowledge_base.{regulation_framework}.handler"
        spec = importlib.util.spec_from_file_location(module_name, handler_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        return module.RegulationHandler(debug=False)
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str, 
                           content_indicators: Optional[Dict] = None, 
                           potential_violations: Optional[List] = None,
                           risk_level: str = "unknown") -> str:
        """Create analysis prompt using handler."""
        return self.regulation_handler.create_analysis_prompt(
            text, section, regulations, content_indicators,
            potential_violations, self.regulation_framework, risk_level
        )
    
    def format_regulations(self, regulations: List[Dict[str, Any]]) -> str:
        """Format regulations using handler."""
        return self.regulation_handler.format_regulations(
            regulations, self.regulation_context, self.regulation_patterns
        )