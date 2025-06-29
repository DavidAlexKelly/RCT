import streamlit as st

def apply_custom_styles():
    """Apply custom CSS styles."""
    
    st.markdown("""
    <style>
    /* Import clean font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .main {
        font-family: 'Inter', sans-serif;
    }
    
    /* Headers */
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .sub-header {
        text-align: center;
        font-size: 1.2rem;
        color: #6c757d;
        margin-bottom: 2rem;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    /* Issue cards */
    .issue-card {
        border-left: 4px solid #007bff;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .issue-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    
    .severity-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .severity-badge.high { background: #fee; color: #dc3545; }
    .severity-badge.medium { background: #fff8e1; color: #856404; }
    .severity-badge.low { background: #d4edda; color: #155724; }
    
    .citation-box {
        background: #f8f9fa;
        border-left: 3px solid #007bff;
        padding: 0.75rem;
        margin-top: 0.5rem;
        border-radius: 0 6px 6px 0;
    }
    
    /* Risk levels */
    .high-risk { border-left-color: #dc3545 !important; background: #fff5f5 !important; }
    .medium-risk { border-left-color: #ffc107 !important; background: #fffbf0 !important; }
    .low-risk { border-left-color: #28a745 !important; background: #f8fff8 !important; }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)