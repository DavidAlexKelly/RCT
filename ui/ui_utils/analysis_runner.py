# ui/ui_utils/analysis_runner.py - Proper error handling without fallbacks

import streamlit as st
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
current_dir = Path(__file__).parent.parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Import the unified engine
from engine import ComplianceAnalyzer

def run_compliance_analysis(uploaded_file, config: Dict[str, Any]) -> Dict[str, Any]:
    """Run compliance analysis using the unified engine with UI progress updates."""
    
    # Validate critical inputs
    if config is None:
        st.error("❌ **Configuration Error:** Analysis configuration is required")
        st.error("**Action Required:** Configuration system failed to initialize properly")
        st.stop()
    
    if uploaded_file is None:
        st.error("❌ **File Upload Error:** No file was uploaded")
        st.error("**Action Required:** Please upload a document before starting analysis")
        st.stop()
    
    # Validate configuration completeness
    required_config_keys = ['framework', 'model', 'preset']
    missing_keys = [key for key in required_config_keys if key not in config]
    if missing_keys:
        st.error(f"❌ **Configuration Error:** Missing required settings: {missing_keys}")
        st.error("**Action Required:** Check sidebar configuration")
        st.stop()
    
    # Validate file content
    try:
        file_content = uploaded_file.getvalue()
        if not file_content or len(file_content) == 0:
            st.error("❌ **File Error:** Uploaded file is empty")
            st.error("**Action Required:** Upload a file with content")
            st.stop()
    except Exception as e:
        st.error(f"❌ **File Read Error:** Could not read uploaded file: {e}")
        st.stop()
    
    # Enhanced progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    detailed_status = st.empty()
    
    try:
        # Initialize analyzer with validation
        try:
            analyzer = ComplianceAnalyzer(debug=config.get("debug_mode", False))
        except Exception as e:
            st.error(f"❌ **Engine Initialization Failed:** {e}")
            st.error("**Possible Causes:**")
            st.error("- Knowledge base directory missing or invalid")
            st.error("- Model configuration issues")
            st.error("- Missing required dependencies")
            if config.get("debug_mode", False):
                st.exception(e)
            st.stop()
        
        # Validate framework exists
        try:
            available_frameworks = analyzer.get_available_frameworks()
            framework_ids = [f['id'] for f in available_frameworks]
            if config['framework'] not in framework_ids:
                st.error(f"❌ **Framework Error:** '{config['framework']}' not found")
                st.error(f"**Available frameworks:** {framework_ids}")
                st.stop()
        except Exception as e:
            st.error(f"❌ **Framework Validation Failed:** {e}")
            if config.get("debug_mode", False):
                st.exception(e)
            st.stop()
        
        # Create analysis config with validation
        try:
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
            
            # Validate numeric parameters
            if analysis_config['rag_articles'] < 1 or analysis_config['rag_articles'] > 20:
                st.error(f"❌ **Configuration Error:** RAG articles count ({analysis_config['rag_articles']}) must be between 1 and 20")
                st.stop()
            
            if analysis_config['chunk_size'] < 200 or analysis_config['chunk_size'] > 5000:
                st.error(f"❌ **Configuration Error:** Chunk size ({analysis_config['chunk_size']}) must be between 200 and 5000")
                st.stop()
                
        except KeyError as e:
            st.error(f"❌ **Configuration Error:** Missing required setting: {e}")
            st.stop()
        except Exception as e:
            st.error(f"❌ **Configuration Error:** Invalid configuration: {e}")
            st.stop()
        
        # Create progress callback function
        def progress_callback(progress_percent, status_message, detail_message):
            # Validate progress parameters
            if not isinstance(progress_percent, (int, float)):
                progress_percent = 0
            progress_percent = max(0, min(100, progress_percent))
            
            progress_bar.progress(progress_percent / 100.0)
            
            if status_message:
                status_text.text(str(status_message))
            
            if detail_message:
                detailed_status.text(str(detail_message))
        
        # Run the actual analysis with comprehensive error handling
        try:
            results = analyzer.analyze_document(
                file_path_or_content=file_content,
                regulation_framework=config['framework'],
                config=analysis_config,
                original_filename=uploaded_file.name,
                progress_callback=progress_callback
            )
        except FileNotFoundError as e:
            st.error(f"❌ **File System Error:** {e}")
            st.error("**Possible Solutions:**")
            st.error("- Check that all required files exist")
            st.error("- Verify file permissions")
            st.stop()
        except ValueError as e:
            st.error(f"❌ **Input Validation Error:** {e}")
            st.error("**Possible Solutions:**")
            st.error("- Check document format (PDF, TXT, MD supported)")
            st.error("- Ensure document contains readable text")
            st.error("- Try a different document")
            if config.get("debug_mode", False):
                st.exception(e)
            st.stop()
        except RuntimeError as e:
            st.error(f"❌ **Analysis Runtime Error:** {e}")
            st.error("**Possible Solutions:**")
            st.error("- Check Ollama is running: `ollama list`")
            st.error("- Verify model is available")
            st.error("- Try a smaller document or different settings")
            if config.get("debug_mode", False):
                st.exception(e)
            st.stop()
        except Exception as e:
            st.error(f"❌ **Unexpected Analysis Error:** {e}")
            st.error("**This is an unexpected error. Please:**")
            st.error("- Enable debug mode for more details")
            st.error("- Check the terminal/console for additional information")
            st.error("- Report this issue if it persists")
            if config.get("debug_mode", False):
                st.exception(e)
            st.stop()
        
        # Validate results
        if not results:
            st.error("❌ **Analysis Failed:** No results returned from analysis engine")
            st.error("**This should not happen. Please:**")
            st.error("- Enable debug mode")
            st.error("- Check terminal output")
            st.error("- Report this issue")
            st.stop()
        
        if not isinstance(results, dict):
            st.error(f"❌ **Analysis Error:** Invalid result type: {type(results)}")
            st.stop()
        
        required_result_keys = ['findings', 'chunk_results', 'metadata', 'config']
        missing_result_keys = [key for key in required_result_keys if key not in results]
        if missing_result_keys:
            st.error(f"❌ **Analysis Error:** Results missing required data: {missing_result_keys}")
            if config.get("debug_mode", False):
                st.json({"available_keys": list(results.keys())})
            st.stop()
        
        # Add some UI-specific metadata
        results["uploaded_filename"] = uploaded_file.name
        
        # Complete progress tracking
        progress_bar.progress(100)
        status_text.text("✅ Analysis complete!")
        
        # Show completion message based on results
        try:
            issues_count = len(results.get("findings", []))
            if issues_count == 0:
                completion_msg = f"🎉 No compliance issues detected!"
            else:
                completion_msg = f"⚠️ Found {issues_count} potential compliance issues"
            
            detailed_status.text(completion_msg)
        except Exception as e:
            # Non-critical error in showing completion message
            detailed_status.text("Analysis complete")
        
        # Clear progress indicators after a brief delay
        import time
        time.sleep(1.5)
        progress_bar.empty()
        status_text.empty()
        detailed_status.empty()
        
        # Show final message
        try:
            issues_count = len(results.get("findings", []))
            if issues_count == 0:
                st.success(f"🎉 No compliance issues detected!")
                st.balloons()
            else:
                st.warning(f"⚠️ Found {issues_count} potential compliance issues")
        except Exception:
            # Non-critical error in final message
            st.success("✅ Analysis completed successfully")
        
        return results
        
    except Exception as e:
        # This catch-all should only trigger for completely unexpected errors
        st.error(f"❌ **Critical System Error:** {str(e)}")
        st.error("**This is a system-level error that needs investigation:**")
        st.error("- The application encountered an unexpected condition")
        st.error("- Please report this error with the full details below")
        
        if config.get("debug_mode", False):
            st.error("**Full Error Details:**")
            st.exception(e)
        else:
            st.error("**Enable Debug Mode in the sidebar for technical details**")
        
        # Show suggestions for common issues
        st.error("**Common Solutions:**")
        st.error("1. Restart the application: `python launch.py`")
        st.error("2. Check Ollama is running: `ollama list`")
        st.error("3. Verify knowledge base integrity")
        st.error("4. Try with a different document")
        
        st.stop()
        
    finally:
        # Always clear progress indicators on any exit path
        try:
            progress_bar.empty()
            status_text.empty()
            detailed_status.empty()
        except:
            pass  # Ignore errors in cleanup