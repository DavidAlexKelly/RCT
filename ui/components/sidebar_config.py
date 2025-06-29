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
    """Load available regulation frameworks - completely framework agnostic."""
    try:
        analyzer = ComplianceAnalyzer(debug=True)
        frameworks = analyzer.get_available_frameworks()
        
        if not frameworks:
            st.error("❌ No regulation frameworks found!")
            st.error("**Required:** knowledge_base/ directory with valid frameworks")
            
            # Provide completely generic guidance - NO hardcoded framework names
            st.markdown("""
            **Expected structure (works with ANY regulation type):**
            ```
            knowledge_base/
            ├── [framework_name]/
            │   ├── articles.txt
            │   ├── classification.yaml
            │   ├── context.yaml
            │   └── handler.py
            └── [another_framework]/
                ├── articles.txt
                ├── classification.yaml
                ├── context.yaml
                └── handler.py
            ```
            
            **Framework Examples (any regulation works):**
            - `gdpr/` - EU General Data Protection Regulation
            - `hipaa/` - US Healthcare Information Portability
            - `ccpa/` - California Consumer Privacy Act  
            - `food_safety/` - FDA Food Safety Regulations
            - `financial/` - Financial Services Regulations
            - `environmental/` - Environmental Protection Rules
            - `your_custom_framework/` - Any regulatory framework
            """)
            
            st.error("**Action Required:** Set up at least one regulatory framework before using the tool.")
            st.info("💡 The tool is completely framework-agnostic - it works with any regulation type!")
            st.stop()
        
        return frameworks
        
    except Exception as e:
        st.error(f"❌ Critical error loading frameworks: {e}")
        st.error("**The application cannot continue without regulatory frameworks.**")
        
        if st.checkbox("Show technical details", key="framework_error_details"):
            st.exception(e)
        
        st.markdown("""
        **Possible solutions:**
        1. Check that `knowledge_base/` directory exists
        2. Verify framework directories have all required files
        3. Check file permissions and encoding (UTF-8)
        4. Run diagnostic: `python debug_kb.py`
        
        **Framework Structure Requirements:**
        - Each framework must be in its own subdirectory
        - Required files: articles.txt, classification.yaml, context.yaml, handler.py
        - Framework names can be anything (gdpr, hipaa, food_safety, etc.)
        """)
        
        st.stop()

def create_sidebar_config():
    """Create the configuration sidebar and return selected options - framework agnostic."""
    
    st.sidebar.header("🔧 Configuration")
    
    # Load available frameworks with proper error handling (completely dynamic)
    frameworks = load_available_frameworks()
    
    # Create framework options (completely dynamic - no hardcoded frameworks)
    framework_options = {f['id']: f"{f['name']} - {f.get('description', '')}" 
                        for f in frameworks}
    
    # Framework selection (uses whatever frameworks are available)
    selected_framework = st.sidebar.selectbox(
        "🏛️ Regulation Framework",
        options=list(framework_options.keys()),
        format_func=lambda x: framework_options[x],
        help="Choose the regulatory framework to analyze against (completely dynamic based on your knowledge_base/)"
    )
    
    # Model selection with validation
    if not MODELS:
        st.sidebar.error("❌ No models configured in config.py!")
        st.stop()
    
    model_options = {k: f"{v['name']} - {v.get('description', '')}" 
                    for k, v in MODELS.items()}
    
    # Validate default model exists
    if DEFAULT_MODEL not in MODELS:
        st.sidebar.error(f"❌ Default model '{DEFAULT_MODEL}' not found in MODELS configuration!")
        st.sidebar.error(f"Available models: {list(MODELS.keys())}")
        st.stop()
    
    default_index = list(model_options.keys()).index(DEFAULT_MODEL)
    
    selected_model = st.sidebar.selectbox(
        "🤖 Analysis Model",
        options=list(model_options.keys()),
        index=default_index,
        format_func=lambda x: model_options[x],
        help="Select the LLM model for analysis"
    )
    
    # Performance preset with validation
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
    
    # Configuration summary (completely dynamic)
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
    
    # Tips and information (framework agnostic)
    with st.sidebar.expander("💡 Framework Tips"):
        st.markdown("""
        **Framework Agnostic Design:**
        - This tool works with ANY regulatory framework
        - Just add your regulation to knowledge_base/[name]/
        - No code changes needed for new regulations
        
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
        
        **Adding New Frameworks:**
        1. Create knowledge_base/[your_framework]/
        2. Add required files (articles.txt, classification.yaml, etc.)
        3. Framework appears automatically in dropdown
        4. No code changes needed!
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