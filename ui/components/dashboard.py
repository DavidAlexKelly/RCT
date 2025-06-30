import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, List

def create_metrics_dashboard(findings: List[Dict], analysis_config: Dict):
    """Create enhanced metrics dashboard with progressive analysis insights."""
    total_issues = len(findings)
    
    # Count issues by regulation
    regulation_counts = {}
    for finding in findings:
        reg = finding.get("regulation", "Unknown")
        regulation_counts[reg] = regulation_counts.get(reg, 0) + 1
    
    # Enhanced metrics in a responsive grid
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
        analyzed_sections = analysis_config.get('analyzed_sections', 0)
        total_sections = analysis_config.get('total_sections', 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">🔍</div>
            <div class="metric-content">
                <h3>Analyzed</h3>
                <h1>{analyzed_sections}/{total_sections}</h1>
                <small>Sections processed</small>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        efficiency = analysis_config.get('efficiency_gain', '0%')
        analysis_type = analysis_config.get('analysis_type', 'Standard')
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">⚡</div>
            <div class="metric-content">
                <h3>Efficiency</h3>
                <h1>{efficiency}</h1>
                <small>{analysis_type}</small>
            </div>
        </div>
        """, unsafe_allow_html=True)

def create_regulation_breakdown_chart(findings: List[Dict]):
    """Create enhanced chart showing issues breakdown by regulation."""
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
            hole=0.4  # Creates donut chart
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

def create_progressive_analysis_dashboard(results: Dict[str, Any]):
    """Create dashboard showing progressive analysis performance metrics."""
    
    if 'scoring_stats' not in results:
        return
    
    st.subheader("🎯 Progressive Analysis Performance")
    
    scoring_stats = results['scoring_stats']
    chunk_results = results.get('chunk_results', [])
    
    # Performance metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_score = scoring_stats.get('average_score', 0)
        st.metric("Average Risk Score", f"{avg_score:.1f}")
    
    with col2:
        max_score = scoring_stats.get('maximum_score', 0)
        st.metric("Maximum Risk Score", f"{max_score:.1f}")
    
    with col3:
        threshold = scoring_stats.get('threshold', 0)
        st.metric("Risk Threshold", f"{threshold:.1f}")
    
    with col4:
        analyzed_count = scoring_stats.get('analyzed_count', 0)
        total_count = analyzed_count + scoring_stats.get('skipped_count', 0)
        if total_count > 0:
            precision_rate = (analyzed_count / total_count) * 100
            st.metric("Analysis Rate", f"{precision_rate:.1f}%")
    
    # Create risk score distribution chart
    if chunk_results:
        create_risk_score_distribution(chunk_results)
    
    # Create efficiency comparison
    create_efficiency_comparison(results)

def create_risk_score_distribution(chunk_results: List[Dict]):
    """Create chart showing risk score distribution."""
    
    # Prepare data
    scores = []
    statuses = []
    positions = []
    issues_counts = []
    
    for chunk in chunk_results:
        scores.append(chunk.get('risk_score', 0))
        statuses.append('Analyzed' if chunk.get('should_analyze', True) else 'Skipped')
        positions.append(chunk.get('position', 'Unknown'))
        issues_counts.append(len(chunk.get('issues', [])))
    
    df = pd.DataFrame({
        'Risk Score': scores,
        'Status': statuses,
        'Section': positions,
        'Issues Found': issues_counts
    })
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Histogram of risk scores
        fig_hist = px.histogram(
            df, 
            x='Risk Score', 
            color='Status',
            title="Risk Score Distribution",
            nbins=20,
            barmode='overlay',
            opacity=0.7
        )
        
        # Add threshold line
        from config import config
        fig_hist.add_vline(x=config.high_risk_threshold, line_dash="dash", 
                          annotation_text="Threshold")
        
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        # Scatter plot: Risk Score vs Issues Found
        fig_scatter = px.scatter(
            df,
            x='Risk Score',
            y='Issues Found',
            color='Status',
            title="Risk Score vs Issues Found",
            hover_data=['Section']
        )
        
        fig_scatter.add_vline(x=config.high_risk_threshold, line_dash="dash", 
                             annotation_text="Threshold")
        
        st.plotly_chart(fig_scatter, use_container_width=True)

def create_efficiency_comparison(results: Dict[str, Any]):
    """Create efficiency comparison visualization."""
    
    config_info = results.get('config', {})
    analyzed_sections = config_info.get('analyzed_sections', 0)
    total_sections = config_info.get('total_sections', 1)
    skipped_sections = config_info.get('skipped_sections', 0)
    
    # Create comparison data
    categories = ['Traditional Analysis', 'Progressive Analysis']
    sections_analyzed = [total_sections, analyzed_sections]
    time_saved = [0, (skipped_sections / total_sections) * 100 if total_sections > 0 else 0]
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=['Sections Analyzed', 'Time Saved (%)'],
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Sections analyzed comparison
    fig.add_trace(
        go.Bar(x=categories, y=sections_analyzed, name='Sections Analyzed', 
               marker_color=['#ff7f7f', '#90EE90']),
        row=1, col=1
    )
    
    # Time saved comparison
    fig.add_trace(
        go.Bar(x=categories, y=[0, time_saved[1]], name='Time Saved (%)', 
               marker_color=['#ff7f7f', '#90EE90']),
        row=1, col=2
    )
    
    fig.update_layout(
        title_text="Progressive Analysis Efficiency Gains",
        showlegend=False,
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Efficiency insights
    if time_saved[1] > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Sections Skipped", 
                skipped_sections,
                delta=f"{-skipped_sections} fewer to analyze"
            )
        
        with col2:
            st.metric(
                "Time Efficiency", 
                f"{time_saved[1]:.1f}%",
                delta="Time saved vs traditional analysis"
            )
        
        with col3:
            # Calculate estimated time savings (rough estimate)
            estimated_minutes_saved = (skipped_sections * 0.5)  # Rough estimate: 30s per section
            st.metric(
                "Est. Time Saved", 
                f"{estimated_minutes_saved:.1f} min",
                delta="Approximate time savings"
            )

def create_framework_comparison_chart(results: Dict[str, Any]):
    """Create chart comparing different framework characteristics."""
    
    framework = results.get('regulation_framework', 'Unknown')
    findings = results.get('findings', [])
    
    # Framework-specific insights
    framework_data = {
        'gdpr': {
            'name': 'GDPR',
            'focus_areas': ['Consent', 'Data Rights', 'Storage Limits', 'Transparency'],
            'color': '#4285f4'
        },
        'hipaa': {
            'name': 'HIPAA', 
            'focus_areas': ['PHI Protection', 'Safeguards', 'Authorization', 'Breach Notification'],
            'color': '#34a853'
        }
    }
    
    current_framework = framework_data.get(framework, {
        'name': framework.upper(),
        'focus_areas': ['Compliance', 'Security', 'Privacy', 'Rights'],
        'color': '#ea4335'
    })
    
    # Count issues by category (simplified)
    issue_categories = {}
    for finding in findings:
        issue_text = finding.get('issue', '').lower()
        regulation = finding.get('regulation', '')
        
        # Categorize based on keywords
        if any(word in issue_text for word in ['consent', 'authorization', 'permission']):
            category = 'Consent/Authorization'
        elif any(word in issue_text for word in ['security', 'safeguard', 'encryption']):
            category = 'Security/Safeguards'
        elif any(word in issue_text for word in ['storage', 'retention', 'deletion']):
            category = 'Data Retention'
        elif any(word in issue_text for word in ['access', 'rights', 'notification']):
            category = 'Individual Rights'
        else:
            category = 'Other'
        
        issue_categories[category] = issue_categories.get(category, 0) + 1
    
    if issue_categories:
        # Create horizontal bar chart
        df = pd.DataFrame(list(issue_categories.items()), columns=['Category', 'Count'])
        
        fig = px.bar(
            df,
            x='Count',
            y='Category',
            orientation='h',
            title=f"{current_framework['name']} Issues by Category",
            color_discrete_sequence=[current_framework['color']]
        )
        
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

def display_analysis_summary_cards(results: Dict[str, Any]):
    """Display summary cards with key analysis insights."""
    
    findings = results.get('findings', [])
    config_info = results.get('config', {})
    
    # Calculate summary statistics
    total_issues = len(findings)
    high_severity_issues = sum(1 for f in findings if 'unauthorized' in f.get('issue', '').lower() 
                              or 'violation' in f.get('issue', '').lower())
    
    framework = results.get('regulation_framework', 'Unknown').upper()
    efficiency = config_info.get('efficiency_gain', '0%')
    
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
        st.info(f"🎯 **Analysis Summary**\n\n**Framework:** {framework}\n**Efficiency Gain:** {efficiency}\n**Type:** {config_info.get('analysis_type', 'Standard')}")
    
    # Recommendations based on findings
    if total_issues > 0:
        st.markdown("### 📋 Recommended Actions")
        
        # Generate framework-specific recommendations
        if framework == 'GDPR':
            recommendations = [
                "Review consent mechanisms for GDPR compliance",
                "Implement data subject rights procedures", 
                "Establish data retention policies",
                "Conduct privacy impact assessments"
            ]
        elif framework == 'HIPAA':
            recommendations = [
                "Review PHI authorization procedures",
                "Implement required safeguards (administrative, physical, technical)",
                "Establish business associate agreements",
                "Create breach notification procedures"
            ]
        else:
            recommendations = [
                "Review identified compliance gaps",
                "Implement necessary policy changes",
                "Establish monitoring procedures",
                "Consider regular compliance audits"
            ]
        
        for i, rec in enumerate(recommendations[:3], 1):
            st.markdown(f"{i}. {rec}")
        
        if total_issues > 5:
            st.warning("🔍 **Priority:** Focus on high-severity violations first")
    else:
        st.markdown("### ✅ Compliance Recommendations")
        st.markdown("1. Maintain current compliance practices\n2. Consider periodic compliance reviews\n3. Stay updated on regulatory changes")