# config/llm_performance.py

"""
LLM Performance Configuration

This file contains all the critical variables that affect LLM performance.
Modify these values to tune the system's accuracy, speed, and cost.

🎯 QUICK TUNING GUIDE:
- For BETTER ACCURACY: Increase RAG_ARTICLES_COUNT, lower PROGRESSIVE_* thresholds
- For FASTER PROCESSING: Decrease RAG_ARTICLES_COUNT, raise PROGRESSIVE_* thresholds  
- For LOWER COSTS: Increase PROGRESSIVE_* thresholds, decrease CHUNK_* sizes
"""

# =============================================================================
# RAG (Retrieval-Augmented Generation) Settings
# =============================================================================

class RAGConfig:
    """Controls what regulatory context the LLM sees."""
    
    # Number of regulation articles to show LLM per document chunk
    # 🔧 KEY LEVER: More articles = better context but longer prompts
    ARTICLES_COUNT = 3  # Current: 3, Suggested: 6-8 for better nuance
    
    # Vector similarity search parameters
    SIMILARITY_THRESHOLD = 0.5  # Minimum similarity score to include article
    ENABLE_RERANKING = False    # Whether to rerank results (slower but more accurate)

# =============================================================================
# Progressive Analysis Settings  
# =============================================================================

class ProgressiveConfig:
    """Controls which document sections get LLM analysis."""
    
    # Risk scoring thresholds (higher = more selective)
    # 🔧 KEY LEVER: Lower thresholds = more sections analyzed = better coverage
    HIGH_RISK_THRESHOLD = 8      # Current: 8, Suggested: 5 for more coverage
    MEDIUM_RISK_THRESHOLD = 3    # Sections scoring above this get analyzed
    LOW_RISK_THRESHOLD = 1       # Sections scoring above this get flagged
    
    # Term scoring weights
    DATA_TERM_WEIGHT = 1         # Weight for data-related terms
    REGULATORY_TERM_WEIGHT = 2   # Weight for regulatory terms  
    HIGH_RISK_PATTERN_WEIGHT = 5 # Weight for high-risk patterns
    
    # Minimum section length to analyze (characters)
    MIN_SECTION_LENGTH = 150     # Skip very short sections
    
    # Enable progressive analysis (if False, analyzes everything)
    ENABLED = True

# =============================================================================
# Document Processing Settings
# =============================================================================

class DocumentConfig:
    """Controls how documents are chunked and processed."""
    
    # Chunk size settings
    # 🔧 KEY LEVER: Larger chunks = more context but may exceed token limits
    DEFAULT_CHUNK_SIZE = 800     # Characters per chunk
    DEFAULT_CHUNK_OVERLAP = 150  # Overlap between chunks
    
    # Chunk size optimization based on document size
    OPTIMIZE_CHUNK_SIZE = True
    SMALL_DOC_THRESHOLD = 10000  # Bytes - use single chunk if smaller
    LARGE_DOC_THRESHOLD = 200000 # Bytes - use smaller chunks if larger
    
    # Maximum chunks to process (prevent runaway costs)
    MAX_CHUNKS_PER_DOCUMENT = 50

# =============================================================================
# LLM Analysis Settings
# =============================================================================

class LLMConfig:
    """Controls LLM behavior and response quality."""
    
    # Response parsing strictness
    # 🔧 KEY LEVER: Stricter = fewer false positives, looser = more coverage
    CITATION_MIN_LENGTH = 10     # Minimum characters for valid citation
    CITATION_MAX_LENGTH = 200    # Maximum characters for valid citation
    
    # Confidence calibration thresholds
    HIGH_CONFIDENCE_TERMS = [
        'indefinitely', 'mandatory', 'required', 'automatic', 
        'no option', 'must accept', 'forced'
    ]
    LOW_CONFIDENCE_TERMS = ['may', 'could', 'possibly', 'potentially']
    
    # Prompt optimization
    MAX_PROMPT_LENGTH = 4000     # Characters - longer prompts may confuse LLM
    INCLUDE_EXAMPLES = False     # Whether to include examples in prompts
    
    # Response validation
    VALIDATE_CITATIONS = True    # Check if citations appear in document
    REQUIRE_ARTICLE_REFERENCES = True  # Require regulation article references

