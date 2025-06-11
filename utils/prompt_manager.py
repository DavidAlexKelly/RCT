# utils/prompt_manager.py

import os
import importlib
from typing import Dict, Any, List, Optional
from pathlib import Path

class PromptManager:
    """Centralized manager for all prompt generation."""
    
    def __init__(self, regulation_framework=None, regulation_context=None, regulation_patterns=None):
        """Initialize the prompt manager."""
        self.regulation_framework = regulation_framework
        self.regulation_context = regulation_context or ""
        self.regulation_patterns = regulation_patterns or ""
        
        # Try to load regulation-specific handler
        self.regulation_handler = self._load_regulation_handler(regulation_framework)
        
    def _load_regulation_handler(self, regulation_framework):
        """Load regulation-specific handler."""
        if not regulation_framework:
            return None
        
        # Look for handler module in knowledge_base
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        handler_path = os.path.join(script_dir, "knowledge_base", regulation_framework, "handler.py")
        if not os.path.exists(handler_path):
            return None
        
        try:
            # Dynamically import the module
            module_name = f"knowledge_base.{regulation_framework}.handler"
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                # Alternative approach for relative imports
                import sys
                sys.path.append(script_dir)
                module_name = f"knowledge_base.{regulation_framework}.handler"
            
            module = importlib.import_module(module_name)
            
            # Create handler instance
            if hasattr(module, 'RegulationHandler'):
                handler = module.RegulationHandler(debug=False)
                return handler
        except Exception as e:
            print(f"Error loading regulation handler: {e}")
        
        return None
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str, 
                           content_indicators: Optional[Dict] = None, 
                           potential_violations: Optional[List] = None,
                           risk_level: str = "unknown") -> str:
        """
        Create a unified analysis prompt with risk-aware capabilities.
        """
        # First try regulation-specific handler if available
        if self.regulation_handler and hasattr(self.regulation_handler, 'create_analysis_prompt'):
            try:
                # Debug log before calling the handler
                print(f"Using {self.regulation_framework} specific handler to create prompt")
                
                # Check if handler supports risk_level
                import inspect
                handler_params = inspect.signature(self.regulation_handler.create_analysis_prompt).parameters
                
                if 'risk_level' in handler_params:
                    return self.regulation_handler.create_analysis_prompt(
                        text, section, regulations, content_indicators,
                        potential_violations, self.regulation_framework, risk_level
                    )
                else:
                    # Fall back to original signature
                    return self.regulation_handler.create_analysis_prompt(
                        text, section, regulations, content_indicators,
                        potential_violations, self.regulation_framework
                    )
            except Exception as e:
                print(f"Error using regulation handler for prompt creation: {e}")
                print("Falling back to default prompt")
                
        # Otherwise use default prompt generation
        print(f"Using framework-agnostic default prompt for {self.regulation_framework}")
        return self._create_default_prompt(text, section, regulations, risk_level)
    
    def format_regulations(self, regulations: List[Dict[str, Any]]) -> str:
        """
        Format regulations for inclusion in a prompt.
        
        Args:
            regulations: List of regulation dictionaries
            
        Returns:
            Formatted regulations text
        """
        if self.regulation_handler and hasattr(self.regulation_handler, 'format_regulations'):
            try:
                return self.regulation_handler.format_regulations(
                    regulations, self.regulation_context, self.regulation_patterns
                )
            except Exception as e:
                print(f"Error using regulation handler for formatting: {e}")
        
        # Fall back to default formatting
        return self._format_regulations_default(regulations)
    
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
    
    def _create_default_prompt(self, text: str, section: str, regulations: str, 
                            risk_level: str = "unknown") -> str:
        """Default prompt creation with framework-agnostic guidance and simplified format."""
        # Determine analysis depth based on risk level
        analysis_depth = "comprehensive"
        if risk_level == "low":
            analysis_depth = "quick"
        elif risk_level == "medium":
            analysis_depth = "standard"
        
        return f"""You are an expert regulatory compliance auditor. Your task is to analyze this text section for compliance issues and points.

    SECTION: {section}
    TEXT:
    {text}

    RELEVANT REGULATIONS:
    {regulations}

    RISK LEVEL: {risk_level.upper()}

    INSTRUCTIONS:
    1. Analyze this section for clear compliance issues based on the regulations provided.
    2. For each issue, provide a comprehensive description that explains both what the issue is AND why it violates regulations.
    3. Include a direct quote from the document text to support each finding.
    4. Format your response EXACTLY as shown in the example below.
    5. Focus on clear violations rather than small technical details.

    EXAMPLE REQUIRED FORMAT:
    ```
    COMPLIANCE ISSUES:
    1. The document states it will retain data indefinitely, violating storage limitation principles which require data to be kept only as long as necessary for specified purposes. "Retain all customer data indefinitely for long-term trend analysis."

    2. Users cannot refuse data collection, violating consent requirements that mandate consent must be freely given and allow users to refuse without detriment. "Users will be required to accept all data collection to use the app."

    COMPLIANCE POINTS:
    1. The document provides clear user notification about data usage, supporting transparency principles that help users understand how their data is being used. "Our implementation will use a simple banner stating 'By using this site, you accept our terms'."
    ```

    If no issues are found, write "NO COMPLIANCE ISSUES DETECTED."
    If no compliance points are found, write "NO COMPLIANCE POINTS DETECTED."
"""
