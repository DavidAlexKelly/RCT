# ui/components/sidebar_config.py

import streamlit as st
import os
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
current_dir = Path(__file__).parent.parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from config import MODELS, DEFAULT_MODEL, RAGConfig, ProgressiveConfig

def load_available_frameworks():
    """Load available regulation frameworks from the knowledge base."""
    try:
        # Get the knowledge base directory relative to the project root
        project_root = Path(__file__).parent.parent.parent
        knowledge_base_dir = project_root / "knowledge_base"
        index_path = knowledge_base_dir / "regulation_index.json"
        
        if index_path.exists():
            with open(index_path, 'r') as f:
                index_data = json.load(f)
                return index_data.get("frameworks", [])
        else:
            # Fallback - scan directories
            frameworks = []
            if knowledge_base_dir.exists():
                for item in knowledge_base_dir.iterdir():
                    if item.is_dir() and item.name != "__pycache__":
                        frameworks.append({
                            "id": item.name,
                            "name": item.name.upper(),
                            "description": f"{item.name.upper()} compliance framework"
                        })
            return frameworks
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
        
        chunk_size = st.slider(
            "Chunk Size",
            min_value=400,
            max_value=1500,
            value=800,
            step=50,
            help="Size of document chunks for analysis"
        )
    
    # Configuration summary
    with st.sidebar.expander("📊 Current Configuration"):
        st.code(f"""
Framework: {selected_framework}
Model: {selected_model}
Preset: {selected_preset}
Progressive: {enable_progressive}
RAG Articles: {rag_articles}
Risk Threshold: {risk_threshold}
Chunk Size: {chunk_size}
        """)
    
    # Tips and information
    with st.sidebar.expander("💡 Tips"):
        st.markdown("""
        **For Best Results:**
        - Use 'Accuracy' preset for final reports
        - Use 'Speed' preset for quick checks
        - Enable debug mode if analysis fails
        - Larger documents work better with progressive analysis
        
        **Performance:**
        - Higher RAG articles = more accurate but slower
        - Lower risk threshold = more thorough but slower
        - Progressive analysis can reduce processing time by 60-80%
        """)
    
    return {
        "framework": selected_framework,
        "model": selected_model,
        "preset": selected_preset,
        "enable_progressive": enable_progressive,
        "debug_mode": debug_mode,
        "rag_articles": rag_articles,
        "risk_threshold": risk_threshold,
        "chunk_size": chunk_size
    }