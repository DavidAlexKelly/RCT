# config.py - UPDATED with improved chunking configuration

"""
Unified Configuration for Compliance Analysis Tool - Enhanced Chunking Version
🎯 QUICK TUNING GUIDE:
- For BETTER ACCURACY: Increase RAG_ARTICLES_COUNT, lower PROGRESSIVE_* thresholds
- For FASTER PROCESSING: Decrease RAG_ARTICLES_COUNT, raise PROGRESSIVE_* thresholds  
- For LOWER COSTS: Increase PROGRESSIVE_* thresholds, decrease CHUNK_* sizes
- For BETTER CONTEXT: Increase chunk sizes, use smart/paragraph chunking
"""

from typing import Dict, Any, List

# =============================================================================
# VERSION & METADATA
# =============================================================================

CONFIG_VERSION = "2.4.0"  # Updated for enhanced chunking
KNOWLEDGE_BASE_DIR = "knowledge_base"

# =============================================================================
# MODEL CONFIGURATIONS
# =============================================================================

class ModelConfig:
    """LLM model configurations for different sizes and capabilities."""
    
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
    
    # Default model to use
    DEFAULT_MODEL = "small"

# =============================================================================
# RAG (Retrieval-Augmented Generation) Settings
# =============================================================================

class RAGConfig:
    """Controls what regulatory context the LLM sees."""
    
    # Number of regulation articles to show LLM per document chunk
    ARTICLES_COUNT = 3
    
    # Vector similarity search parameters
    SIMILARITY_THRESHOLD = 0.5
    ENABLE_RERANKING = False

# =============================================================================
# PROGRESSIVE ANALYSIS SETTINGS  
# =============================================================================

class ProgressiveConfig:
    """Controls which document sections get LLM analysis."""
    
    # Enable/disable progressive analysis
    ENABLED = True
    
    # Risk scoring thresholds (higher = more selective)
    HIGH_RISK_THRESHOLD = 8
    MEDIUM_RISK_THRESHOLD = 3
    LOW_RISK_THRESHOLD = 1
    
    # Term scoring weights
    DATA_TERM_WEIGHT = 1
    REGULATORY_TERM_WEIGHT = 2
    HIGH_RISK_PATTERN_WEIGHT = 5
    
    # Minimum section length to analyze (characters)
    MIN_SECTION_LENGTH = 150
    
    # Legacy compatibility
    RISK_SCORE_WEIGHTS = {
        "high_risk_keyword": HIGH_RISK_PATTERN_WEIGHT,
        "pattern_indicator": REGULATORY_TERM_WEIGHT,
        "data_term": DATA_TERM_WEIGHT
    }

# =============================================================================
# ENHANCED DOCUMENT PROCESSING SETTINGS
# =============================================================================

class DocumentConfig:
    """Controls how documents are chunked and processed - Enhanced Version."""
    
    # Default chunk size settings
    DEFAULT_CHUNK_SIZE = 800
    DEFAULT_CHUNK_OVERLAP = 100
    
    # Chunking method options
    CHUNKING_METHODS = {
        "smart": "Detect sections, fallback to paragraphs",
        "paragraph": "Group by paragraphs", 
        "sentence": "Group by sentences",
        "simple": "Character-based with word boundaries"
    }
    DEFAULT_CHUNKING_METHOD = "smart"
    
    # Chunk size limits
    MIN_CHUNK_SIZE = 200
    MAX_CHUNK_SIZE = 2000
    
    # Overlap limits
    MIN_OVERLAP = 0
    MAX_OVERLAP = 200
    
    # Chunk size optimization based on document size
    OPTIMIZE_CHUNK_SIZE = True
    SMALL_DOC_THRESHOLD = 10000    # Less than 10KB
    LARGE_DOC_THRESHOLD = 200000   # More than 200KB
    
    # Smart chunking parameters
    SMART_SECTION_MAX_SIZE = 3000  # Keep sections together up to this size
    SMART_MIN_SECTIONS = 2         # Minimum sections needed for smart chunking
    SMART_MAX_SECTIONS = 20        # Too many sections = probably false positives
    SMART_MIN_AVG_SIZE = 300       # Minimum average section size
    
    # Maximum chunks to process (prevent runaway costs)
    MAX_CHUNKS_PER_DOCUMENT = 50
    
    # Section detection patterns (for smart chunking)
    SECTION_PATTERNS = [
        r'^(\d+\.\s+[A-Z][^\n]{10,80})$',  # "1. Section Title"
        r'^([A-Z][A-Z\s]{5,50}[A-Z])$',   # "SECTION TITLE" (all caps)
        r'^(#{1,3}\s+[^\n]+)$',           # "# Markdown Headers"
        r'^([A-Z][a-zA-Z\s&]{5,60}:)$'   # "Section Title:"
    ]

