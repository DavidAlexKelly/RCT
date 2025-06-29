# config.py - Enhanced Configuration with Proper Validation

"""
Enhanced Configuration for Compliance Analysis Tool with Validation
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

CONFIG_VERSION = "2.5.1"  # Enhanced validation version
KNOWLEDGE_BASE_DIR = "knowledge_base"

# =============================================================================
# MODEL CONFIGURATIONS WITH VALIDATION
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

# Validate model configuration on import
def _validate_models():
    """Validate model configurations."""
    if not MODELS:
        raise ValueError("MODELS dictionary cannot be empty")
    
    if DEFAULT_MODEL not in MODELS:
        available = list(MODELS.keys())
        raise ValueError(f"DEFAULT_MODEL '{DEFAULT_MODEL}' not found in MODELS. Available: {available}")
    
    required_model_fields = ["key", "name", "batch_size", "context_window", "temperature"]
    
    for model_key, model_config in MODELS.items():
        if not isinstance(model_config, dict):
            raise ValueError(f"Model '{model_key}' configuration must be a dictionary")
        
        for field in required_model_fields:
            if field not in model_config:
                raise ValueError(f"Model '{model_key}' missing required field: {field}")
        
        # Validate field types and ranges
        if not isinstance(model_config["batch_size"], int) or model_config["batch_size"] < 1:
            raise ValueError(f"Model '{model_key}' batch_size must be a positive integer")
        
        if not isinstance(model_config["context_window"], int) or model_config["context_window"] < 1000:
            raise ValueError(f"Model '{model_key}' context_window must be >= 1000")
        
        if not isinstance(model_config["temperature"], (int, float)) or not (0 <= model_config["temperature"] <= 2):
            raise ValueError(f"Model '{model_key}' temperature must be between 0 and 2")

# Run validation on import
_validate_models()

# =============================================================================
# CORE CONFIGURATION CLASSES WITH VALIDATION
# =============================================================================

class RAGConfig:
    """Controls what regulatory context the LLM sees."""
    _ARTICLES_COUNT = 5
    SIMILARITY_THRESHOLD = 0.5
    ENABLE_RERANKING = False
    
    @property
    def ARTICLES_COUNT(self):
        return self._ARTICLES_COUNT
    
    @ARTICLES_COUNT.setter
    def ARTICLES_COUNT(self, value):
        if not isinstance(value, int):
            raise ValueError("ARTICLES_COUNT must be an integer")
        if not (1 <= value <= 20):
            raise ValueError("ARTICLES_COUNT must be between 1 and 20")
        self._ARTICLES_COUNT = value

# Create instance to allow property access
RAGConfig = RAGConfig()

class ProgressiveConfig:
    """Controls which document sections get LLM analysis."""
    _ENABLED = True
    _HIGH_RISK_THRESHOLD = 8
    _MEDIUM_RISK_THRESHOLD = 3
    _LOW_RISK_THRESHOLD = 1
    DATA_TERM_WEIGHT = 1
    REGULATORY_TERM_WEIGHT = 2
    HIGH_RISK_PATTERN_WEIGHT = 5
    MIN_SECTION_LENGTH = 150
    
    @property
    def ENABLED(self):
        return self._ENABLED
    
    @ENABLED.setter
    def ENABLED(self, value):
        if not isinstance(value, bool):
            raise ValueError("ENABLED must be a boolean")
        self._ENABLED = value
    
    @property
    def HIGH_RISK_THRESHOLD(self):
        return self._HIGH_RISK_THRESHOLD
    
    @HIGH_RISK_THRESHOLD.setter
    def HIGH_RISK_THRESHOLD(self, value):
        if not isinstance(value, int):
            raise ValueError("HIGH_RISK_THRESHOLD must be an integer")
        if not (1 <= value <= 50):
            raise ValueError("HIGH_RISK_THRESHOLD must be between 1 and 50")
        self._HIGH_RISK_THRESHOLD = value
    
    @property
    def MEDIUM_RISK_THRESHOLD(self):
        return self._MEDIUM_RISK_THRESHOLD
    
    @MEDIUM_RISK_THRESHOLD.setter
    def MEDIUM_RISK_THRESHOLD(self, value):
        if not isinstance(value, int):
            raise ValueError("MEDIUM_RISK_THRESHOLD must be an integer")
        if not (1 <= value <= 20):
            raise ValueError("MEDIUM_RISK_THRESHOLD must be between 1 and 20")
        self._MEDIUM_RISK_THRESHOLD = value

# Create instance
ProgressiveConfig = ProgressiveConfig()

class DocumentConfig:
    """Controls how documents are chunked and processed."""
    _DEFAULT_CHUNK_SIZE = 800
    _DEFAULT_CHUNK_OVERLAP = 100
    _DEFAULT_CHUNKING_METHOD = "smart"
    MIN_CHUNK_SIZE = 200
    MAX_CHUNK_SIZE = 5000
    MIN_OVERLAP = 0
    MAX_OVERLAP = 500
    _OPTIMIZE_CHUNK_SIZE = True
    SMALL_DOC_THRESHOLD = 10000
    LARGE_DOC_THRESHOLD = 200000
    MAX_CHUNKS_PER_DOCUMENT = 50
    
    @property
    def DEFAULT_CHUNK_SIZE(self):
        return self._DEFAULT_CHUNK_SIZE
    
    @DEFAULT_CHUNK_SIZE.setter
    def DEFAULT_CHUNK_SIZE(self, value):
        if not isinstance(value, int):
            raise ValueError("DEFAULT_CHUNK_SIZE must be an integer")
        if not (self.MIN_CHUNK_SIZE <= value <= self.MAX_CHUNK_SIZE):
            raise ValueError(f"DEFAULT_CHUNK_SIZE must be between {self.MIN_CHUNK_SIZE} and {self.MAX_CHUNK_SIZE}")
        self._DEFAULT_CHUNK_SIZE = value
    
    @property
    def DEFAULT_CHUNK_OVERLAP(self):
        return self._DEFAULT_CHUNK_OVERLAP
    
    @DEFAULT_CHUNK_OVERLAP.setter
    def DEFAULT_CHUNK_OVERLAP(self, value):
        if not isinstance(value, int):
            raise ValueError("DEFAULT_CHUNK_OVERLAP must be an integer")
        if not (self.MIN_OVERLAP <= value <= self.MAX_OVERLAP):
            raise ValueError(f"DEFAULT_CHUNK_OVERLAP must be between {self.MIN_OVERLAP} and {self.MAX_OVERLAP}")
        if value >= self._DEFAULT_CHUNK_SIZE:
            raise ValueError("DEFAULT_CHUNK_OVERLAP must be less than DEFAULT_CHUNK_SIZE")
        self._DEFAULT_CHUNK_OVERLAP = value
    
    @property
    def DEFAULT_CHUNKING_METHOD(self):
        return self._DEFAULT_CHUNKING_METHOD
    
    @DEFAULT_CHUNKING_METHOD.setter
    def DEFAULT_CHUNKING_METHOD(self, value):
        valid_methods = ["smart", "paragraph", "sentence", "simple"]
        if value not in valid_methods:
            raise ValueError(f"DEFAULT_CHUNKING_METHOD must be one of {valid_methods}")
        self._DEFAULT_CHUNKING_METHOD = value
    
    @property
    def OPTIMIZE_CHUNK_SIZE(self):
        return self._OPTIMIZE_CHUNK_SIZE
    
    @OPTIMIZE_CHUNK_SIZE.setter
    def OPTIMIZE_CHUNK_SIZE(self, value):
        if not isinstance(value, bool):
            raise ValueError("OPTIMIZE_CHUNK_SIZE must be a boolean")
        self._OPTIMIZE_CHUNK_SIZE = value

# Create instance
DocumentConfig = DocumentConfig()

class LLMConfig:
    """Basic LLM settings with validation."""
    _MAX_PROMPT_LENGTH = 8000
    INCLUDE_EXAMPLES = False
    
    @property
    def MAX_PROMPT_LENGTH(self):
        return self._MAX_PROMPT_LENGTH
    
    @MAX_PROMPT_LENGTH.setter
    def MAX_PROMPT_LENGTH(self, value):
        if not isinstance(value, int):
            raise ValueError("MAX_PROMPT_LENGTH must be an integer")
        if not (1000 <= value <= 50000):
            raise ValueError("MAX_PROMPT_LENGTH must be between 1000 and 50000")
        self._MAX_PROMPT_LENGTH = value

# Create instance
LLMConfig = LLMConfig()

# =============================================================================
# PERFORMANCE PRESETS WITH VALIDATION
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

def _validate_presets():
    """Validate performance presets."""
    if not PERFORMANCE_PRESETS:
        raise ValueError("PERFORMANCE_PRESETS cannot be empty")
    
    required_preset_fields = [
        'rag_articles', 'high_risk_threshold', 'progressive_enabled',
        'chunking_method', 'chunk_size', 'chunk_overlap', 'optimize_chunks'
    ]
    
    for preset_name, preset_config in PERFORMANCE_PRESETS.items():
        if not isinstance(preset_config, dict):
            raise ValueError(f"Preset '{preset_name}' must be a dictionary")
        
        for field in required_preset_fields:
            if field not in preset_config:
                raise ValueError(f"Preset '{preset_name}' missing required field: {field}")
        
        # Validate ranges
        if not (1 <= preset_config['rag_articles'] <= 20):
            raise ValueError(f"Preset '{preset_name}' rag_articles must be between 1 and 20")
        
        if not (1 <= preset_config['high_risk_threshold'] <= 50):
            raise ValueError(f"Preset '{preset_name}' high_risk_threshold must be between 1 and 50")
        
        if preset_config['chunking_method'] not in ["smart", "paragraph", "sentence", "simple"]:
            raise ValueError(f"Preset '{preset_name}' invalid chunking_method")
        
        if not (200 <= preset_config['chunk_size'] <= 5000):
            raise ValueError(f"Preset '{preset_name}' chunk_size must be between 200 and 5000")
        
        if preset_config['chunk_overlap'] >= preset_config['chunk_size']:
            raise ValueError(f"Preset '{preset_name}' chunk_overlap must be less than chunk_size")

# Run validation
_validate_presets()

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
# HELPER FUNCTIONS WITH VALIDATION
# =============================================================================

def apply_preset(preset_name: str) -> Dict[str, Any]:
    """Apply a performance preset with validation."""
    if not preset_name:
        raise ValueError("preset_name cannot be empty")
    
    if not isinstance(preset_name, str):
        raise ValueError("preset_name must be a string")
    
    if preset_name not in PERFORMANCE_PRESETS:
        available = list(PERFORMANCE_PRESETS.keys())
        raise ValueError(f"Unknown preset: {preset_name}. Available: {available}")
    
    settings = PERFORMANCE_PRESETS[preset_name].copy()
    
    # Apply settings to configuration classes with validation
    try:
        RAGConfig.ARTICLES_COUNT = settings['rag_articles']
        ProgressiveConfig.HIGH_RISK_THRESHOLD = settings['high_risk_threshold']
        ProgressiveConfig.ENABLED = settings['progressive_enabled']
        
        # Apply chunking settings
        DocumentConfig.DEFAULT_CHUNKING_METHOD = settings['chunking_method']
        DocumentConfig.DEFAULT_CHUNK_SIZE = settings['chunk_size']
        DocumentConfig.DEFAULT_CHUNK_OVERLAP = settings['chunk_overlap']
        DocumentConfig.OPTIMIZE_CHUNK_SIZE = settings['optimize_chunks']
        
    except Exception as e:
        raise ValueError(f"Failed to apply preset '{preset_name}': {e}")
    
    return settings

def apply_chunking_preset(preset_name: str) -> Dict[str, Any]:
    """Apply a chunking preset with validation."""
    if not preset_name:
        raise ValueError("preset_name cannot be empty")
    
    if preset_name not in CHUNKING_PRESETS:
        available = list(CHUNKING_PRESETS.keys())
        raise ValueError(f"Unknown chunking preset: {preset_name}. Available: {available}")
    
    settings = CHUNKING_PRESETS[preset_name].copy()
    
    try:
        # Apply settings with validation
        DocumentConfig.DEFAULT_CHUNKING_METHOD = settings['chunking_method']
        DocumentConfig.DEFAULT_CHUNK_SIZE = settings['chunk_size']
        DocumentConfig.DEFAULT_CHUNK_OVERLAP = settings['chunk_overlap']
        DocumentConfig.OPTIMIZE_CHUNK_SIZE = settings['optimize_chunks']
    except Exception as e:
        raise ValueError(f"Failed to apply chunking preset '{preset_name}': {e}")
    
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
        'max_prompt_length': LLMConfig.MAX_PROMPT_LENGTH,
        'config_version': CONFIG_VERSION
    }

def validate_configuration() -> Dict[str, Any]:
    """Comprehensive configuration validation."""
    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "config_version": CONFIG_VERSION
    }
    
    try:
        # Validate models
        _validate_models()
        
        # Validate presets
        _validate_presets()
        
        # Check consistency
        if DocumentConfig.DEFAULT_CHUNK_OVERLAP >= DocumentConfig.DEFAULT_CHUNK_SIZE:
            validation_result["errors"].append("DEFAULT_CHUNK_OVERLAP must be less than DEFAULT_CHUNK_SIZE")
            validation_result["valid"] = False
        
        # Check reasonable values
        if RAGConfig.ARTICLES_COUNT > 15:
            validation_result["warnings"].append("High RAG articles count may slow analysis")
        
        if ProgressiveConfig.HIGH_RISK_THRESHOLD < 3:
            validation_result["warnings"].append("Very low risk threshold may analyze too many sections")
        
        if DocumentConfig.DEFAULT_CHUNK_SIZE > 2000:
            validation_result["warnings"].append("Large chunk size may exceed model context window")
        
    except Exception as e:
        validation_result["errors"].append(f"Configuration validation failed: {e}")
        validation_result["valid"] = False
    
    return validation_result

def print_config_summary():
    """Print a summary of current performance settings."""
    validation = validate_configuration()
    
    print("🔧 COMPLIANCE ANALYZER CONFIGURATION")
    print("=" * 45)
    print(f"Config Version: {CONFIG_VERSION}")
    print(f"Validation Status: {'✅ Valid' if validation['valid'] else '❌ Invalid'}")
    
    if validation['errors']:
        print("❌ Errors:")
        for error in validation['errors']:
            print(f"  - {error}")
    
    if validation['warnings']:
        print("⚠️ Warnings:")
        for warning in validation['warnings']:
            print(f"  - {warning}")
    
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
    """Get configuration for a specific model with validation."""
    if model_key is None:
        model_key = DEFAULT_MODEL
    
    if not isinstance(model_key, str):
        raise ValueError("model_key must be a string")
    
    if model_key not in MODELS:
        available = list(MODELS.keys())
        raise ValueError(f"Unknown model: {model_key}. Available: {available}")
    
    return MODELS[model_key].copy()

def list_available_models() -> List[str]:
    """Get list of available model keys."""
    return list(MODELS.keys())

def get_chunking_methods() -> Dict[str, str]:
    """Get available chunking methods with descriptions."""
    return CHUNKING_METHODS.copy()

# =============================================================================
# BACKWARD COMPATIBILITY (Deprecated - use class properties instead)
# =============================================================================

# Keep these for any code that imports them directly
DEFAULT_CHUNK_SIZE = DocumentConfig.DEFAULT_CHUNK_SIZE
DEFAULT_CHUNK_OVERLAP = DocumentConfig.DEFAULT_CHUNK_OVERLAP
PROGRESSIVE_ANALYSIS_ENABLED = ProgressiveConfig.ENABLED
HIGH_RISK_SCORE_THRESHOLD = ProgressiveConfig.HIGH_RISK_THRESHOLD
MEDIUM_RISK_SCORE_THRESHOLD = ProgressiveConfig.MEDIUM_RISK_THRESHOLD

# Legacy function for backward compatibility
def get_prompt_for_regulation(regulation_framework: str, prompt_type: str) -> str:
    """Legacy function for prompt generation - deprecated."""
    import warnings
    warnings.warn("get_prompt_for_regulation is deprecated. Use PromptManager instead.", DeprecationWarning)
    
    if not regulation_framework or not prompt_type:
        raise ValueError("regulation_framework and prompt_type cannot be empty")
    
    if prompt_type == "analyze_compliance":
        return f"Analyze this text for compliance with {regulation_framework} requirements."
    elif prompt_type == "contradiction_analysis":
        return "Analyze for contradictions across sections."
    else:
        raise ValueError(f"Unknown prompt_type: {prompt_type}")

# =============================================================================
# USAGE EXAMPLE AND VALIDATION ON IMPORT
# =============================================================================

if __name__ == "__main__":
    # Run comprehensive validation
    validation = validate_configuration()
    
    if not validation["valid"]:
        print("❌ Configuration validation failed!")
        for error in validation["errors"]:
            print(f"  - {error}")
        exit(1)
    
    print_config_summary()
    config = get_current_config()
    print(f"\nCurrent config: {config}")
    
    print(f"\nAvailable chunking methods:")
    for method, description in get_chunking_methods().items():
        print(f"  {method}: {description}")
    
    print(f"\nAvailable presets:")
    for preset in PERFORMANCE_PRESETS.keys():
        print(f"  {preset}")

# Run basic validation on import
try:
    _basic_validation = validate_configuration()
    if not _basic_validation["valid"]:
        print("⚠️ Configuration validation warnings on import:")
        for error in _basic_validation["errors"]:
            print(f"  - {error}")
except Exception as e:
    print(f"⚠️ Configuration validation error on import: {e}")