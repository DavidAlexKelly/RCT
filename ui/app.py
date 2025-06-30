import streamlit as st
import sys
import os
from pathlib import Path

# Add the parent directory to the Python path so we can import from the main project
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Import UI components directly (avoid __init__.py issues)
from components.dashboard import create_metrics_dashboard, create_regulation_breakdown_chart
from components.file_upload import handle_file_upload, display_file_info
from components.results_display import display_findings, display_section_analysis
from components.sidebar_config import create_sidebar_config
from styles.custom_css import apply_custom_styles
from ui_utils.analysis_runner import run_compliance_analysis
from ui_utils.export_handler import handle_exports

def main():
    """Main Streamlit application."""
    
    # Page configuration
    st.set_page_config(
        page_title="Regulatory Compliance Analyser",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Apply custom styles
    apply_custom_styles()
    
    # Header
    st.markdown('''
    <h1 class="main-header">⚖️ Regulatory Compliance Analyser</h1>
    <p class="sub-header">Intelligent document analysis for regulatory compliance across multiple frameworks</p>
    ''', unsafe_allow_html=True)
    
    # Sidebar configuration
    config = create_sidebar_config()
    
    # File upload section
    st.header("📁 Document Upload")
    uploaded_file = handle_file_upload()
    
    if uploaded_file is not None:
        # Display file information
        display_file_info(uploaded_file)
        
        # Analysis button
        if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
            # Run the analysis
            results = run_compliance_analysis(uploaded_file, config)
            
            if results:
                # Store results in session state
                st.session_state.analysis_results = results
    
    # Display results if available
    if "analysis_results" in st.session_state:
        results = st.session_state.analysis_results
        
        # Metrics dashboard (no header or summary cards)
        create_metrics_dashboard(results["findings"], results["config"])
        
        # Charts
        col1, col2 = st.columns(2)
        with col1:
            create_regulation_breakdown_chart(results["findings"])
        
        with col2:
            display_simple_analysis_info(results)
        
        # Detailed findings
        st.header("🔍 Detailed Findings")
        
        tab1, tab2 = st.tabs(["📋 Issues by Regulation", "📄 Section Analysis"])
        
        with tab1:
            display_findings(results["findings"], results["chunk_results"])
        
        with tab2:
            display_section_analysis(results["chunk_results"])
        
        # Export options
        st.header("📤 Export Results")
        handle_exports(results, uploaded_file)

def display_simple_analysis_info(results):
    """Display simple analysis information without technical details."""
    st.subheader("📈 Analysis Details")
    
    config = results["config"]
    metadata = results["metadata"]
    
    # Simple, user-friendly information
    info_data = {
        "Framework": config["framework"].upper(),
        "Model": config["model"].title(),
        "Analysis Mode": config["preset"].title(),
        "Document Type": metadata.get("document_type", "Unknown").replace('_', ' ').title(),
        "Total Sections": config["total_sections"],
        "Total Issues": len(results["findings"])
    }
    
    for key, value in info_data.items():
        st.metric(key, value)

if __name__ == "__main__":
    main()