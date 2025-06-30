import streamlit as st
import sys
from pathlib import Path

# Add parent directory for imports
current_dir = Path(__file__).parent.parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from config import MODELS, DEFAULT_MODEL, PRESETS
from engine import ComplianceAnalyser

def load_available_frameworks():
    """Load available regulation frameworks."""
    try:
        analyser = ComplianceAnalyser(debug=False)
        frameworks = analyser.get_available_frameworks()
        
        if not frameworks:
            st.error("❌ No regulation frameworks found!")
            st.markdown("""
            **Required structure:**
            ```
            knowledge_base/
            ├── [framework_name]/
            │   ├── articles.txt
            │   ├── context.yaml
            │   └── handler.py
            ```
            """)
            st.stop()
        
        return frameworks
        
    except Exception as e:
        st.error(f"❌ Error loading frameworks: {e}")
        st.stop()

def create_sidebar_config():
    """Create clean, simplified configuration sidebar."""
    
    st.sidebar.header("🔧 Configuration")
    
    # Load frameworks
    frameworks = load_available_frameworks()
    framework_options = {f['id']: f"{f['name']} - {f.get('description', '')}" 
                        for f in frameworks}
    
    # Framework selection
    selected_framework = st.sidebar.selectbox(
        "🏛️ Regulation Framework",
        options=list(framework_options.keys()),
        format_func=lambda x: framework_options[x],
        help="Choose regulatory framework for analysis"
    )
    
    # Model selection
    model_options = {k: f"{v['name']} - {v.get('description', '')}" 
                    for k, v in MODELS.items()}
    
    selected_model = st.sidebar.selectbox(
        "🤖 Analysis Model",
        options=list(model_options.keys()),
        index=list(model_options.keys()).index(DEFAULT_MODEL),
        format_func=lambda x: model_options[x],
        help="Select LLM model for analysis"
    )
    
    # Simple preset selection
    preset_options = {
        'balanced': '⚖️ Balanced - Recommended for most documents',
        'thorough': '🔍 Thorough - More comprehensive analysis',
        'speed': '⚡ Fast - Quick analysis for large documents'
    }
    
    selected_preset = st.sidebar.selectbox(
        "⚙️ Analysis Mode",
        options=list(preset_options.keys()),
        format_func=lambda x: preset_options[x],
        help="Choose analysis approach"
    )
    
    # Document processing (simplified)
    with st.sidebar.expander("📄 Document Settings"):
        chunking_method = st.selectbox(
            "Document Processing",
            options=["smart", "paragraph", "simple"],
            index=0,
            help="How to break up the document",
            format_func=lambda x: {
                "smart": "Smart - Auto-detect sections (recommended)",
                "paragraph": "Paragraph - Group by paragraphs", 
                "simple": "Simple - Fixed-size chunks"
            }[x]
        )
        
        chunk_size = st.slider("Section Size", 600, 1200, 800, 100,
                              help="Size of document sections for analysis")
    
    # Advanced options (minimal)
    with st.sidebar.expander("🔬 Advanced"):
        debug_mode = st.checkbox("Debug Mode", False,
                                help="Show detailed technical information")
        
        rag_articles = st.slider("Regulations per Section", 3, 8, 5,
                                help="Number of relevant regulations to consider per section")
    
    # Simple status display
    with st.sidebar.expander("📊 Configuration Summary"):
        st.code(f"""Framework: {selected_framework}
Model: {selected_model}
Mode: {selected_preset}
Processing: {chunking_method}
Section Size: {chunk_size} chars
Regulations: {rag_articles} per section""")
    
    # Usage tips (simplified)
    with st.sidebar.expander("💡 Tips"):
        st.markdown("""
        **📋 Document Types:**
        - Privacy policies and terms of service
        - Compliance procedures and manuals
        - Business proposals and contracts
        - Technical documentation
        
        **⚙️ Analysis Modes:**
        - **Balanced**: Good for most documents
        - **Thorough**: Detailed analysis, slower
        - **Fast**: Quick review for large documents
        
        **📊 Best Practices:**
        - Upload clear, text-based documents
        - Avoid scanned images when possible
        - Larger sections work better for context
        """)
    
    # Get defaults for hidden settings
    preset_config = PRESETS.get(selected_preset, PRESETS['balanced'])
    
    return {
        "framework": selected_framework,
        "model": selected_model,
        "preset": selected_preset,
        "debug_mode": debug_mode,
        "rag_articles": rag_articles,
        "chunking_method": chunking_method,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_size // 8,  # Auto-calculate overlap
        # Hidden progressive analysis settings (use preset defaults)
        "enable_progressive": True,  # Always enabled
        "topic_threshold": preset_config.get('topic_threshold', 2.0)
    }