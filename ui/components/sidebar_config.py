# ui/components/sidebar_config.py - SIMPLIFIED VERSION

import streamlit as st
import os
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
current_dir = Path(__file__).parent.parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from config import MODELS, DEFAULT_MODEL

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
    """Create the simplified configuration sidebar and return selected options."""
    
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
        help="Choose analysis approach - this controls speed vs thoroughness"
    )
    
    # Chunking method
    chunking_options = {
        'smart': '🧠 Smart - Detect sections, fallback to paragraphs',
        'paragraph': '📄 Paragraph - Group by paragraphs', 
        'sentence': '📝 Sentence - Group by sentences',
        'simple': '✂️ Simple - Character-based splitting'
    }
    
    selected_chunking = st.sidebar.selectbox(
        "📄 Document Chunking",
        options=list(chunking_options.keys()),
        format_func=lambda x: chunking_options[x],
        help="How to break up the document - Smart works best for most documents"
    )
    
    # Configuration summary
    with st.sidebar.expander("📊 Current Configuration"):
        st.code(f"""
Framework: {selected_framework}
Model: {selected_model}
Preset: {selected_preset}
Chunking: {selected_chunking}

Note: The preset controls all other 
analysis parameters like chunk size,
risk thresholds, and processing options.
        """)
    
    # Tips and information
    with st.sidebar.expander("💡 Tips"):
        st.markdown("""
        **Performance Presets:**
        - **Balanced**: Good for most documents (recommended)
        - **Accuracy**: When you need the highest quality results
        - **Speed**: For quick scans or testing
        - **Comprehensive**: Analyzes every section thoroughly
        
        **Chunking Methods:**
        - **Smart**: Best for most documents - automatically detects structure
        - **Paragraph**: Good for contracts and flowing text
        - **Sentence**: Fine control for complex documents
        - **Simple**: Basic splitting when structure detection fails
        """)
    
    return {
        "framework": selected_framework,
        "model": selected_model,
        "preset": selected_preset,
        "chunking_method": selected_chunking
    }