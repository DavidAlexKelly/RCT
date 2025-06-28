# config.py - Simplified Configuration for Compliance Analysis Tool

"""
Simplified Configuration for Compliance Analysis Tool
🎯 QUICK TUNING GUIDE:
- For BETTER ACCURACY: Increase rag_articles, lower risk_threshold
- For FASTER PROCESSING: Decrease rag_articles, raise risk_threshold  
- For LOWER COSTS: Increase risk_threshold, decrease chunk_size
- For BETTER CONTEXT: Increase chunk_size, use smart/paragraph chunking
"""

from typing import Dict, Any, List

# =============================================================================
# VERSION & METADATA
# =============================================================================

CONFIG_VERSION = "2.5.0"  # Simplified version
KNOWLEDGE_BASE_DIR = "knowledge_base"

# =============================================================================
# MODEL CONFIGURATIONS
# =============================================================================

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

# =============================================================================
# CORE CONFIGURATION CLASSES (Simplified)
# =============================================================================

class RAGConfig:
    """Controls what regulatory context the LLM sees."""
    ARTICLES_COUNT = 5
    SIMILARITY_THRESHOLD = 0.5
    ENABLE_RERANKING = False

class ProgressiveConfig:
    """Controls which document sections get LLM analysis."""
    ENABLED = True
    HIGH_RISK_THRESHOLD = 8
    MEDIUM_RISK_THRESHOLD = 3
    LOW_RISK_THRESHOLD = 1
    DATA_TERM_WEIGHT = 1
    REGULATORY_TERM_WEIGHT = 2
    HIGH_RISK_PATTERN_WEIGHT = 5
    MIN_SECTION_LENGTH = 150

class DocumentConfig:
    """Controls how documents are chunked and processed."""
    DEFAULT_CHUNK_SIZE = 800
    DEFAULT_CHUNK_OVERLAP = 100
    DEFAULT_CHUNKING_METHOD = "smart"
    MIN_CHUNK_SIZE = 200
    MAX_CHUNK_SIZE = 2000
    MIN_OVERLAP = 0
    MAX_OVERLAP = 200
    OPTIMIZE_CHUNK_SIZE = True
    SMALL_DOC_THRESHOLD = 10000
    LARGE_DOC_THRESHOLD = 200000
    MAX_CHUNKS_PER_DOCUMENT = 50

class LLMConfig:
    """Basic LLM settings."""
    MAX_PROMPT_LENGTH = 4000
    INCLUDE_EXAMPLES = False

# =============================================================================
# PERFORMANCE PRESETS (Simplified)
# =============================================================================

PERFORMANCE_PRESETS = {
    'speed': {
        'rag_articles': 3,
        'high_risk_threshold': 12,
        'progressive_enabled': True,
        'chunking_method': 'simple',
        'chunk_size': 600,
        'chunk_overlap': 50,
        'optimize_chunks': True
    },
    'balanced': {
        'rag_articles': 5,
        'high_risk_threshold': 8,
        'progressive_enabled': True,
        'chunking_method': 'smart',
        'chunk_size': 800,
        'chunk_overlap': 100,
        'optimize_chunks': True
    },
    'accuracy': {
        'rag_articles': 8,
        'high_risk_threshold': 3,
        'progressive_enabled': True,
        'chunking_method': 'smart',
        'chunk_size': 1500,
        'chunk_overlap': 150,
        'optimize_chunks': True
    },
    'comprehensive': {
        'rag_articles': 10,
        'high_risk_threshold': 1,
        'progressive_enabled': False,
        'chunking_method': 'smart',
        'chunk_size': 1200,
        'chunk_overlap': 120,
        'optimize_chunks': False
    }
}

CHUNKING_PRESETS = {
    'fast': {
        'chunking_method': 'simple',
        'chunk_size': 600,
        'chunk_overlap': 50,
        'optimize_chunks': True
    },
    'balanced': {
        'chunking_method': 'smart',
        'chunk_size': 800,
        'chunk_overlap': 100,
        'optimize_chunks': True
    },
    'context': {
        'chunking_method': 'smart',
        'chunk_size': 1500,
        'chunk_overlap': 150,
        'optimize_chunks': True
    },
    'compliance': {
        'chunking_method': 'smart',
        'chunk_size': 1200,
        'chunk_overlap': 120,
        'optimize_chunks': False
    }
}

CHUNKING_METHODS = {
    "smart": "Detect sections, fallback to paragraphs",
    "paragraph": "Group by paragraphs", 
    "sentence": "Group by sentences",
    "simple": "Character-based with word boundaries"
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def apply_preset(preset_name: str) -> Dict[str, Any]:
    """Apply a performance preset to the current configuration."""
    if preset_name not in PERFORMANCE_PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PERFORMANCE_PRESETS.keys())}")
    
    settings = PERFORMANCE_PRESETS[preset_name]
    
    # Apply settings to configuration classes
    RAGConfig.ARTICLES_COUNT = settings['rag_articles']
    ProgressiveConfig.HIGH_RISK_THRESHOLD = settings['high_risk_threshold']
    ProgressiveConfig.ENABLED = settings['progressive_enabled']
    
    # Apply chunking settings
    DocumentConfig.DEFAULT_CHUNKING_METHOD = settings['chunking_method']
    DocumentConfig.DEFAULT_CHUNK_SIZE = settings['chunk_size']
    DocumentConfig.DEFAULT_CHUNK_OVERLAP = settings['chunk_overlap']
    DocumentConfig.OPTIMIZE_CHUNK_SIZE = settings['optimize_chunks']
    
    return settings

