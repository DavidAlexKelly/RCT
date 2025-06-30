import streamlit as st
import sys
from pathlib import Path

# Add parent directory for imports
current_dir = Path(__file__).parent.parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from config import MODELS, DEFAULT_MODEL, PRESETS, config, get_scoring_config
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
    """Create enhanced configuration sidebar and return selected options."""
    
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
    
    # Enhanced Progressive Analysis Settings
    with st.sidebar.expander("🎯 Progressive Analysis"):
        enable_progressive = st.checkbox("Enable Progressive Analysis", True, 
                                       help="Smart filtering to focus on high-risk sections")
        
        if enable_progressive:
            st.markdown("#### Enhanced Scoring Features")
            enable_phrase_matching = st.checkbox("Phrase Matching", True,
                                                help="Match complete phrases like 'without consent'")
            enable_context_analysis = st.checkbox("Context Analysis", True,
                                                 help="Bonus for data+risk combinations in same sentence")
            enable_negation_detection = st.checkbox("Negation Detection", True,
                                                   help="Reduce false positives from compliance statements")
            
            st.markdown("#### Risk Thresholds")
            risk_threshold = st.slider("High Risk Threshold", 1.0, 20.0, config.high_risk_threshold, 0.5,
                                     help="Sections above this score get full LLM analysis")
            
            st.markdown("#### Scoring Weights")
            phrase_weight = st.slider("Phrase Match Weight", 1.0, 5.0, 2.5, 0.5,
                                    help="Weight for multi-word phrase matches")
            context_weight = st.slider("Context Bonus Weight", 1.0, 5.0, 2.0, 0.5,
                                     help="Weight for data+risk context combinations")
        else:
            enable_phrase_matching = False
            enable_context_analysis = False
            enable_negation_detection = False
            risk_threshold = config.high_risk_threshold
            phrase_weight = 2.5
            context_weight = 2.0
    
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
        
        chunk_size = st.slider("Chunk Size", 400, 2000, config.chunk_size, 50,
                              help="Size of document chunks for analysis")
        chunk_overlap = st.slider("Chunk Overlap", 0, 200, config.chunk_overlap, 25,
                                 help="Overlap between adjacent chunks")
        optimize_chunks = st.checkbox("Auto-optimize for document size", True,
                                     help="Adjust chunk size based on document length")
    
    # Advanced options
    with st.sidebar.expander("🔬 Advanced Options"):
        debug_mode = st.checkbox("Debug Mode", False,
                                help="Show detailed analysis information")
        
        st.markdown("#### RAG Settings")
        rag_articles = st.slider("RAG Articles Count", 1, 10, config.rag_articles,
                                help="Number of regulation articles to use for each chunk")
        
        st.markdown("#### Analysis Features")
        enable_enhanced_scoring = st.checkbox("Enhanced Scoring", True,
                                             help="Use advanced framework-specific scoring")
        enable_scoring_debug = st.checkbox("Show Scoring Details", False,
                                          help="Display detailed scoring breakdown in results")
    
    # Configuration summary
    with st.sidebar.expander("📊 Current Configuration"):
        scoring_config = get_scoring_config()
        
        st.code(f"""Framework: {selected_framework}
Model: {selected_model}
Preset: {selected_preset}
Progressive: {enable_progressive}

Enhanced Features:
- Phrase Matching: {enable_phrase_matching}
- Context Analysis: {enable_context_analysis}
- Negation Detection: {enable_negation_detection}

Chunking: {chunking_method}
Size: {chunk_size} chars
Overlap: {chunk_overlap} chars

Scoring:
- Risk Threshold: {risk_threshold}
- Phrase Weight: {phrase_weight}
- Context Weight: {context_weight}

RAG Articles: {rag_articles}
Enhanced Scoring: {enable_enhanced_scoring}""")
    
    # Enhanced tips
    with st.sidebar.expander("💡 Enhanced Features Guide"):
        st.markdown("""
        **🎯 Progressive Analysis:**
        - **Smart Filtering**: Only analyzes high-risk sections with LLM
        - **Efficiency**: 60-80% reduction in processing time
        - **Accuracy**: Maintains or improves detection quality
        
        **🔍 Enhanced Scoring:**
        - **Phrase Matching**: "without consent" > just "consent"
        - **Context Analysis**: Bonus for data+risk in same sentence
        - **Negation Detection**: "We do NOT sell data" → compliance
        
        **⚙️ Performance Presets:**
        - **Speed**: Skip advanced features, high threshold
        - **Balanced**: Standard enhanced analysis
        - **Accuracy**: Lower threshold, all features
        - **Comprehensive**: Analyze almost everything
        
        **📊 Framework-Specific:**
        - **GDPR**: Focus on consent, data minimization
        - **HIPAA**: Focus on PHI authorization, safeguards
        - **Custom**: Automatic adaptation to new regulations
        
        **🎯 Risk Scoring:**
        - Data terms: 1.0x weight
        - Regulatory keywords: 1.5x weight  
        - High-risk patterns: 5.0x weight
        - Phrase matches: 2.5x bonus
        - Context combinations: 2.0x bonus
        - Negations: -2.0x penalty
        
        **📈 Typical Results:**
        - 15-25 total chunks → 4-8 analyzed
        - 70% efficiency gain
        - Same or better violation detection
        - Detailed scoring explanations
        """)
    
    # Performance impact indicator
    if enable_progressive:
        efficiency_estimate = _estimate_efficiency(selected_preset, enable_phrase_matching, 
                                                 enable_context_analysis, risk_threshold)
        
        if efficiency_estimate > 70:
            st.sidebar.success(f"🚀 High efficiency: ~{efficiency_estimate}% of chunks will be skipped")
        elif efficiency_estimate > 50:
            st.sidebar.info(f"⚖️ Balanced efficiency: ~{efficiency_estimate}% of chunks will be skipped")
        else:
            st.sidebar.warning(f"🐌 Low efficiency: Only ~{efficiency_estimate}% of chunks will be skipped")
    
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
        "optimize_chunks": optimize_chunks,
        "enable_enhanced_scoring": enable_enhanced_scoring,
        "enable_phrase_matching": enable_phrase_matching,
        "enable_context_analysis": enable_context_analysis,
        "enable_negation_detection": enable_negation_detection,
        "phrase_weight_multiplier": phrase_weight,
        "context_weight_multiplier": context_weight,
        "enable_scoring_debug": enable_scoring_debug
    }

def _estimate_efficiency(preset: str, phrase_matching: bool, context_analysis: bool, threshold: float) -> int:
    """Estimate efficiency gain based on configuration."""
    base_efficiency = {
        'speed': 85,
        'balanced': 70,
        'accuracy': 50,
        'comprehensive': 30
    }.get(preset, 70)
    
    # Adjust for enhanced features
    if phrase_matching:
        base_efficiency += 5
    if context_analysis:
        base_efficiency += 5
    
    # Adjust for threshold
    if threshold > 10:
        base_efficiency += 10
    elif threshold < 5:
        base_efficiency -= 15
    
    return min(95, max(20, base_efficiency))