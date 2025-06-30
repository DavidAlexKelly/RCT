from dataclasses import dataclass
from typing import Dict, Any

CONFIG_VERSION = "3.1.0"

# Model configurations
MODELS = {
    "small": {
        "key": "small",
        "name": "llama3:8b",
        "temperature": 0.1,
        "description": "Fast model suitable for most analyses"
    },
    "medium": {
        "key": "medium", 
        "name": "llama3:70b-instruct-q4_0",
        "temperature": 0.1,
        "description": "Balanced model with improved accuracy"
    },
    "large": {
        "key": "large",
        "name": "llama3:70b-instruct",
        "temperature": 0.1,
        "description": "High-accuracy model (requires 32GB+ RAM)"
    }
}

DEFAULT_MODEL = "small"

# Core configuration
@dataclass
class Config:
    # Document processing
    chunk_size: int = 800
    chunk_overlap: int = 100
    chunking_method: str = "smart"
    max_chunks_per_document: int = 50
    
    # RAG settings
    rag_articles: int = 5
    max_prompt_length: int = 8000
    
    # Progressive analysis
    topic_threshold: float = 2.0  # Number of regulated topics needed

# Global config instance
config = Config()

# Analysis presets
PRESETS = {
    'speed': {
        'rag_articles': 3,
        'topic_threshold': 3.0,  # Need 3+ topics (very specific sections)
        'chunk_size': 600,
        'chunk_overlap': 50,
        'chunking_method': 'simple'
    },
    'balanced': {
        'rag_articles': 5,
        'topic_threshold': 2.0,  # Need 2+ topics (standard)
        'chunk_size': 800,
        'chunk_overlap': 100,
        'chunking_method': 'smart'
    },
    'thorough': {
        'rag_articles': 8,
        'topic_threshold': 1.0,  # Any regulated topic gets analyzed
        'chunk_size': 1000,
        'chunk_overlap': 150,
        'chunking_method': 'smart'
    }
}

def apply_preset(preset_name: str) -> Dict[str, Any]:
    """Apply a performance preset to global config."""
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PRESETS.keys())}")
    
    settings = PRESETS[preset_name]
    for key, value in settings.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return settings

def get_model_config(model_key: str = None) -> Dict[str, Any]:
    """Get model configuration."""
    model_key = model_key or DEFAULT_MODEL
    if model_key not in MODELS:
        raise ValueError(f"Unknown model: {model_key}. Available: {list(MODELS.keys())}")
    return MODELS[model_key].copy()