def apply_chunking_preset(preset_name: str) -> Dict[str, Any]:
    """Apply a chunking preset."""
    if preset_name not in CHUNKING_PRESETS:
        raise ValueError(f"Unknown chunking preset: {preset_name}")
    
    settings = CHUNKING_PRESETS[preset_name]
    
    # Apply settings
    DocumentConfig.DEFAULT_CHUNKING_METHOD = settings['chunking_method']
    DocumentConfig.DEFAULT_CHUNK_SIZE = settings['chunk_size']
    DocumentConfig.DEFAULT_CHUNK_OVERLAP = settings['chunk_overlap']
    DocumentConfig.OPTIMIZE_CHUNK_SIZE = settings['optimize_chunks']
    
    return settings

def get_current_config() -> Dict[str, Any]:
    """Get current configuration as a dictionary."""
    return {
        'rag_articles_count': RAGConfig.ARTICLES_COUNT,
        'high_risk_threshold': ProgressiveConfig.HIGH_RISK_THRESHOLD,
        'progressive_enabled': ProgressiveConfig.ENABLED,
        'default_model': DEFAULT_MODEL,
        'chunking_method': DocumentConfig.DEFAULT_CHUNKING_METHOD,
        'chunk_size': DocumentConfig.DEFAULT_CHUNK_SIZE,
        'chunk_overlap': DocumentConfig.DEFAULT_CHUNK_OVERLAP,
        'optimize_chunks': DocumentConfig.OPTIMIZE_CHUNK_SIZE,
        'config_version': CONFIG_VERSION
    }

def print_config_summary():
    """Print a summary of current performance settings."""
    print("🔧 COMPLIANCE ANALYZER CONFIGURATION")
    print("=" * 45)
    print(f"Config Version: {CONFIG_VERSION}")
    print(f"Default Model: {DEFAULT_MODEL}")
    print(f"RAG Articles Count: {RAGConfig.ARTICLES_COUNT}")
    print(f"High Risk Threshold: {ProgressiveConfig.HIGH_RISK_THRESHOLD}")
    print(f"Progressive Analysis: {'Enabled' if ProgressiveConfig.ENABLED else 'Disabled'}")
    print("------ Document Processing ------")
    print(f"Chunking Method: {DocumentConfig.DEFAULT_CHUNKING_METHOD}")
    print(f"Chunk Size: {DocumentConfig.DEFAULT_CHUNK_SIZE}")
    print(f"Chunk Overlap: {DocumentConfig.DEFAULT_CHUNK_OVERLAP}")
    print(f"Auto-optimize: {'Enabled' if DocumentConfig.OPTIMIZE_CHUNK_SIZE else 'Disabled'}")
    print("=" * 45)

def get_model_config(model_key: str = None) -> Dict[str, Any]:
    """Get configuration for a specific model."""
    if model_key is None:
        model_key = DEFAULT_MODEL
    
    if model_key not in MODELS:
        raise ValueError(f"Unknown model: {model_key}. Available: {list(MODELS.keys())}")
    
    return MODELS[model_key]

def list_available_models() -> List[str]:
    """Get list of available model keys."""
    return list(MODELS.keys())

def get_chunking_methods() -> Dict[str, str]:
    """Get available chunking methods with descriptions."""
    return CHUNKING_METHODS.copy()

# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

# Keep these for any code that imports them directly
DEFAULT_CHUNK_SIZE = DocumentConfig.DEFAULT_CHUNK_SIZE
DEFAULT_CHUNK_OVERLAP = DocumentConfig.DEFAULT_CHUNK_OVERLAP
PROGRESSIVE_ANALYSIS_ENABLED = ProgressiveConfig.ENABLED
HIGH_RISK_SCORE_THRESHOLD = ProgressiveConfig.HIGH_RISK_THRESHOLD
MEDIUM_RISK_SCORE_THRESHOLD = ProgressiveConfig.MEDIUM_RISK_THRESHOLD

# Legacy function for backward compatibility
def get_prompt_for_regulation(regulation_framework: str, prompt_type: str) -> str:
    """Legacy function for prompt generation."""
    if prompt_type == "analyze_compliance":
        return f"Analyze this text for compliance with {regulation_framework} requirements."
    elif prompt_type == "contradiction_analysis":
        return "Analyze for contradictions across sections."
    return ""

# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    print_config_summary()
    config = get_current_config()
    print(f"\nCurrent config: {config}")
    
    print(f"\nAvailable chunking methods:")
    for method, description in get_chunking_methods().items():
        print(f"  {method}: {description}")
    
    print(f"\nAvailable presets:")
    for preset in PERFORMANCE_PRESETS.keys():
        print(f"  {preset}")