# =============================================================================
# Quality Control Settings
# =============================================================================

class QualityConfig:
    """Controls output quality and validation."""
    
    # Deduplication settings
    SIMILARITY_THRESHOLD_DEDUP = 0.8  # How similar findings need to be to merge
    MAX_ISSUES_PER_SECTION = 10       # Prevent LLM from finding too many issues
    
    # Citation quality requirements
    BUSINESS_TERMS_REQUIRED = 1       # Min business terms in citation
    LEGAL_TERMS_ALLOWED = 0           # Max legal terms in citation
    
    # Article mapping validation
    VALIDATE_ARTICLE_MAPPING = True   # Check if article matches violation type
    
    # Confidence adjustment based on evidence quality
    ADJUST_CONFIDENCE_BY_CITATION = True

# =============================================================================
# Performance Tuning Presets
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
            'validate_citations': True,
            'progressive_enabled': True
        }
    
    @staticmethod
    def speed_focused():
        """Settings optimized for speed (less accurate, cheaper)."""
        return {
            'rag_articles': 3,
            'high_risk_threshold': 12,
            'chunk_size': 600,
            'validate_citations': False,
            'progressive_enabled': True
        }
    
    @staticmethod
    def balanced():
        """Balanced settings (current defaults)."""
        return {
            'rag_articles': 5,
            'high_risk_threshold': 6,
            'chunk_size': 800,
            'validate_citations': True,
            'progressive_enabled': True
        }
    
    @staticmethod
    def comprehensive():
        """Analyze everything (most thorough, most expensive)."""
        return {
            'rag_articles': 10,
            'high_risk_threshold': 1,
            'chunk_size': 1000,
            'validate_citations': True,
            'progressive_enabled': False  # Analyze all sections
        }

# =============================================================================
# Experimental Settings
# =============================================================================

class ExperimentalConfig:
    """Experimental features that may improve performance."""
    
    # Multi-pass analysis
    ENABLE_SECOND_PASS = False   # Re-analyze sections with no findings
    
    # Cross-section analysis  
    ENABLE_CROSS_SECTION = False # Look for contradictions between sections
    
    # Advanced prompting
    ENABLE_CHAIN_OF_THOUGHT = False  # Ask LLM to explain reasoning
    ENABLE_SELF_CORRECTION = False   # Ask LLM to review its own output
    
    # Context enhancement
    INCLUDE_DOCUMENT_METADATA = True  # Include doc type, size, etc. in prompts
    INCLUDE_PREVIOUS_FINDINGS = False # Show LLM findings from previous sections

# =============================================================================
# Helper Functions
# =============================================================================

def apply_preset(preset_name: str):
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

def get_current_config():
    """Get current configuration as a dictionary."""
    return {
        'rag_articles_count': RAGConfig.ARTICLES_COUNT,
        'high_risk_threshold': ProgressiveConfig.HIGH_RISK_THRESHOLD,
        'chunk_size': DocumentConfig.DEFAULT_CHUNK_SIZE,
        'validate_citations': LLMConfig.VALIDATE_CITATIONS,
        'progressive_enabled': ProgressiveConfig.ENABLED,
    }

def print_config_summary():
    """Print a summary of current performance settings."""
    print("🔧 LLM PERFORMANCE CONFIGURATION")
    print("=" * 40)
    print(f"RAG Articles Count: {RAGConfig.ARTICLES_COUNT}")
    print(f"High Risk Threshold: {ProgressiveConfig.HIGH_RISK_THRESHOLD}")
    print(f"Chunk Size: {DocumentConfig.DEFAULT_CHUNK_SIZE}")
    print(f"Progressive Analysis: {'Enabled' if ProgressiveConfig.ENABLED else 'Disabled'}")
    print(f"Citation Validation: {'Enabled' if LLMConfig.VALIDATE_CITATIONS else 'Disabled'}")
    print("=" * 40)

# =============================================================================
# Usage Examples
# =============================================================================

if __name__ == "__main__":
    # Example: Apply accuracy-focused preset
    # apply_preset('accuracy')
    
    # Example: Print current configuration
    print_config_summary()
    
    # Example: Get config as dict
    config = get_current_config()
    print(f"Current config: {config}")