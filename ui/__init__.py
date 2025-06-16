# ui/__init__.py
"""
Regulatory Compliance Analyzer - Streamlit UI

A user-friendly web interface for the compliance analysis tool.
"""

__version__ = "1.0.0"
__author__ = "Compliance Analyzer Team"

# ui/components/__init__.py
"""
UI Components for the Compliance Analyzer Streamlit App
"""

from .dashboard import create_metrics_dashboard, create_regulation_breakdown_chart
from .file_upload import handle_file_upload, display_file_info
from .results_display import display_findings, display_section_analysis
from .sidebar_config import create_sidebar_config

__all__ = [
    'create_metrics_dashboard',
    'create_regulation_breakdown_chart', 
    'handle_file_upload',
    'display_file_info',
    'display_findings',
    'display_section_analysis',
    'create_sidebar_config'
]

# ui/styles/__init__.py
"""
Custom CSS styles for the Streamlit app
"""

from .custom_css import apply_custom_styles

__all__ = ['apply_custom_styles']

# ui/utils/__init__.py  
"""
Utility functions for the Streamlit UI
"""

from .analysis_runner import run_compliance_analysis, load_knowledge_base
from .export_handler import handle_exports

__all__ = [
    'run_compliance_analysis',
    'load_knowledge_base', 
    'handle_exports'
]