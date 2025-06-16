# ui/styles/custom_css.py

import streamlit as st

def apply_custom_styles():
    """Apply custom CSS styles to the Streamlit app."""
    
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .main {
        font-family: 'Inter', sans-serif;
    }
    
    /* Header Styles */
    .main-header {
        font-size: 3.5rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .sub-header {
        text-align: center;
        font-size: 1.2rem;
        color: #6c757d;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 120px;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    
    .metric-card .metric-icon {
        font-size: 2rem;
        margin-right: 1rem;
    }
    
    .metric-card .metric-content h3 {
        margin: 0;
        font-size: 0.9rem;
        font-weight: 500;
        opacity: 0.9;
    }
    
    .metric-card .metric-content h1 {
        margin: 0.5rem 0 0 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    /* Issue Cards */
    .issue-card {
        border: 1px solid #e1e5e9;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        background: white;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        transition: box-shadow 0.2s ease;
    }
    
    .issue-card:hover {
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .issue-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1rem;
    }
    
    .issue-header h4 {
        margin: 0;
        color: #2c3e50;
        font-weight: 600;
        flex-grow: 1;
        margin-right: 1rem;
    }
    
    .severity-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .severity-badge.high {
        background: #fee;
        color: #dc3545;
        border: 1px solid #f5c6cb;
    }
    
    .severity-badge.medium {
        background: #fff8e1;
        color: #856404;
        border: 1px solid #ffeaa7;
    }
    
    .severity-badge.low {
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    
    .issue-details p {
        margin: 0.5rem 0;
        color: #495057;
    }
    
    .citation-box {
        background: #f8f9fa;
        border-left: 4px solid #007bff;
        padding: 1rem;
        margin-top: 1rem;
        border-radius: 0 8px 8px 0;
    }
    
    .citation-box blockquote {
        margin: 0.5rem 0 0 0;
        font-style: italic;
        color: #495057;
        background: white;
        padding: 0.75rem;
        border-radius: 6px;
        border: 1px solid #dee2e6;
    }
    
    /* Risk Level Styling */
    .high-risk {
        border-left: 4px solid #dc3545 !important;
        background: #fff5f5 !important;
    }
    
    .medium-risk {
        border-left: 4px solid #ffc107 !important;
        background: #fffbf0 !important;
    }
    
    .low-risk {
        border-left: 4px solid #28a745 !important;
        background: #f8fff8 !important;
    }
    
    /* Section Analysis */
    .section-issue {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .section-issue h5 {
        color: #856404;
        margin: 0 0 0.5rem 0;
        font-weight: 600;
    }
    
    .section-issue p {
        margin: 0.25rem 0;
        color: #495057;
        font-size: 0.9rem;
    }
    
    /* Status Classes */
    .has-issues {
        border-left: 3px solid #dc3545;
    }
    
    .clean {
        border-left: 3px solid #28a745;
    }
    
    .skipped {
        border-left: 3px solid #6c757d;
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        border: 1px solid #dee2e6;
    }
    
    /* Button Styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Sidebar Styling */
    .css-1d391kg {
        background: #f8f9fa;
    }
    
    .css-1d391kg .stSelectbox > div > div {
        background: white;
        border-radius: 8px;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* File Upload */
    .stFileUploader > section > div {
        border: 2px dashed #667eea;
        border-radius: 12px;
        background: #f8f9ff;
    }
    
    /* Metrics */
    .css-1r6slb0 {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
    }
    
    /* Success/Info/Error Messages */
    .stSuccess {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
    }
    
    .stInfo {
        background: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 8px;
    }
    
    .stError {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 8px;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .main-header {
            font-size: 2.5rem;
        }
        
        .metric-card {
            padding: 1rem;
            min-height: 100px;
        }
        
        .metric-card .metric-content h1 {
            font-size: 2rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)