import streamlit as st
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add parent directory for imports
current_dir = Path(__file__).parent.parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from engine import ComplianceAnalyser

def run_compliance_analysis(uploaded_file, config: Dict[str, Any]) -> Dict[str, Any]:
    """Run compliance analysis with clean user interface."""
    
    # Basic validation
    if not config or not uploaded_file:
        st.error("❌ Missing configuration or file")
        st.stop()
    
    required_keys = ['framework', 'model', 'preset']
    missing = [k for k in required_keys if k not in config]
    if missing:
        st.error(f"❌ Missing config: {missing}")
        st.stop()
    
    # Validate file content
    try:
        file_content = uploaded_file.getvalue()
        if not file_content:
            st.error("❌ Empty file")
            st.stop()
    except Exception as e:
        st.error(f"❌ File read error: {e}")
        st.stop()
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Initialize analyser
        progress_bar.progress(0.1)
        status_text.text("🔧 Initializing analyser...")
        
        analyser = ComplianceAnalyser(debug=config.get("debug_mode", False))
        
        # Validate framework exists
        frameworks = analyser.get_available_frameworks()
        framework_ids = [f['id'] for f in frameworks]
        if config['framework'] not in framework_ids:
            st.error(f"❌ Framework '{config['framework']}' not found")
            st.error(f"Available frameworks: {framework_ids}")
            st.stop()
        
        # Create analysis config
        analysis_config = {
            'model': config.get('model', 'small'),
            'preset': config.get('preset', 'balanced'),
            'progressive_enabled': config.get('enable_progressive', True),
            'topic_threshold': config.get('topic_threshold', 2.0),
            'rag_articles': config.get('rag_articles', 5),
            'chunking_method': config.get('chunking_method', 'smart'),
            'chunk_size': config.get('chunk_size', 800),
            'chunk_overlap': config.get('chunk_overlap', 100),
            'debug': config.get('debug_mode', False)
        }
        
        # Progress callback
        def progress_callback(percent, status, detail):
            progress_bar.progress(min(percent / 100.0, 1.0))
            # Simplify status messages for users
            clean_status = _clean_status_message(status)
            status_text.text(f"⚙️ {clean_status}")
        
        # Run analysis
        progress_bar.progress(0.2)
        status_text.text("🚀 Starting analysis...")
        
        results = analyser.analyse_document(
            file_path_or_content=file_content,
            regulation_framework=config['framework'],
            config_dict=analysis_config,
            original_filename=uploaded_file.name,
            progress_callback=progress_callback
        )
        
        # Validate results
        if not results or not isinstance(results, dict):
            st.error("❌ Invalid analysis results")
            st.stop()
        
        required_result_keys = ['findings', 'chunk_results', 'metadata', 'config']
        missing_results = [k for k in required_result_keys if k not in results]
        if missing_results:
            st.error(f"❌ Results missing: {missing_results}")
            st.stop()
        
        # Add UI metadata
        results["uploaded_filename"] = uploaded_file.name
        
        # Complete progress
        progress_bar.progress(1.0)
        status_text.text("✅ Analysis complete!")
        
        # Show simple completion message
        issues_count = len(results.get("findings", []))
        if issues_count == 0:
            st.success("🎉 No compliance issues detected!")
            st.balloons()
        else:
            st.warning(f"⚠️ Found {issues_count} potential compliance issues")
        
        # Clear progress after delay
        time.sleep(1.5)
        progress_bar.empty()
        status_text.empty()
        
        return results
        
    except Exception as e:
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        st.error(f"❌ Analysis failed: {e}")
        
        if config.get("debug_mode", False):
            st.exception(e)
        else:
            st.error("💡 Enable Debug Mode in Advanced Options for technical details")
        
        # Common solutions
        with st.expander("🔧 Troubleshooting"):
            st.markdown("""
            **Common solutions:**
            1. **Restart application**: `python launch.py`
            2. **Check Ollama**: Run `ollama list` to verify models
            3. **Try different settings**: Use different analysis mode
            4. **Check document**: Ensure it's not corrupted or too large
            5. **Framework issues**: Verify framework files exist
            
            **If issues persist:**
            - Enable Debug Mode for detailed error information
            - Check that your document contains readable text
            - Try a smaller document or different format
            """)
        
        st.stop()
    
    finally:
        # Cleanup progress indicators
        try:
            progress_bar.empty()
            status_text.empty()
        except:
            pass

def _clean_status_message(status: str) -> str:
    """Convert technical status messages to user-friendly ones."""
    status_mapping = {
        "Loading knowledge base": "Loading compliance rules",
        "Processing document": "Reading document",
        "Analysing compliance": "Checking for violations",
        "Processing results": "Preparing results",
        "Analysing high-risk": "Analysing section",
        "Complete": "Complete"
    }
    
    # Check for partial matches
    for technical, friendly in status_mapping.items():
        if technical.lower() in status.lower():
            return friendly
    
    # Default to original status if no mapping found
    return status