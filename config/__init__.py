# config/__init__.py
"""
Configuration for the compliance analysis tool.
"""

from .models import MODELS, DEFAULT_MODEL
from .settings import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP

def get_prompt_for_regulation(regulation_framework, prompt_type):
    """Simple prompt function."""
    # Simple default prompts
    if prompt_type == "analyze_compliance":
        return "Analyze this text for compliance with {regulation_framework} requirements."
    elif prompt_type == "contradiction_analysis":
        return "Analyze for contradictions across sections."
    return ""