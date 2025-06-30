import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List

def create_metrics_dashboard(findings: List[Dict], analysis_config: Dict):
    """Create clean metrics dashboard focused on results."""
    total_issues = len(findings)
    
    # Count issues by regulation
    regulation_counts = {}
    for finding in findings:
        reg = finding.get("regulation", "Unknown")
        regulation_counts[reg] = regulation_counts.get(reg, 0) + 1
    
    # Clean metrics display
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">🚨</div>
            <div class="metric-content">
                <h3>Total Issues</h3>
                <h1>{total_issues}</h1>
                <small>Compliance violations found</small>
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
                <small>Articles affected</small>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        total_sections = analysis_config.get('total_sections', 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">📄</div>
            <div class="metric-content">
                <h3>Sections</h3>
                <h1>{total_sections}</h1>
                <small>Document sections</small>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        framework = analysis_config.get('framework', 'Unknown').upper()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">🛡️</div>
            <div class="metric-content">
                <h3>Framework</h3>
                <h1>{framework}</h1>
                <small>Compliance standard</small>
            </div>
        </div>
        """, unsafe_allow_html=True)

def create_regulation_breakdown_chart(findings: List[Dict]):
    """Create chart showing issues breakdown by regulation."""
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
        
        # Create an enhanced donut chart
        fig = px.pie(
            df, 
            values='Count', 
            names='Regulation', 
            title="Issues by Regulation Article",
            color_discrete_sequence=px.colors.qualitative.Set3,
            hole=0.4
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

def display_analysis_summary_cards(results: Dict[str, Any]):
    """Display simple summary cards."""
    
    findings = results.get('findings', [])
    config_info = results.get('config', {})
    
    # Calculate summary statistics
    total_issues = len(findings)
    high_severity_issues = sum(1 for f in findings if 'unauthorized' in f.get('issue', '').lower() 
                              or 'violation' in f.get('issue', '').lower())
    
    framework = results.get('regulation_framework', 'Unknown').upper()
    
    # Summary cards
    col1, col2 = st.columns(2)
    
    with col1:
        if total_issues == 0:
            st.success("🎉 **Compliance Status: CLEAN**\n\nNo violations detected in this document.")
        elif high_severity_issues > 0:
            st.error(f"⚠️ **Compliance Status: HIGH RISK**\n\n{high_severity_issues} high-severity violations found.")
        else:
            st.warning(f"⚠️ **Compliance Status: ISSUES FOUND**\n\n{total_issues} compliance issues detected.")
    
    with col2:
        analysis_type = config_info.get('analysis_type', 'Standard')
        st.info(f"🎯 **Analysis Summary**\n\n**Framework:** {framework}\n**Type:** {analysis_type}\n**Model:** {config_info.get('model', 'Unknown')}")
    
    # Simple recommendations
    if total_issues > 0:
        st.markdown("### 📋 Recommended Actions")
        
        # Generate framework-specific recommendations
        if framework == 'GDPR':
            recommendations = [
                "Review consent mechanisms for GDPR compliance",
                "Implement data subject rights procedures", 
                "Establish clear data retention policies",
                "Ensure transparency in data processing"
            ]
        elif framework == 'HIPAA':
            recommendations = [
                "Review PHI authorization procedures",
                "Implement required administrative, physical, and technical safeguards",
                "Establish business associate agreements where needed",
                "Create proper breach notification procedures"
            ]
        else:
            recommendations = [
                "Review identified compliance gaps with legal counsel",
                "Implement necessary policy changes",
                "Establish monitoring procedures",
                "Consider regular compliance audits"
            ]
        
        for i, rec in enumerate(recommendations[:3], 1):
            st.markdown(f"{i}. {rec}")
        
        if total_issues > 5:
            st.warning("🔍 **Priority:** Focus on the most critical violations first")
    else:
        st.markdown("### ✅ Maintenance Recommendations")
        st.markdown("1. Maintain current compliance practices\n2. Consider periodic compliance reviews\n3. Stay updated on regulatory changes")