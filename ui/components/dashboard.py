import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Dict, Any, List

def create_metrics_dashboard(findings: List[Dict], analysis_config: Dict):
    """Create a metrics dashboard with key statistics."""
    total_issues = len(findings)
    
    # Count issues by regulation
    regulation_counts = {}
    for finding in findings:
        reg = finding.get("regulation", "Unknown")
        regulation_counts[reg] = regulation_counts.get(reg, 0) + 1
    
    # Display metrics in a responsive grid
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">📊</div>
            <div class="metric-content">
                <h3>Total Issues</h3>
                <h1>{total_issues}</h1>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        unique_regulations = len(regulation_counts)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">⚖️</div>
            <div class="metric-content">
                <h3>Regulations</h3>
                <h1>{unique_regulations}</h1>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        analyzed_sections = analysis_config.get('analyzed_sections', 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">📄</div>
            <div class="metric-content">
                <h3>Sections</h3>
                <h1>{analyzed_sections}</h1>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        analysis_type = analysis_config.get('analysis_type', 'Standard')
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">🎯</div>
            <div class="metric-content">
                <h3>Analysis</h3>
                <h1>{analysis_type}</h1>
            </div>
        </div>
        """, unsafe_allow_html=True)

def create_regulation_breakdown_chart(findings: List[Dict]):
    """Create a chart showing issues breakdown by regulation."""
    if not findings:
        st.info("No issues found to display in chart.")
        return
    
    # Count issues by regulation
    regulation_counts = {}
    for finding in findings:
        reg = finding.get("regulation", "Unknown")
        regulation_counts[reg] = regulation_counts.get(reg, 0) + 1
    
    if regulation_counts:
        # Create DataFrame for plotting
        df = pd.DataFrame(list(regulation_counts.items()), columns=['Regulation', 'Count'])
        
        # Create an enhanced pie chart
        fig = px.pie(
            df, 
            values='Count', 
            names='Regulation', 
            title="Issues by Regulation Article",
            color_discrete_sequence=px.colors.qualitative.Set3,
            hover_data=['Count']
        )
        
        # Customize the chart
        fig.update_traces(
            textposition='inside', 
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Issues: %{value}<br>Percentage: %{percent}<extra></extra>'
        )
        
        fig.update_layout(
            height=400,
            font=dict(size=12),
            title=dict(font=dict(size=16, color='#2c3e50')),
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.01
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)