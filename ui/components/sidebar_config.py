import streamlit as st
import sys
from pathlib import Path

# Add parent directory for imports
current_dir = Path(__file__).parent.parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from config import MODELS, DEFAULT_MODEL, PRESETS, config
from engine import ComplianceAnalyzer

def load_available_frameworks():
    """Load available regulation frameworks."""
    try:
        analyzer = ComplianceAnalyzer(debug=False)
        frameworks = analyzer.get_available_frameworks()
        
        if not frameworks:
            st.error("❌ No regulation frameworks found!")
            st.markdown("""
            **Required structure:**
            ```
            knowledge_base/
            ├── [framework_name]/
            │   ├── articles.txt
            │   ├── classification.yaml
            │   ├── context.yaml
            │   └── handler.py
            ```
            **Examples:** gdpr/, hipaa/, ccpa/, food_safety/, etc.
            """)
            st.stop()
        
        return frameworks
        
    except Exception as e:
        st.error(f"❌ Error loading frameworks: {e}")
        st.error("Check that knowledge_base/ directory exists with valid frameworks")
        st.stop()

def create_sidebar_config():
    """Create configuration sidebar and return selected options."""
    
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
    
    # Performance preset
    preset_options = {
        'balanced': '⚖️ Balanced - Good speed and accuracy',
        'accuracy': '🎯 Accuracy - Best quality, slower',
        'speed': '⚡ Speed - Fastest, less thorough',
        'comprehensive': '🔍 Comprehensive - Analyze everything'
    }
    
    selected_preset = st.sidebar.selectbox(
        "⚙️ Performance Preset",
        options=list(preset_options.keys()),
        format_func=lambda x: preset_options[x],
        help="Choose analysis approach"
    )
    
    # Document processing
    with st.sidebar.expander("📄 Document Processing"):
        chunking_method = st.selectbox(
            "Chunking Method",
            options=["smart", "paragraph", "sentence", "simple"],
            index=0,
            help="How to break up the document",
            format_func=lambda x: {
                "smart": "Smart - Auto-detect sections",
                "paragraph": "Paragraph - Group by paragraphs", 
                "sentence": "Sentence - Group by sentences",
                "simple": "Simple - Character-based"
            }[x]
        )
        
        chunk_size = st.slider("Chunk Size", 400, 2000, config.chunk_size, 50)
        chunk_overlap = st.slider("Chunk Overlap", 0, 200, config.chunk_overlap, 25)
        optimize_chunks = st.checkbox("Auto-optimize for document size", True)
    
    # Advanced options
    with st.sidebar.expander("🔬 Advanced Options"):
        enable_progressive = st.checkbox("Enable Progressive Analysis", True)
        debug_mode = st.checkbox("Debug Mode", False)
        
        st.markdown("#### RAG Settings")
        rag_articles = st.slider("RAG Articles Count", 1, 10, config.rag_articles)
        
        st.markdown("#### Progressive Analysis")
        risk_threshold = st.slider("High Risk Threshold", 1, 20, config.high_risk_threshold)
    
    # Configuration summary
    with st.sidebar.expander("📊 Current Configuration"):
        st.code(f"""Framework: {selected_framework}
Model: {selected_model}
Preset: {selected_preset}
Progressive: {enable_progressive}

Chunking: {chunking_method}
Size: {chunk_size} chars
Overlap: {chunk_overlap} chars

RAG Articles: {rag_articles}
Risk Threshold: {risk_threshold}""")
    
    # Tips
    with st.sidebar.expander("💡 Tips"):
        st.markdown("""
        **Framework Agnostic:**
        - Works with ANY regulatory framework
        - Add your regulation to knowledge_base/[name]/
        - No code changes needed
        
        **Performance:**
        - **Speed**: Fast analysis, basic accuracy
        - **Balanced**: Good for most documents  
        - **Accuracy**: Thorough analysis, slower
        - **Comprehensive**: Analyze everything
        
        **Chunking:**
        - **Smart**: Best for structured documents
        - **Paragraph**: Good for contracts/policies
        - **Sentence**: Fine control
        - **Simple**: Basic character splitting
        """)
    
    return {
        "framework": selected_framework,
        "model": selected_model,
        "preset": selected_preset,
        "enable_progressive": enable_progressive,
        "debug_mode": debug_mode,
        "rag_articles": rag_articles,
        "risk_threshold": risk_threshold,
        "chunking_method": chunking_method,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "optimize_chunks": optimize_chunks
    }