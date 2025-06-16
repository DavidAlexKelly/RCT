# config.py

"""
Unified Configuration for Compliance Analysis Tool - Framework Agnostic Version

🎯 QUICK TUNING GUIDE:
- For BETTER ACCURACY: Increase RAG_ARTICLES_COUNT, lower PROGRESSIVE_* thresholds
- For FASTER PROCESSING: Decrease RAG_ARTICLES_COUNT, raise PROGRESSIVE_* thresholds  
- For LOWER COSTS: Increase PROGRESSIVE_* thresholds, decrease CHUNK_* sizes
"""

from typing import Dict, Any, List

# =============================================================================
# VERSION & METADATA
# =============================================================================

CONFIG_VERSION = "2.2.0"  # Updated for framework-agnostic version
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
# DOCUMENT PROCESSING SETTINGS
# =============================================================================

class DocumentConfig:
    """Controls how documents are chunked and processed."""
    
    # Chunk size settings
    DEFAULT_CHUNK_SIZE = 800
    DEFAULT_CHUNK_OVERLAP = 150
    
    # Chunk size optimization based on document size
    OPTIMIZE_CHUNK_SIZE = True
    SMALL_DOC_THRESHOLD = 10000
    LARGE_DOC_THRESHOLD = 200000
    
    # Maximum chunks to process (prevent runaway costs)
    MAX_CHUNKS_PER_DOCUMENT = 50

# =============================================================================
# LLM ANALYSIS SETTINGS - SIMPLIFIED (NO VALIDATION)
# =============================================================================

class LLMConfig:
    """Controls LLM behavior and response quality - simplified version."""
    
    # Citation handling - very permissive, no validation
    CITATION_MIN_LENGTH = 3      # Very short minimum
    CITATION_MAX_LENGTH = 1000   # Very long maximum
    
    # VALIDATION DISABLED FOR SIMPLICITY
    VALIDATE_CITATIONS = False           # No citation validation
    REQUIRE_ARTICLE_REFERENCES = False   # No article reference requirements
    
    # Framework-agnostic confidence terms
    HIGH_CONFIDENCE_TERMS = [
        'mandatory', 'required', 'must', 'shall', 'prohibited', 'forbidden',
        'illegal', 'unauthorized', 'violation', 'breach', 'non-compliant'
    ]
    LOW_CONFIDENCE_TERMS = [
        'may', 'could', 'possibly', 'potentially', 'might', 'appears',
        'seems', 'suggests', 'unclear', 'ambiguous'
    ]
    
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
    ADJUST_CONFIDENCE_BY_CITATION = False  # No citation-based adjustment

# =============================================================================
# FRAMEWORK-AGNOSTIC DATA TERMS & KEYWORDS
# =============================================================================

class TermsConfig:
    """Generic data terms and regulatory keywords for all frameworks."""
    
    # Generic terms that apply across regulatory frameworks
    DATA_TERMS = [
        "information", "data", "record", "file", "database", "document",
        "entity", "individual", "organization", "business", "system",
        "collection", "storage", "processing", "handling", "management"
    ]
    
    # Generic regulatory keywords
    REGULATORY_KEYWORDS = [
        "compliance", "regulation", "legal", "lawful", "requirement",
        "standard", "rule", "policy", "procedure", "guideline",
        "obligation", "responsibility", "mandate", "violation",
        "breach", "audit", "inspection", "assessment", "review",
        "authorization", "approval", "permit", "license"
    ]
    
    # Framework-agnostic high risk patterns
    HIGH_RISK_PATTERNS = [
        "non-compliant", "violation", "breach", "illegal", "unauthorized",
        "improper", "inadequate", "insufficient", "failed", "missing"
    ]
    
    # Priority keywords for enhanced weighting
    PRIORITY_KEYWORDS = [
        "compliance", "violation", "breach", "requirement", "standard"
    ]

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

# =============================================================================
# PERFORMANCE TUNING PRESETS
# =============================================================================

class PerformancePresets:
    """Pre-configured settings for different use cases."""
    
    @staticmethod
    def accuracy_focused():
        """Settings optimized for maximum accuracy (slower, more expensive)."""
        return {
            'rag_articles': 8,
            'high_risk_threshold': 3,
            'chunk_size': 1200,
            'validate_citations': False,  # Simplified
            'progressive_enabled': True
        }
    
    @staticmethod
    def speed_focused():
        """Settings optimized for speed (less accurate, cheaper)."""
        return {
            'rag_articles': 3,
            'high_risk_threshold': 12,
            'chunk_size': 600,
            'validate_citations': False,  # Simplified
            'progressive_enabled': True
        }
    
    @staticmethod
    def balanced():
        """Balanced settings (current defaults)."""
        return {
            'rag_articles': 5,
            'high_risk_threshold': 6,
            'chunk_size': 800,
            'validate_citations': False,  # Simplified
            'progressive_enabled': True
        }
    
    @staticmethod
    def comprehensive():
        """Analyze everything (most thorough, most expensive)."""
        return {
            'rag_articles': 10,
            'high_risk_threshold': 1,
            'chunk_size': 1000,
            'validate_citations': False,  # Simplified
            'progressive_enabled': False
        }

# =============================================================================
# HELPER FUNCTIONS
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
    DocumentConfig.DEFAULT_CHUNK_SIZE = settings['chunk_size']
    LLMConfig.VALIDATE_CITATIONS = settings['validate_citations']
    ProgressiveConfig.ENABLED = settings['progressive_enabled']
    
    return settings

def get_current_config() -> Dict[str, Any]:
    """Get current configuration as a dictionary."""
    return {
        'rag_articles_count': RAGConfig.ARTICLES_COUNT,
        'high_risk_threshold': ProgressiveConfig.HIGH_RISK_THRESHOLD,
        'chunk_size': DocumentConfig.DEFAULT_CHUNK_SIZE,
        'validate_citations': LLMConfig.VALIDATE_CITATIONS,
        'progressive_enabled': ProgressiveConfig.ENABLED,
        'default_model': ModelConfig.DEFAULT_MODEL,
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
    print(f"Chunk Size: {DocumentConfig.DEFAULT_CHUNK_SIZE}")
    print(f"Progressive Analysis: {'Enabled' if ProgressiveConfig.ENABLED else 'Disabled'}")
    print(f"Citation Validation: {'Enabled' if LLMConfig.VALIDATE_CITATIONS else 'Disabled'}")
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
DATA_TERMS = TermsConfig.DATA_TERMS

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