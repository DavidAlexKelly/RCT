"""
Regulatory Compliance Analyzer

AI-powered document analysis tool for regulatory compliance checking.
"""

__version__ = "1.0.0"
__author__ = "Compliance Analyzer Team" 
__email__ = "team@compliance-analyzer.com"

# Package information
__title__ = "regulatory-compliance-analyzer"
__description__ = "AI-powered document analysis tool for regulatory compliance checking"
__url__ = "https://github.com/your-org/compliance-analyzer"

# Import main classes for easier access
try:
    from .utils.document_processor import DocumentProcessor
    from .utils.embeddings_handler import EmbeddingsHandler  
    from .utils.llm_handler import LLMHandler
    from .utils.progressive_analyzer import ProgressiveAnalyzer
    from .utils.prompt_manager import PromptManager
    from .utils.report_generator import ReportGenerator
    
    # Import configuration
    from .config import (
        MODELS, DEFAULT_MODEL,
        apply_preset, get_current_config,
        DocumentConfig, ProgressiveConfig, RAGConfig
    )
    
    # Make key classes available at package level
    __all__ = [
        "DocumentProcessor",
        "EmbeddingsHandler", 
        "LLMHandler",
        "ProgressiveAnalyzer",
        "PromptManager",
        "ReportGenerator",
        "MODELS",
        "DEFAULT_MODEL", 
        "apply_preset",
        "get_current_config",
        "DocumentConfig",
        "ProgressiveConfig", 
        "RAGConfig"
    ]
    
except ImportError:
    # If imports fail, define minimal interface
    __all__ = []
    
    import warnings
    warnings.warn(
        "Some modules could not be imported. "
        "Please ensure all dependencies are installed.",
        ImportWarning
    )

# Logging configuration
import logging

def setup_logging(level=logging.INFO, format_string=None):
    """
    Setup logging for the compliance analyzer.
    
    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=[
            logging.StreamHandler(),
            # Optionally add file handler
            # logging.FileHandler('compliance_analyzer.log')
        ]
    )
    
    # Set specific loggers to appropriate levels
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# Package metadata
def get_version():
    """Get the package version."""
    return __version__

def get_info():
    """Get package information."""
    return {
        "name": __title__,
        "version": __version__, 
        "description": __description__,
        "author": __author__,
        "url": __url__
    }