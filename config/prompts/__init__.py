# config/prompts/__init__.py

"""
Import and manage regulation-specific prompts.
"""

from .base_prompts import ANALYZE_COMPLIANCE_PROMPT, CONTRADICTION_ANALYSIS_PROMPT

# Dictionary mapping regulation frameworks to their respective prompt modules
REGULATION_PROMPT_MODULES = {
    "gdpr": "config.prompts.gdpr_prompts",
    "hipaa": "config.prompts.hipaa_prompts",
    "ccpa": "config.prompts.ccpa_prompts"
}

def get_prompt_for_regulation(regulation_framework, prompt_type):
    """
    Get the appropriate prompt for a specific regulation and prompt type.
    
    Args:
        regulation_framework: The regulation framework name (e.g., "gdpr", "hipaa")
        prompt_type: The type of prompt (e.g., "analyze_compliance", "contradiction_analysis")
        
    Returns:
        The prompt template string for the specified regulation and prompt type
    """
    # Default prompts
    default_prompts = {
        "analyze_compliance": ANALYZE_COMPLIANCE_PROMPT,
        "contradiction_analysis": CONTRADICTION_ANALYSIS_PROMPT
    }
    
    # Check if we have a module for this regulation
    if regulation_framework in REGULATION_PROMPT_MODULES:
        try:
            # Import the module dynamically
            import importlib
            module_name = REGULATION_PROMPT_MODULES[regulation_framework]
            module = importlib.import_module(module_name)
            
            # Get the appropriate prompt getter function
            if prompt_type == "analyze_compliance":
                if hasattr(module, "get_analyze_compliance_prompt"):
                    return module.get_analyze_compliance_prompt()
            elif prompt_type == "contradiction_analysis":
                if hasattr(module, "get_contradiction_analysis_prompt"):
                    return module.get_contradiction_analysis_prompt()
        except ImportError as e:
            print(f"Warning: Could not import regulation-specific prompts: {e}")
    
    # Fall back to default prompts
    return default_prompts.get(prompt_type, "")