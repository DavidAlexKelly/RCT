import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
current_dir = Path(__file__).parent.parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from config import MODELS, DEFAULT_MODEL, RAGConfig, ProgressiveConfig
from engine import ComplianceAnalyzer

def load_available_frameworks():
    """Load available regulation frameworks using the unified engine."""
    try:
        analyzer = ComplianceAnalyzer()
        return analyzer.get_available_frameworks()
    except Exception as e:
        st.error(f"Error loading frameworks: {e}")
        return [{"id": "gdpr", "name": "GDPR", "description": "General Data Protection Regulation"}]

def create_sidebar_config():
    """Create the configuration sidebar and return selected options."""
    
    st.sidebar.header("🔧 Configuration")
    
    # Load available frameworks
    frameworks = load_available_frameworks()
    framework_options = {f['id']: f"{f['name']} - {f.get('description', '')}" 
                        for f in frameworks}
    
    if not framework_options:
        st.sidebar.error("❌ No regulation frameworks found!")
        st.sidebar.info("Make sure the knowledge_base directory exists with regulation frameworks.")
        return None
    
    # Framework selection
    selected_framework = st.sidebar.selectbox(
        "🏛️ Regulation Framework",
        options=list(framework_options.keys()),
        format_func=lambda x: framework_options[x],
        help="Choose the regulatory framework to analyze against"
    )
    
    # Model selection
    model_options = {k: f"{v['name']} - {v.get('description', '')}" 
                    for k, v in MODELS.items()}
    selected_model = st.sidebar.selectbox(
        "🤖 Analysis Model",
        options=list(model_options.keys()),
        index=list(model_options.keys()).index(DEFAULT_MODEL),
        format_func=lambda x: model_options[x],
        help="Select the LLM model for analysis"
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
    
    # Document Processing Section
    with st.sidebar.expander("📄 Document Processing", expanded=False):
        st.markdown("**Chunking Strategy**")
        
        chunking_method = st.selectbox(
            "Chunking Method",
            options=["smart", "paragraph", "sentence", "simple"],
            index=0,
            help="How to break up the document into chunks",
            format_func=lambda x: {
                "smart": "Smart - Detect sections, fallback to paragraphs",
                "paragraph": "Paragraph - Group by paragraphs", 
                "sentence": "Sentence - Group by sentences",
                "simple": "Simple - Character-based with word boundaries"
            }[x]
        )
        
        chunk_size = st.slider(
            "Target Chunk Size (characters)", 
            min_value=400, 
            max_value=2000, 
            value=800,
            step=50,
            help="Target size of document chunks for analysis"
        )
        
        chunk_overlap = st.slider(
            "Chunk Overlap", 
            min_value=0, 
            max_value=200, 
            value=100,
            step=25,
            help="Overlap between adjacent chunks to preserve context"
        )
        
        optimize_chunks = st.checkbox(
            "Auto-optimize for document size", 
            value=True,
            help="Automatically adjust chunk sizes based on document length"
        )
        
        # Show chunk size estimation
        if chunk_size and chunk_overlap:
            estimated_chunks_per_1000_chars = max(1, 1000 // (chunk_size - chunk_overlap))
            st.info(f"📊 ~{estimated_chunks_per_1000_chars} chunks per 1000 characters")
    
    # Advanced options in an expander
    with st.sidebar.expander("🔬 Advanced Options"):
        enable_progressive = st.checkbox(
            "Enable Progressive Analysis", 
            value=True,
            help="Intelligently skip low-risk sections to improve speed"
        )
        
        debug_mode = st.checkbox(
            "Debug Mode", 
            value=False,
            help="Show detailed debug information during analysis"
        )
        
        st.markdown("#### RAG Settings")
        rag_articles = st.slider(
            "RAG Articles Count", 
            min_value=1, 
            max_value=10, 
            value=RAGConfig.ARTICLES_COUNT,
            help="Number of regulation articles to show the LLM"
        )
        
        st.markdown("#### Progressive Analysis")
        risk_threshold = st.slider(
            "High Risk Threshold", 
            min_value=1, 
            max_value=20, 
            value=ProgressiveConfig.HIGH_RISK_THRESHOLD,
            help="Threshold for classifying sections as high-risk"
        )
    
    # Configuration summary
    with st.sidebar.expander("📊 Current Configuration"):
        st.code(f"""
Framework: {selected_framework}
Model: {selected_model}
Preset: {selected_preset}
Progressive: {enable_progressive}

Document Processing:
- Method: {chunking_method}
- Size: {chunk_size} chars
- Overlap: {chunk_overlap} chars
- Auto-optimize: {optimize_chunks}

Analysis:
- RAG Articles: {rag_articles}
- Risk Threshold: {risk_threshold}
        """)
    
    # Tips and information
    with st.sidebar.expander("💡 Chunking Tips"):
        st.markdown("""
        **Chunking Methods:**
        - **Smart**: Best for most documents - detects structure automatically
        - **Paragraph**: Good for flowing text like contracts
        - **Sentence**: Fine control for complex documents
        - **Simple**: Basic character splitting
        
        **Chunk Size Guidelines:**
        - **400-800**: Fast processing, good for simple documents
        - **800-1200**: Balanced approach for most use cases
        - **1200-2000**: Better context for complex compliance documents
        
        **Overlap Benefits:**
        - Preserves context across chunk boundaries
        - Helps catch violations spanning multiple paragraphs
        - 50-150 characters usually sufficient
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