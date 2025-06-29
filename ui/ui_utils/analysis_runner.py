# ui/ui_utils/analysis_runner.py - Simplified (336 → 80 lines)

import streamlit as st
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add parent directory for imports
current_dir = Path(__file__).parent.parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from engine import ComplianceAnalyzer

def run_compliance_analysis(uploaded_file, config: Dict[str, Any]) -> Dict[str, Any]:
    """Run compliance analysis with UI progress updates."""
    
    # Basic validation
    assert config and uploaded_file, "Missing config or file"
    
    required_keys = ['framework', 'model', 'preset']
    missing = [k for k in required_keys if k not in config]
    if missing:
        st.error(f"Missing config: {missing}")
        st.stop()
    
    # Validate file content
    try:
        file_content = uploaded_file.getvalue()
        assert file_content, "Empty file"
    except Exception as e:
        st.error(f"File read error: {e}")
        st.stop()
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Initialize analyzer
        analyzer = ComplianceAnalyzer(debug=config.get("debug_mode", False))
        
        # Validate framework exists
        frameworks = analyzer.get_available_frameworks()
        framework_ids = [f['id'] for f in frameworks]
        if config['framework'] not in framework_ids:
            st.error(f"Framework '{config['framework']}' not found")
            st.error(f"Available: {framework_ids}")
            st.stop()
        
        # Create analysis config
        analysis_config = {
            'model': config['model'],
            'preset': config['preset'],
            'progressive_enabled': config['enable_progressive'],
            'rag_articles': config['rag_articles'],
            'risk_threshold': config['risk_threshold'],
            'chunking_method': config['chunking_method'],
            'chunk_size': config['chunk_size'],
            'chunk_overlap': config['chunk_overlap'],
            'optimize_chunks': config['optimize_chunks'],
            'debug': config.get('debug_mode', False)
        }
        
        # Progress callback
        def progress_callback(percent, status, detail):
            progress_bar.progress(min(percent / 100.0, 1.0))
            status_text.text(status)
        
        # Run analysis
        results = analyzer.analyze_document(
            file_path_or_content=file_content,
            regulation_framework=config['framework'],
            config_dict=analysis_config,
            original_filename=uploaded_file.name,
            progress_callback=progress_callback
        )
        
        # Validate results
        assert results and isinstance(results, dict), "Invalid results"
        
        required_result_keys = ['findings', 'chunk_results', 'metadata', 'config']
        missing_results = [k for k in required_result_keys if k not in results]
        if missing_results:
            st.error(f"Results missing: {missing_results}")
            st.stop()
        
        # Add UI metadata
        results["uploaded_filename"] = uploaded_file.name
        
        # Complete progress
        progress_bar.progress(1.0)
        status_text.text("✅ Analysis complete!")
        
        # Show completion message
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
        st.error(f"Analysis failed: {e}")
        
        if config.get("debug_mode", False):
            st.exception(e)
        else:
            st.error("Enable Debug Mode for technical details")
        
        # Common solutions
        st.error("**Common solutions:**")
        st.error("1. Restart: `python launch.py`")
        st.error("2. Check Ollama: `ollama list`")
        st.error("3. Try different document/settings")
        
        st.stop()
    
    finally:
        # Cleanup progress indicators
        try:
            progress_bar.empty()
            status_text.empty()
        except:
            pass