import streamlit as st
from typing import Dict, Any, List

def display_findings(findings: List[Dict], chunk_results: List[Dict]):
    """Display findings in a clean, user-friendly way."""
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
        st.metric("Most Common", f"{most_common_reg.split()[0]} ({len(by_regulation[most_common_reg])})")
    
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
    """Display clean section-by-section analysis."""
    if not chunk_results:
        st.info("No section analysis data available.")
        return
    
    # Simple summary statistics
    total_sections = len(chunk_results)
    sections_with_issues = sum(1 for chunk in chunk_results if chunk.get("issues", []))
    
    # Display summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Sections", total_sections)
    with col2:
        st.metric("With Issues", sections_with_issues)
    with col3:
        clean_sections = total_sections - sections_with_issues
        st.metric("Clean Sections", clean_sections)
    
    st.markdown("---")
    
    # Filter options (simplified)
    col1, col2 = st.columns(2)
    with col1:
        filter_option = st.selectbox(
            "Show sections:",
            ["All sections", "Sections with issues", "Clean sections"]
        )
    with col2:
        show_text = st.checkbox("Show document text", value=False)
    
    # Filter sections
    if filter_option == "Sections with issues":
        filtered_chunks = [chunk for chunk in chunk_results if chunk.get("issues", [])]
    elif filter_option == "Clean sections":
        filtered_chunks = [chunk for chunk in chunk_results if not chunk.get("issues", [])]
    else:
        filtered_chunks = chunk_results
    
    if not filtered_chunks:
        st.info(f"No sections match the filter: {filter_option}")
        return
    
    # Display sections
    for i, chunk in enumerate(filtered_chunks):
        display_single_section(chunk, i + 1, show_text)

def display_single_section(chunk: Dict, section_number: int, show_text: bool = False):
    """Display a single document section analysis."""
    section = chunk.get("position", f"Section {section_number}")
    text = chunk.get("text", "No text available")
    issues = chunk.get("issues", [])
    
    # Determine section status
    if issues:
        status = f"⚠️ {len(issues)} issues found"
        status_class = "has-issues"
        expander_expanded = True
    else:
        status = f"✅ No issues"
        status_class = "clean"
        expander_expanded = False
    
    # Use expander for each section
    with st.expander(f"📄 {section} - {status}", expanded=expander_expanded):
        if show_text:
            st.markdown("**📝 Document Text:**")
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
            st.success("✅ No compliance issues detected in this section")

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