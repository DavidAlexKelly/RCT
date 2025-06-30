import streamlit as st
from typing import Optional

def handle_file_upload() -> Optional[st.runtime.uploaded_file_manager.UploadedFile]:
    """Handle file upload with validation and preview."""
    
    uploaded_file = st.file_uploader(
        "Choose a document to analyse",
        type=['pdf', 'txt', 'md'],
        help="Upload a PDF, TXT, or Markdown file for compliance analysis",
        key="compliance_file_uploader"
    )
    
    if uploaded_file is not None:
        # Validate file size (limit to 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if uploaded_file.size > max_size:
            st.error(f"❌ File too large! Maximum size is 50MB. Your file is {uploaded_file.size / (1024*1024):.1f}MB")
            return None
        
        # Validate file type
        allowed_types = ['application/pdf', 'text/plain', 'text/markdown']
        if uploaded_file.type and uploaded_file.type not in allowed_types:
            st.warning(f"⚠️ Unexpected file type: {uploaded_file.type}. Proceeding anyway...")
    
    return uploaded_file

def display_file_info(uploaded_file):
    """Display information about the uploaded file."""
    
    # File information in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📄 File Name", 
            value=uploaded_file.name[:20] + "..." if len(uploaded_file.name) > 20 else uploaded_file.name
        )
    
    with col2:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb < 1:
            size_display = f"{uploaded_file.size / 1024:.0f} KB"
        else:
            size_display = f"{file_size_mb:.1f} MB"
        st.metric(label="📊 File Size", value=size_display)
    
    with col3:
        file_type_display = get_file_type_display(uploaded_file.type)
        st.metric(label="📋 File Type", value=file_type_display)
    
    with col4:
        # Estimate processing time based on file size
        estimated_time = estimate_processing_time(uploaded_file.size)
        st.metric(label="⏱️ Est. Time", value=estimated_time)
    
    # File preview for text files
    if uploaded_file.type == 'text/plain' or uploaded_file.name.endswith('.md'):
        with st.expander("👀 File Preview", expanded=False):
            try:
                # Read first 1000 characters for preview
                file_content = str(uploaded_file.read(), "utf-8")
                uploaded_file.seek(0)  # Reset file pointer
                
                preview_text = file_content[:1000]
                if len(file_content) > 1000:
                    preview_text += "\n\n... (truncated)"
                
                st.text_area(
                    "Document preview:",
                    value=preview_text,
                    height=200,
                    disabled=True
                )
                
                # Document statistics
                word_count = len(file_content.split())
                char_count = len(file_content)
                line_count = len(file_content.split('\n'))
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Words", word_count)
                with col2:
                    st.metric("Characters", f"{char_count:,}")
                with col3:
                    st.metric("Lines", line_count)
                    
            except Exception as e:
                st.error(f"Could not preview file: {e}")

def get_file_type_display(mime_type):
    """Get a user-friendly display name for the file type."""
    type_mapping = {
        'application/pdf': 'PDF',
        'text/plain': 'Text',
        'text/markdown': 'Markdown',
        None: 'Unknown'
    }
    return type_mapping.get(mime_type, 'Unknown')

def estimate_processing_time(file_size_bytes):
    """Estimate processing time based on file size."""
    # Rough estimates based on file size
    if file_size_bytes < 100 * 1024:  # < 100KB
        return "< 1 min"
    elif file_size_bytes < 1024 * 1024:  # < 1MB
        return "1-2 min"
    elif file_size_bytes < 5 * 1024 * 1024:  # < 5MB
        return "2-5 min"
    elif file_size_bytes < 20 * 1024 * 1024:  # < 20MB
        return "5-10 min"
    else:
        return "10+ min"

def display_upload_tips():
    """Display helpful tips for file upload."""
    with st.expander("💡 Upload Tips"):
        st.markdown("""
        **Supported Formats:**
        - 📄 **PDF**: Best for formal documents, contracts, policies
        - 📝 **TXT**: Plain text files, simple documents
        - 📋 **Markdown**: Structured text with formatting
        
        **Recommendations:**
        - Files under 5MB process faster
        - Clear, well-structured documents work best
        - Remove headers/footers that might confuse analysis
        - Ensure text is selectable in PDFs (not scanned images)
        
        **Document Types:**
        - Privacy policies and terms of service
        - Compliance manuals and procedures
        - Contracts and agreements
        - Technical documentation
        - Business proposals
        """)