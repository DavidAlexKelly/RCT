# ui/ui_utils/analysis_runner.py - Final simplified version

import streamlit as st
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path for imports
current_dir = Path(__file__).parent.parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Import the unified engine
from engine import ComplianceAnalyzer

def run_compliance_analysis(uploaded_file, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Run compliance analysis using the unified engine with UI progress updates."""
    
    if config is None:
        st.error("❌ Configuration is required")
        return None
    
    # Enhanced progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    detailed_status = st.empty()
    
    try:
        # Initialize analyzer
        analyzer = ComplianceAnalyzer(debug=config.get("debug_mode", False))
        
        # Prepare file content
        file_content = uploaded_file.getvalue()
        
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
        
        # Create progress callback function
        def progress_callback(progress_percent, status_message, detail_message):
            progress_bar.progress(progress_percent)
            status_text.text(status_message)
            if detail_message:
                detailed_status.text(detail_message)
        
        # Run the actual analysis with progress tracking
        results = analyzer.analyze_document(
            file_path_or_content=file_content,
            regulation_framework=config['framework'],
            config=analysis_config,
            original_filename=uploaded_file.name,  # Pass original filename for extension detection
            progress_callback=progress_callback  # Pass progress callback for detailed updates
        )
        
        # Add some UI-specific metadata
        results["uploaded_filename"] = uploaded_file.name
        
        # Complete
        progress_bar.progress(100)
        status_text.text("✅ Analysis complete!")
        
        # Show completion message
        issues_count = len(results["findings"])
        if issues_count == 0:
            completion_msg = f"🎉 No compliance issues detected!"
        else:
            completion_msg = f"⚠️ Found {issues_count} potential compliance issues"
        
        detailed_status.text(completion_msg)
        
        # Clear progress indicators after a brief delay
        import time
        time.sleep(1.5)
        progress_bar.empty()
        status_text.empty()
        detailed_status.empty()
        
        # Show final message
        if issues_count == 0:
            st.success(completion_msg)
        else:
            st.warning(completion_msg)
        
        return results
        
    except Exception as e:
        st.error(f"❌ Analysis failed: {str(e)}")
        if config.get("debug_mode", False):
            st.exception(e)
        return None
        
    finally:
        # Clear progress indicators on error
        progress_bar.empty()
        status_text.empty()
        detailed_status.empty()

