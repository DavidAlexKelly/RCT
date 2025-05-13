# utils/regulation_handler_base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class RegulationHandlerBase(ABC):
    """
    Abstract base class for regulation-specific handlers.
    Any regulation framework should implement this interface.
    """
    
    def __init__(self, debug=False):
        """Initialize the regulation handler."""
        self.debug = debug
    
    @abstractmethod
    def extract_content_indicators(self, text: str) -> Dict[str, str]:
        """
        Extract content indicators from text.
        
        Args:
            text: Document text to analyze
            
        Returns:
            Dictionary of indicators
        """
        pass
    
    @abstractmethod
    def extract_potential_violations(self, text: str, patterns_text: str) -> List[Dict[str, Any]]:
        """
        Extract potential violation patterns from text.
        
        Args:
            text: Document text to analyze
            patterns_text: Text containing pattern definitions
            
        Returns:
            List of potential violations
        """
        pass
    
    @abstractmethod
    def create_analysis_prompt(self, text: str, section: str, regulations: str,
                              content_indicators: Optional[Dict[str, str]] = None,
                              potential_violations: Optional[List[Dict[str, Any]]] = None,
                              regulation_framework: str = "",
                              risk_level: str = "unknown") -> str:
        """
        Create a regulation-specific analysis prompt.
        
        Args:
            text: Document text to analyze
            section: Section identifier
            regulations: Formatted regulations text
            content_indicators: Dictionary of content indicators
            potential_violations: List of potential violations
            regulation_framework: Name of the regulation framework
            risk_level: Risk level of the section (high, medium, low)
            
        Returns:
            Analysis prompt for LLM
        """
        pass
        
    @abstractmethod
    def format_regulations(self, regulations: List[Dict[str, Any]], 
                         regulation_context: str = "",
                         regulation_patterns: str = "") -> str:
        """
        Format regulations for prompt.
        
        Args:
            regulations: List of regulations
            regulation_context: Context about the regulation framework
            regulation_patterns: Common violation patterns
            
        Returns:
            Formatted regulations text
        """
        pass