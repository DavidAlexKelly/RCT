# utils/prompt_manager.py

import os
import importlib
import importlib.util
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

class PromptManager:
    """Prompt manager with array-based response system."""
    
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
        
        # Get the script directory
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Add script directory to path if not already there
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        
        # Look for handler module in knowledge_base
        handler_path = os.path.join(script_dir, "knowledge_base", regulation_framework, "handler.py")
        if not os.path.exists(handler_path):
            print(f"No handler found at {handler_path}")
            return None
        
        try:
            # Dynamically import the module using importlib.util
            module_name = f"knowledge_base.{regulation_framework}.handler"
            
            # Use importlib.util.spec_from_file_location for reliable import
            spec = importlib.util.spec_from_file_location(module_name, handler_path)
            if spec is None:
                print(f"Could not create spec for {module_name}")
                return None
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Create handler instance
            if hasattr(module, 'RegulationHandler'):
                handler = module.RegulationHandler(debug=False)
                print(f"Successfully loaded {regulation_framework} regulation handler")
                return handler
            else:
                print(f"Warning: {regulation_framework} handler module found but no RegulationHandler class")
                
        except Exception as e:
            print(f"Error loading regulation handler for {regulation_framework}: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str, 
                           content_indicators: Optional[Dict] = None, 
                           potential_violations: Optional[List] = None,
                           risk_level: str = "unknown") -> str:
        """Create a prompt that requests array format."""
        
        # Try regulation-specific handler first
        if self.regulation_handler and hasattr(self.regulation_handler, 'create_analysis_prompt'):
            try:
                return self.regulation_handler.create_analysis_prompt(
                    text, section, regulations, content_indicators,
                    potential_violations, self.regulation_framework, risk_level
                )
            except Exception as e:
                print(f"Error using regulation handler for prompt creation: {e}")
                print("Falling back to default prompt")
                
        # Otherwise use simple default prompt
        return self._create_simple_prompt(text, section, regulations, risk_level)
    
    def format_regulations(self, regulations: List[Dict[str, Any]]) -> str:
        """Format regulations for inclusion in a prompt."""
        if self.regulation_handler and hasattr(self.regulation_handler, 'format_regulations'):
            try:
                return self.regulation_handler.format_regulations(
                    regulations, self.regulation_context, self.regulation_patterns
                )
            except Exception as e:
                print(f"Error using regulation handler for formatting: {e}")
        
        # Fall back to simple formatting
        return self._format_regulations_simple(regulations)
    
    def _format_regulations_simple(self, regulations: List[Dict]) -> str:
        """Simple implementation to format regulations."""
        formatted_regs = []
        
        # Add general regulation context if available (truncated)
        if self.regulation_context:
            context_preview = self.regulation_context[:300] + "..." if len(self.regulation_context) > 300 else self.regulation_context
            formatted_regs.append(f"CONTEXT:\n{context_preview}")
        
        # Add specific regulations (simplified)
        for i, reg in enumerate(regulations):
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", f"Regulation {i+1}")
            
            # Truncate long regulation text for better prompt efficiency
            if len(reg_text) > 400:
                reg_text = reg_text[:400] + "..."
            
            formatted_reg = f"{reg_id}:\n{reg_text}"
            formatted_regs.append(formatted_reg)
        
        return "\n\n".join(formatted_regs)
    
    def _create_simple_prompt(self, text: str, section: str, regulations: str, 
                            risk_level: str = "unknown") -> str:
        """Simple prompt creation that requests array format."""
        
        # Simple risk guidance
        focus = ""
        if risk_level == "high":
            focus = "This section appears high-risk - be thorough in finding violations."
        elif risk_level == "low":
            focus = "This section appears low-risk - only flag clear, obvious violations."
        
        return f"""Analyze this document section for compliance violations.

SECTION: {section}
DOCUMENT TEXT:
{text}

RELEVANT REGULATIONS:
{regulations}

{focus}

TASK: Find compliance violations and return them as a JSON array.

RESPONSE FORMAT - Return ONLY a JSON array, nothing else:
[
["Clear description of violation", "Regulation reference", "Exact quote from document"],
["Another violation description", "Another regulation", "Another exact quote"]
]

REQUIREMENTS:
- Each violation = [description, regulation, exact_document_quote]
- Only quote text that appears EXACTLY in the document above
- Keep descriptions clear and concise
- If no violations found, return: []

EXAMPLES:
["Data stored without time limits", "Article 5", "data will be retained indefinitely"]
["No user consent mechanism", "Article 7", "users must accept all terms"]
["Inadequate security measures", "Article 32", "basic password protection only"]
"""