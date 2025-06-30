import os
from dataclasses import dataclass
from typing import Dict, Any

CONFIG_VERSION = "3.1.0"

# Application settings
DEFAULT_PORT = int(os.environ.get('STREAMLIT_PORT', 8501))
DEFAULT_HOST = os.environ.get('STREAMLIT_HOST', 'localhost')
MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', 50))

# Model configurations
MODELS = {
    "small": {
        "key": "small",
        "name": "llama3:8b",
        "temperature": 0.1,
        "description": "Fast model suitable for most analyses",
        "min_ram_gb": 8
    },
    "medium": {
        "key": "medium", 
        "name": "llama3:70b-instruct-q4_0",
        "temperature": 0.1,
        "description": "Balanced model with improved accuracy",
        "min_ram_gb": 16
    },
    "large": {
        "key": "large",
        "name": "llama3:70b-instruct",
        "temperature": 0.1,
        "description": "High-accuracy model (requires 32GB+ RAM)",
        "min_ram_gb": 32
    }
}

DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', "small")

# Validate default model
if DEFAULT_MODEL not in MODELS:
    print(f"Warning: Invalid DEFAULT_MODEL '{DEFAULT_MODEL}', using 'small'")
    DEFAULT_MODEL = "small"

# Core configuration
@dataclass
class Config:
    """Core configuration settings for the analyser."""
    
    # Document processing
    chunk_size: int = int(os.environ.get('CHUNK_SIZE', 800))
    chunk_overlap: int = int(os.environ.get('CHUNK_OVERLAP', 100))
    chunking_method: str = os.environ.get('CHUNKING_METHOD', "smart")
    max_chunks_per_document: int = int(os.environ.get('MAX_CHUNKS', 50))
    
    # RAG settings
    rag_articles: int = int(os.environ.get('RAG_ARTICLES', 5))
    max_prompt_length: int = int(os.environ.get('MAX_PROMPT_LENGTH', 8000))
    
    # Progressive analysis
    topic_threshold: float = float(os.environ.get('TOPIC_THRESHOLD', 2.0))
    
    # Application limits
    max_file_size_mb: int = MAX_FILE_SIZE_MB
    
    def __post_init__(self):
        """Validate configuration values."""
        if not (200 <= self.chunk_size <= 5000):
            raise ValueError(f"chunk_size must be 200-5000, got {self.chunk_size}")
        
        if not (0 <= self.chunk_overlap < self.chunk_size):
            raise ValueError(f"chunk_overlap must be 0 to {self.chunk_size-1}, got {self.chunk_overlap}")
        
        if self.chunking_method not in ["smart", "paragraph", "sentence", "simple"]:
            raise ValueError(f"Invalid chunking_method: {self.chunking_method}")
        
        if not (1 <= self.rag_articles <= 20):
            raise ValueError(f"rag_articles must be 1-20, got {self.rag_articles}")
        
        if not (0.1 <= self.topic_threshold <= 10.0):
            raise ValueError(f"topic_threshold must be 0.1-10.0, got {self.topic_threshold}")

# Global config instance
try:
    config = Config()
except ValueError as e:
    print(f"Configuration error: {e}")
    print("Using default values...")
    config = Config(
        chunk_size=800,
        chunk_overlap=100,
        chunking_method="smart",
        max_chunks_per_document=50,
        rag_articles=5,
        max_prompt_length=8000,
        topic_threshold=2.0,
        max_file_size_mb=50
    )

# Analysis presets
PRESETS = {
    'speed': {
        'rag_articles': 3,
        'topic_threshold': 3.0,  # Need 3+ topics (very specific sections)
        'chunk_size': 600,
        'chunk_overlap': 50,
        'chunking_method': 'simple',
        'description': 'Fast analysis for large documents'
    },
    'balanced': {
        'rag_articles': 5,
        'topic_threshold': 2.0,  # Need 2+ topics (standard)
        'chunk_size': 800,
        'chunk_overlap': 100,
        'chunking_method': 'smart',
        'description': 'Recommended for most use cases'
    },
    'thorough': {
        'rag_articles': 8,
        'topic_threshold': 1.0,  # Any regulated topic gets analysed
        'chunk_size': 1000,
        'chunk_overlap': 150,
        'chunking_method': 'smart',
        'description': 'Comprehensive analysis (slower)'
    }
}

def apply_preset(preset_name: str) -> Dict[str, Any]:
    """Apply a performance preset to global config."""
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PRESETS.keys())}")
    
    settings = PRESETS[preset_name].copy()
    # Remove description from settings applied to config
    settings.pop('description', None)
    
    for key, value in settings.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return settings

def get_model_config(model_key: str = None) -> Dict[str, Any]:
    """Get model configuration with validation."""
    model_key = model_key or DEFAULT_MODEL
    if model_key not in MODELS:
        print(f"Warning: Unknown model '{model_key}', using '{DEFAULT_MODEL}'")
        model_key = DEFAULT_MODEL
    
    return MODELS[model_key].copy()