# =============================================================================
# LLM ANALYSIS SETTINGS - SIMPLIFIED
# =============================================================================

class LLMConfig:
    """Controls LLM behavior and response quality - simplified version."""
    
    # Citation handling - very permissive, no validation
    CITATION_MIN_LENGTH = 3      # Very short minimum
    CITATION_MAX_LENGTH = 1000   # Very long maximum
    
    # VALIDATION DISABLED FOR SIMPLICITY
    VALIDATE_CITATIONS = False           # No citation validation
    REQUIRE_ARTICLE_REFERENCES = False   # No article reference requirements
    
    # Prompt optimization
    MAX_PROMPT_LENGTH = 4000
    INCLUDE_EXAMPLES = False

# =============================================================================
# QUALITY CONTROL SETTINGS - SIMPLIFIED
# =============================================================================

class QualityConfig:
    """Controls output quality and validation - simplified version."""
    
    # Deduplication settings
    SIMILARITY_THRESHOLD_DEDUP = 0.8
    MAX_ISSUES_PER_SECTION = 10
    
    # SIMPLIFIED - NO COMPLEX VALIDATION
    BUSINESS_TERMS_REQUIRED = 0      # No requirements
    LEGAL_TERMS_ALLOWED = 100        # No limits
    VALIDATE_ARTICLE_MAPPING = False # No validation

# =============================================================================
# CHUNKING OPTIMIZATION PRESETS
# =============================================================================

class ChunkingPresets:
    """Pre-configured chunking settings for different use cases."""
    
    @staticmethod
    def fast_processing():
        """Optimized for speed - smaller chunks, simple method."""
        return {
            'chunking_method': 'simple',
            'chunk_size': 600,
            'chunk_overlap': 50,
            'optimize_chunks': True
        }
    
    @staticmethod
    def balanced():
        """Balanced approach - good speed and context."""
        return {
            'chunking_method': 'smart',
            'chunk_size': 800,
            'chunk_overlap': 100,
            'optimize_chunks': True
        }
    
    @staticmethod
    def high_context():
        """Optimized for accuracy - larger chunks, better context."""
        return {
            'chunking_method': 'smart',
            'chunk_size': 1500,
            'chunk_overlap': 150,
            'optimize_chunks': True
        }
    
    @staticmethod
    def compliance_focused():
        """Optimized for compliance documents - section-aware."""
        return {
            'chunking_method': 'smart',
            'chunk_size': 1200,
            'chunk_overlap': 120,
            'optimize_chunks': False  # Keep consistent sizes
        }

# =============================================================================
# PERFORMANCE TUNING PRESETS - UPDATED
# =============================================================================

class PerformancePresets:
    """Pre-configured settings for different use cases - now includes chunking."""
    
    @staticmethod
    def accuracy_focused():
        """Settings optimized for maximum accuracy (slower, more expensive)."""
        return {
            'rag_articles': 8,
            'high_risk_threshold': 3,
            'progressive_enabled': True,
            **ChunkingPresets.high_context()
        }
    
    @staticmethod
    def speed_focused():
        """Settings optimized for speed (less accurate, cheaper)."""
        return {
            'rag_articles': 3,
            'high_risk_threshold': 12,
            'progressive_enabled': True,
            **ChunkingPresets.fast_processing()
        }
    
    @staticmethod
    def balanced():
        """Balanced settings (current defaults)."""
        return {
            'rag_articles': 5,
            'high_risk_threshold': 6,
            'progressive_enabled': True,
            **ChunkingPresets.balanced()
        }
    
    @staticmethod
    def comprehensive():
        """Analyze everything (most thorough, most expensive)."""
        return {
            'rag_articles': 10,
            'high_risk_threshold': 1,
            'progressive_enabled': False,
            **ChunkingPresets.compliance_focused()
        }

# =============================================================================
# EXPERIMENTAL SETTINGS
# =============================================================================

