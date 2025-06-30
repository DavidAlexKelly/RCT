import streamlit as st
from typing import Dict, Any, List
import re

def display_findings(findings: List[Dict], chunk_results: List[Dict]):
    """Display findings in an organized, appealing way."""
    if not findings:
        st.success("🎉 No compliance issues detected!")
        st.balloons()
        return
    
    # Group findings by regulation
    by_regulation = {}
    for finding in findings:
        regulation = finding.get("regulation", "Unknown regulation")
        if regulation not in by_regulation:
            by_regulation[regulation] = []
        by_regulation[regulation].append(finding)
    
    # Display summary statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Issues", len(findings))
    with col2:
        st.metric("Regulations Affected", len(by_regulation))
    with col3:
        most_common_reg = max(by_regulation.keys(), key=lambda x: len(by_regulation[x]))
        st.metric("Most Common", f"{most_common_reg} ({len(by_regulation[most_common_reg])})")
    
    st.markdown("---")
    
    # Display issues by regulation
    for regulation, reg_findings in sorted(by_regulation.items()):
        severity = get_regulation_severity(regulation, reg_findings)
        severity_icon = get_severity_icon(severity)
        
        with st.expander(f"{severity_icon} {regulation} ({len(reg_findings)} issues)", expanded=True):
            for i, finding in enumerate(reg_findings):
                display_single_finding(finding, i + 1)

