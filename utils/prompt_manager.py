# utils/prompt_manager.py

import os
import importlib
import importlib.util
import sys
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
        """
        Create a unified analysis prompt with risk-aware capabilities.
        """
        # First try regulation-specific handler if available
        if self.regulation_handler and hasattr(self.regulation_handler, 'create_analysis_prompt'):
            try:
                # Debug log before calling the handler
                print(f"Using {self.regulation_framework} specific handler to create prompt")
                
                # Check if handler supports risk_level parameter
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
        try:
            formatted_regs = []
            
            # Add general regulation context if available
            if self.regulation_context:
                formatted_regs.append(f"REGULATION FRAMEWORK CONTEXT:\n{self.regulation_context}")
            
            # Add common patterns if available (brief summary)
            if self.regulation_patterns:
                pattern_count = self.regulation_patterns.count("Pattern:")
                if pattern_count > 0:
                    formatted_regs.append(f"VIOLATION PATTERNS: {pattern_count} patterns available")
            
            # Add specific regulations with more context
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
            
        except Exception as e:
            print(f"Error in default format_regulations: {e}")
            # Provide a basic fallback format
            return "\n\n".join([f"Regulation: {reg.get('id', 'Unknown')}\n{reg.get('text', '')}" for reg in regulations])
    
    def _create_default_prompt(self, text: str, section: str, regulations: str, 
                            risk_level: str = "unknown") -> str:
        """Default prompt creation with framework-agnostic guidance and simplified format."""
        # Determine analysis depth based on risk level
        analysis_guidance = ""
        if risk_level == "high":
            analysis_guidance = """IMPORTANT: This section has been identified as HIGH RISK. 
Be thorough in your analysis and identify all potential compliance issues. 
Look carefully for any violations, even subtle ones.
"""
        elif risk_level == "medium":
            analysis_guidance = """IMPORTANT: This section has been identified as MEDIUM RISK.
Focus on the most significant compliance issues and be reasonably thorough in your analysis.
"""
        elif risk_level == "low":
            analysis_guidance = """IMPORTANT: This section has been identified as LOW RISK.
Be conservative in flagging issues - only note clear, obvious violations.
Focus on ensuring there are no major compliance gaps.
"""
        
        return f"""You are an expert regulatory compliance auditor. Your task is to analyze this text section for compliance issues and points.

SECTION: {section}
TEXT:
{text}

RELEVANT REGULATIONS:
{regulations}

RISK LEVEL: {risk_level.upper()}

{analysis_guidance}

INSTRUCTIONS:
1. Analyze this section for clear compliance issues based on the regulations provided.
2. For each issue, provide a comprehensive description that explains both what the issue is AND why it violates regulations.
3. Include a direct quote from the document text to support each finding.
4. Format your response EXACTLY as shown in the example below.
5. Focus on clear violations rather than small technical details.

EXAMPLE REQUIRED FORMAT:
COMPLIANCE ISSUES:
1. The document states it will retain data indefinitely, violating storage limitation principles which require data to be kept only as long as necessary for specified purposes. "Retain all customer data indefinitely for long-term trend analysis."
2. Users cannot refuse data collection, violating consent requirements that mandate consent must be freely given and allow users to refuse without detriment. "Users will be required to accept all data collection to use the app."

COMPLIANCE POINTS:
1. The document provides clear user notification about data usage, supporting transparency principles that help users understand how their data is being used. "Our implementation will use a simple banner stating 'By using this site, you accept our terms'."

If no issues are found, write "NO COMPLIANCE ISSUES DETECTED."
If no compliance points are found, write "NO COMPLIANCE POINTS DETECTED."
"""