class ExperimentalConfig:
    """Experimental features that may improve performance."""
    
    ENABLE_SECOND_PASS = False
    ENABLE_CROSS_SECTION = False
    ENABLE_CHAIN_OF_THOUGHT = False
    ENABLE_SELF_CORRECTION = False
    INCLUDE_DOCUMENT_METADATA = True
    INCLUDE_PREVIOUS_FINDINGS = False
    
    # NEW: Chunking experiments
    ENABLE_SEMANTIC_CHUNKING = False      # Chunk by semantic similarity
    ENABLE_ADAPTIVE_OVERLAP = False       # Adjust overlap based on content
    ENABLE_CROSS_CHUNK_ANALYSIS = False   # Analyze relationships between chunks

# =============================================================================
# HELPER FUNCTIONS - UPDATED
# =============================================================================

def apply_preset(preset_name: str) -> Dict[str, Any]:
    """Apply a performance preset to the current configuration."""
    presets = {
        'accuracy': PerformancePresets.accuracy_focused(),
        'speed': PerformancePresets.speed_focused(), 
        'balanced': PerformancePresets.balanced(),
        'comprehensive': PerformancePresets.comprehensive()
    }
    
    if preset_name not in presets:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(presets.keys())}")
    
    settings = presets[preset_name]
    
    # Apply settings to configuration classes
    RAGConfig.ARTICLES_COUNT = settings['rag_articles']
    ProgressiveConfig.HIGH_RISK_THRESHOLD = settings['high_risk_threshold']
    ProgressiveConfig.ENABLED = settings['progressive_enabled']
    
    # NEW: Apply chunking settings
    DocumentConfig.DEFAULT_CHUNKING_METHOD = settings['chunking_method']
    DocumentConfig.DEFAULT_CHUNK_SIZE = settings['chunk_size']
    DocumentConfig.DEFAULT_CHUNK_OVERLAP = settings['chunk_overlap']
    DocumentConfig.OPTIMIZE_CHUNK_SIZE = settings['optimize_chunks']
    
    return settings

def apply_chunking_preset(preset_name: str) -> Dict[str, Any]:
    """Apply a chunking preset."""
    presets = {
        'fast': ChunkingPresets.fast_processing(),
        'balanced': ChunkingPresets.balanced(),
        'context': ChunkingPresets.high_context(),
        'compliance': ChunkingPresets.compliance_focused()
    }
    
    if preset_name not in presets:
        raise ValueError(f"Unknown chunking preset: {preset_name}")
    
    settings = presets[preset_name]
    
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
        'default_model': ModelConfig.DEFAULT_MODEL,
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
    print(f"Default Model: {ModelConfig.DEFAULT_MODEL}")
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
        model_key = ModelConfig.DEFAULT_MODEL
    
    if model_key not in ModelConfig.MODELS:
        raise ValueError(f"Unknown model: {model_key}. Available: {list(ModelConfig.MODELS.keys())}")
    
    return ModelConfig.MODELS[model_key]

def list_available_models() -> List[str]:
    """Get list of available model keys."""
    return list(ModelConfig.MODELS.keys())

def get_chunking_methods() -> Dict[str, str]:
    """Get available chunking methods with descriptions."""
    return DocumentConfig.CHUNKING_METHODS.copy()

# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================

# For backward compatibility with existing imports
MODELS = ModelConfig.MODELS
DEFAULT_MODEL = ModelConfig.DEFAULT_MODEL
DEFAULT_CHUNK_SIZE = DocumentConfig.DEFAULT_CHUNK_SIZE
DEFAULT_CHUNK_OVERLAP = DocumentConfig.DEFAULT_CHUNK_OVERLAP
PROGRESSIVE_ANALYSIS_ENABLED = ProgressiveConfig.ENABLED
HIGH_RISK_SCORE_THRESHOLD = ProgressiveConfig.HIGH_RISK_THRESHOLD
MEDIUM_RISK_SCORE_THRESHOLD = ProgressiveConfig.MEDIUM_RISK_THRESHOLD

def get_prompt_for_regulation(regulation_framework: str, prompt_type: str) -> str:
    """Legacy function for prompt generation."""
    if prompt_type == "analyze_compliance":
        return f"Analyze this text for compliance with {regulation_framework} requirements."
    elif prompt_type == "contradiction_analysis":
        return "Analyze for contradictions across sections."
    return ""

# =============================================================================
# USAGE EXAMPLES
# =============================================================================

if __name__ == "__main__":
    print_config_summary()
    config = get_current_config()
    print(f"\nCurrent config: {config}")
    
    print(f"\nAvailable chunking methods:")
    for method, description in get_chunking_methods().items():
        print(f"  {method}: {description}")