def display_single_finding(finding: Dict, issue_number: int):
    """Display a single compliance finding."""
    issue = finding.get("issue", "Unknown issue")
    citation = finding.get("citation", "No citation provided")
    section = finding.get("section", "Unknown section")
    regulation = finding.get("regulation", "Unknown")
    
    # Clean up citation
    if citation.startswith('"') and citation.endswith('"'):
        citation = citation[1:-1]
    
    # Get severity class for styling
    severity = get_issue_severity(issue)
    severity_class = f"{severity}-risk"
    
    st.markdown(f"""
    <div class="issue-card {severity_class}">
        <div class="issue-header">
            <h4>🔍 Issue {issue_number}: {issue}</h4>
            <span class="severity-badge {severity}">{severity.upper()}</span>
        </div>
        <div class="issue-details">
            <p><strong>📍 Section:</strong> {section}</p>
            <p><strong>⚖️ Regulation:</strong> {regulation}</p>
            <div class="citation-box">
                <strong>💬 Citation:</strong>
                <blockquote>"{citation}"</blockquote>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def display_section_analysis(chunk_results: List[Dict]):
    """Display section-by-section analysis with enhanced scoring information."""
    if not chunk_results:
        st.info("No section analysis data available.")
        return
    
    # Summary statistics
    total_sections = len(chunk_results)
    analyzed_chunks = [c for c in chunk_results if c.get("should_analyze", True)]
    skipped_chunks = [c for c in chunk_results if not c.get("should_analyze", True)]
    sections_with_issues = sum(1 for chunk in chunk_results if chunk.get("issues", []))
    
    # Display enhanced summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sections", total_sections)
    with col2:
        st.metric("Analyzed", len(analyzed_chunks))
    with col3:
        st.metric("With Issues", sections_with_issues)
    with col4:
        efficiency = (len(skipped_chunks) / total_sections * 100) if total_sections else 0
        st.metric("Efficiency Gain", f"{efficiency:.1f}%")
    
    # Display progressive analysis scoring if available
    if any(chunk.get('score_breakdown') for chunk in chunk_results):
        st.markdown("---")
        display_scoring_analysis(chunk_results)
    
    st.markdown("---")
    
    # Filter and sort options
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_option = st.selectbox(
            "Filter sections:",
            ["All sections", "Sections with issues", "Analyzed sections", "Skipped sections", "High-risk sections"]
        )
    with col2:
        sort_option = st.selectbox(
            "Sort by:",
            ["Position", "Risk Score", "Issue Count"]
        )
    with col3:
        show_text = st.checkbox("Show document text", value=False)
    
    # Filter and sort sections
    filtered_chunks = filter_and_sort_sections(chunk_results, filter_option, sort_option)
    
    if not filtered_chunks:
        st.info(f"No sections match the filter: {filter_option}")
        return
    
    # Display sections
    for i, chunk in enumerate(filtered_chunks):
        display_single_section(chunk, i + 1, show_text)

def display_scoring_analysis(chunk_results: List[Dict]):
    """Display enhanced progressive analysis scoring details."""
    
    st.subheader("🎯 Progressive Analysis Scoring")
    
    # Create scoring summary
    analyzed_chunks = [c for c in chunk_results if c.get('should_analyze', True)]
    skipped_chunks = [c for c in chunk_results if not c.get('should_analyze', True)]
    
    # Calculate scoring statistics
    all_scores = [c.get('risk_score', 0) for c in chunk_results if c.get('risk_score') is not None]
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
    max_score = max(all_scores) if all_scores else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("High Risk (Analyzed)", len(analyzed_chunks))
    with col2:
        st.metric("Low Risk (Skipped)", len(skipped_chunks))
    with col3:
        st.metric("Average Score", f"{avg_score:.1f}")
    with col4:
        st.metric("Maximum Score", f"{max_score:.1f}")
    
    # Show detailed scoring breakdown
    with st.container():
        st.markdown("🔍 **Detailed Scoring Analysis**")
        
        # Create a simple chart of scores
        if all_scores:
            import plotly.express as px
            import pandas as pd
            
            # Prepare data for visualization
            chart_data = []
            for chunk in chunk_results:
                chart_data.append({
                    'Section': chunk.get('position', 'Unknown'),
                    'Risk Score': chunk.get('risk_score', 0),
                    'Status': 'Analyzed' if chunk.get('should_analyze', True) else 'Skipped',
                    'Issues Found': len(chunk.get('issues', []))
                })
            
            df = pd.DataFrame(chart_data)
            
            # Create scatter plot
            fig = px.scatter(df, x='Section', y='Risk Score', 
                           color='Status', size='Issues Found',
                           title="Risk Scores by Section",
                           hover_data=['Issues Found'])
            
            # Add threshold line
            from config import config
            fig.add_hline(y=config.high_risk_threshold, line_dash="dash", 
                         annotation_text="Risk Threshold")
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Show individual section scoring details
        st.markdown("**Individual Section Scores:**")
        
        for chunk in chunk_results:
            score_breakdown = chunk.get('score_breakdown', {})
            if not score_breakdown:
                continue
                
            position = chunk.get('position', 'Unknown')
            total_score = chunk.get('risk_score', 0)
            should_analyze = chunk.get('should_analyze', True)
            analysis_reason = chunk.get('analysis_reason', '')
            skip_reason = chunk.get('skip_reason', '')
            
            status = "🔴 ANALYZED" if should_analyze else "🟢 SKIPPED"
            reason = analysis_reason if should_analyze else skip_reason
            
            # Use containers instead of expanders to avoid nesting
            with st.container():
                st.markdown(f"**{position} - {status} (Score: {total_score:.2f})**")
                
                if reason:
                    st.info(f"**Reason:** {reason}")
                
                # Show score components in a collapsible way using columns
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if st.button(f"Show Details", key=f"details_{position}"):
                        st.session_state[f"show_details_{position}"] = not st.session_state.get(f"show_details_{position}", False)
                
                with col2:
                    if st.session_state.get(f"show_details_{position}", False):
                        # Show score components
                        components = {k: v for k, v in score_breakdown.items() 
                                     if k != 'total_score' and v != 0}
                        
                        if components:
                            st.markdown("**Score Breakdown:**")
                            for component, score in components.items():
                                color = "🔴" if score > 0 else "🟢" if score < 0 else "⚪"
                                component_name = component.replace('_', ' ').title()
                                st.text(f"  {color} {component_name}: {score:.2f}")
                        
                        # Show top contributing terms if available
                        if should_analyze and total_score > 0:
                            st.markdown("*This section was flagged for detailed LLM analysis due to high risk indicators.*")
                        elif not should_analyze:
                            st.markdown("*This section was skipped to improve efficiency.*")
                
                st.markdown("---")

def display_single_section(chunk: Dict, section_number: int, show_text: bool = False):
    """Display a single document section analysis with enhanced metadata."""
    section = chunk.get("position", f"Section {section_number}")
    text = chunk.get("text", "No text available")
    issues = chunk.get("issues", [])
    should_analyze = chunk.get("should_analyze", True)
    risk_score = chunk.get("risk_score", 0)
    analysis_reason = chunk.get("analysis_reason", "")
    skip_reason = chunk.get("skip_reason", "")
    
    # Determine section status and styling
    if not should_analyze:
        status = f"⏭️ Skipped (Score: {risk_score:.1f})"
        status_class = "skipped"
        expander_expanded = False
    elif issues:
        status = f"⚠️ {len(issues)} issues found (Score: {risk_score:.1f})"
        status_class = "has-issues"
        expander_expanded = True
    else:
        status = f"✅ No issues (Score: {risk_score:.1f})"
        status_class = "clean"
        expander_expanded = False
    
    # Use container instead of expander to avoid nesting issues
    with st.container():
        # Create a collapsible section using columns and session state
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"**📄 {section} - {status}**")
        
        with col2:
            expand_key = f"expand_section_{section_number}"
            if st.button("Toggle", key=expand_key):
                st.session_state[expand_key] = not st.session_state.get(expand_key, expander_expanded)
        
        # Show content if expanded
        if st.session_state.get(expand_key, expander_expanded):
            # Show analysis metadata
            if analysis_reason or skip_reason:
                reason = analysis_reason if should_analyze else skip_reason
                st.info(f"**Analysis Decision:** {reason}")
            
            if show_text:
                st.markdown("**📝 Document Text:**")
                with st.container():
                    # Truncate very long text
                    display_text = text[:1000] + "..." if len(text) > 1000 else text
                    st.text_area(
                        "",
                        value=display_text,
                        height=150,
                        key=f"section_text_{section_number}",
                        disabled=True
                    )
            
            if issues:
                st.markdown("**🚨 Issues Found:**")
                for j, issue in enumerate(issues):
                    issue_text = issue.get('issue', 'Unknown issue')
                    regulation = issue.get('regulation', 'Unknown')
                    citation = issue.get('citation', 'No citation')
                    
                    # Clean citation
                    if citation.startswith('"') and citation.endswith('"'):
                        citation = citation[1:-1]
                    
                    st.markdown(f"""
                    <div class="section-issue">
                        <h5>🔸 {j+1}. {issue_text}</h5>
                        <p><strong>Regulation:</strong> {regulation}</p>
                        <p><strong>Citation:</strong> "{citation}"</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                if should_analyze:
                    st.success("✅ No compliance issues detected in this section")
                else:
                    st.info("ℹ️ This section was skipped due to low risk score")
        
        st.markdown("---")

def filter_and_sort_sections(chunk_results: List[Dict], filter_option: str, sort_option: str) -> List[Dict]:
    """Filter and sort sections based on the selected options."""
    
    # Apply filter
    if filter_option == "All sections":
        filtered = chunk_results
    elif filter_option == "Sections with issues":
        filtered = [chunk for chunk in chunk_results if chunk.get("issues", [])]
    elif filter_option == "Analyzed sections":
        filtered = [chunk for chunk in chunk_results if chunk.get("should_analyze", True)]
    elif filter_option == "Skipped sections":
        filtered = [chunk for chunk in chunk_results if not chunk.get("should_analyze", True)]
    elif filter_option == "High-risk sections":
        from config import config
        filtered = [chunk for chunk in chunk_results 
                   if chunk.get("risk_score", 0) >= config.high_risk_threshold]
    else:
        filtered = chunk_results
    
    # Apply sort
    if sort_option == "Position":
        # Keep original order
        pass
    elif sort_option == "Risk Score":
        filtered.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
    elif sort_option == "Issue Count":
        filtered.sort(key=lambda x: len(x.get("issues", [])), reverse=True)
    
    return filtered

def get_regulation_severity(regulation: str, findings: List[Dict]) -> str:
    """Determine severity based on regulation type and number of findings."""
    # High-impact regulations
    high_impact_keywords = ["privacy", "security", "consent", "data protection", "breach"]
    
    regulation_lower = regulation.lower()
    
    # Check for high-impact keywords
    if any(keyword in regulation_lower for keyword in high_impact_keywords):
        return "high"
    
    # Consider number of findings
    if len(findings) >= 5:
        return "high"
    elif len(findings) >= 2:
        return "medium"
    else:
        return "low"

def get_issue_severity(issue_text: str) -> str:
    """Determine issue severity based on keywords in the issue description."""
    issue_lower = issue_text.lower()
    
    # High severity keywords
    high_keywords = ["violation", "breach", "illegal", "unauthorized", "indefinitely", "without consent"]
    
    # Medium severity keywords  
    medium_keywords = ["inadequate", "insufficient", "missing", "unclear", "may violate"]
    
    if any(keyword in issue_lower for keyword in high_keywords):
        return "high"
    elif any(keyword in issue_lower for keyword in medium_keywords):
        return "medium"
    else:
        return "low"

def get_severity_icon(severity: str) -> str:
    """Get appropriate icon for severity level."""
    icons = {
        "high": "🔴",
        "medium": "🟡", 
        "low": "🟢"
    }
    return icons.get(severity, "⚪")