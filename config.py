from dataclasses import dataclass
from typing import Dict, Any

CONFIG_VERSION = "2.6.0"
KNOWLEDGE_BASE_DIR = "knowledge_base"

# Model configurations
MODELS = {
    "small": {
        "key": "small",
        "name": "llama3:8b",
        "batch_size": 4,
        "context_window": 4096,
        "temperature": 0.1,
        "description": "Fast model suitable for most analyses"
    },
    "medium": {
        "key": "medium", 
        "name": "llama3:70b-instruct-q4_0",
        "batch_size": 2,
        "context_window": 8192,
        "temperature": 0.1,
        "description": "Balanced model with improved accuracy"
    },
    "large": {
        "key": "large",
        "name": "llama3:70b-instruct",
        "batch_size": 1,
        "context_window": 8192,
        "temperature": 0.1,
        "description": "High-accuracy model (requires 32GB+ RAM)"
    }
}

DEFAULT_MODEL = "small"

# Enhanced configuration with progressive analysis features
@dataclass
class Config:
    # Core settings
    rag_articles: int = 5
    high_risk_threshold: float = 8.0
    chunk_size: int = 800
    chunk_overlap: int = 100
    chunking_method: str = "smart"
    progressive_enabled: bool = True
    max_prompt_length: int = 8000
    max_chunks_per_document: int = 50
    
    # Enhanced progressive analysis settings
    enable_enhanced_scoring: bool = True
    enable_phrase_matching: bool = True
    enable_context_analysis: bool = True
    enable_negation_detection: bool = True
    
    # Scoring thresholds
    medium_risk_threshold: float = 4.0
    low_risk_threshold: float = 1.0
    
    # Advanced scoring features
    phrase_weight_multiplier: float = 2.0
    context_weight_multiplier: float = 1.5
    negation_penalty_multiplier: float = -2.0
    
    # Performance tuning
    enable_scoring_debug: bool = False
    enable_framework_specific_weights: bool = True

# Global config instance
config = Config()

# Enhanced performance presets
PRESETS = {
    'speed': {
        'rag_articles': 3,
        'high_risk_threshold': 15.0,  # Only catch highest risk
        'chunk_size': 600,
        'chunk_overlap': 50,
        'chunking_method': 'simple',
        'enable_phrase_matching': False,
        'enable_context_analysis': False,
        'enable_negation_detection': False
    },
    'balanced': {
        'rag_articles': 5,
        'high_risk_threshold': 8.0,
        'chunk_size': 800,
        'chunk_overlap': 100,
        'chunking_method': 'smart',
        'enable_phrase_matching': True,
        'enable_context_analysis': True,
        'enable_negation_detection': True
    },
    'accuracy': {
        'rag_articles': 8,
        'high_risk_threshold': 3.0,  # Catch more potential issues
        'chunk_size': 1500,
        'chunk_overlap': 150,
        'chunking_method': 'smart',
        'enable_phrase_matching': True,
        'enable_context_analysis': True,
        'enable_negation_detection': True,
        'enable_scoring_debug': True
    },
    'comprehensive': {
        'rag_articles': 10,
        'high_risk_threshold': 1.0,  # Analyze almost everything
        'chunk_size': 1200,
        'chunk_overlap': 120,
        'chunking_method': 'smart',
        'enable_phrase_matching': True,
        'enable_context_analysis': True,
        'enable_negation_detection': True,
        'enable_scoring_debug': True,
        'phrase_weight_multiplier': 3.0,
        'context_weight_multiplier': 2.5
    }
}

def apply_preset(preset_name: str) -> Dict[str, Any]:
    """Apply a performance preset to global config."""
    assert preset_name in PRESETS, f"Unknown preset: {preset_name}"
    
    settings = PRESETS[preset_name]
    for key, value in settings.items():
        setattr(config, key, value)
    
    return settings

def get_current_config() -> Dict[str, Any]:
    """Get current configuration as dictionary."""
    return {
        'rag_articles': config.rag_articles,
        'high_risk_threshold': config.high_risk_threshold,
        'chunk_size': config.chunk_size,
        'chunk_overlap': config.chunk_overlap,
        'chunking_method': config.chunking_method,
        'progressive_enabled': config.progressive_enabled,
        'enable_enhanced_scoring': config.enable_enhanced_scoring,
        'enable_phrase_matching': config.enable_phrase_matching,
        'enable_context_analysis': config.enable_context_analysis,
        'enable_negation_detection': config.enable_negation_detection,
        'config_version': CONFIG_VERSION
    }

def get_model_config(model_key: str = None) -> Dict[str, Any]:
    """Get model configuration."""
    model_key = model_key or DEFAULT_MODEL
    assert model_key in MODELS, f"Unknown model: {model_key}"
    return MODELS[model_key].copy()

def get_scoring_config() -> Dict[str, Any]:
    """Get scoring configuration for progressive analysis."""
    return {
        'high_risk_threshold': config.high_risk_threshold,
        'medium_risk_threshold': config.medium_risk_threshold,
        'low_risk_threshold': config.low_risk_threshold,
        'enable_phrase_matching': config.enable_phrase_matching,
        'enable_context_analysis': config.enable_context_analysis,
        'enable_negation_detection': config.enable_negation_detection,
        'phrase_weight_multiplier': config.phrase_weight_multiplier,
        'context_weight_multiplier': config.context_weight_multiplier,
        'negation_penalty_multiplier': config.negation_penalty_multiplier,
        'enable_scoring_debug': config.enable_scoring_debug
    }