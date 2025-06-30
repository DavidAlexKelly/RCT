import streamlit as st
import json
import tempfile
import os
from datetime import datetime
from typing import Dict, Any, Optional

def handle_exports(results: Dict[str, Any], uploaded_file: Optional[st.runtime.uploaded_file_manager.UploadedFile]):
    """Handle all export options for analysis results."""
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        handle_detailed_report_export(results, uploaded_file)
    
    with col2:
        handle_json_export(results, uploaded_file)
    
    with col3:
        handle_summary_export(results, uploaded_file)

def handle_detailed_report_export(results: Dict[str, Any], uploaded_file: Optional[st.runtime.uploaded_file_manager.UploadedFile]):
    """Handle detailed text report export - single click download."""
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"compliance_report_{timestamp}.txt"
    
    # Function to generate report content when button is clicked
    @st.cache_data
    def generate_detailed_report():
        try:
            # Get the report generator from results
            report_generator = results.get("report_generator")
            if not report_generator:
                from utils.report_generator import ReportGenerator
                report_generator = ReportGenerator(debug=False)
            
            # Create temporary file for the report
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as tmp_file:
                success = report_generator.export_report(
                    export_path=tmp_file.name,
                    analysed_file=uploaded_file.name if uploaded_file else "document",
                    regulation_framework=results["config"]["framework"],
                    findings=results["findings"],
                    document_metadata=results["metadata"],
                    chunk_results=results["chunk_results"]
                )
                
                if success:
                    # Read the generated report
                    with open(tmp_file.name, 'r', encoding='utf-8') as f:
                        report_content = f.read()
                    
                    # Clean up
                    try:
                        os.unlink(tmp_file.name)
                    except:
                        pass
                    
                    return report_content
                else:
                    return "Error: Failed to generate detailed report"
                    
        except Exception as e:
            return f"Error generating detailed report: {e}"
    
    # Single-click download button
    report_content = generate_detailed_report()
    
    st.download_button(
        label="📄 Download Detailed Report",
        data=report_content,
        file_name=filename,
        mime="text/plain",
        use_container_width=True,
        help="Generate and download comprehensive text report"
    )

def handle_json_export(results: Dict[str, Any], uploaded_file: Optional[st.runtime.uploaded_file_manager.UploadedFile]):
    """Handle JSON export - single click download."""
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"compliance_results_{timestamp}.json"
    
    # Function to generate JSON content when button is clicked
    @st.cache_data
    def generate_json_export():
        try:
            # Prepare JSON data (exclude report_generator object)
            json_data = {
                "document": uploaded_file.name if uploaded_file else "document",
                "framework": results["config"]["framework"],
                "analysis_date": datetime.now().isoformat(),
                "analysis_config": {
                    "model": results["config"]["model"],
                    "preset": results["config"]["preset"],
                    "analysis_type": results["config"]["analysis_type"],
                    "rag_articles": results["config"].get("rag_articles", "N/A"),
                    "risk_threshold": results["config"].get("risk_threshold", "N/A")
                },
                "summary": {
                    "total_issues": len(results["findings"]),
                    "total_sections": results["config"]["total_sections"],
                    "analysed_sections": results["config"]["analysed_sections"],
                    "document_type": results["metadata"].get("document_type", "unknown")
                },
                "findings": results["findings"],
                "metadata": results["metadata"]
            }
            
            # Create JSON string with nice formatting
            return json.dumps(json_data, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f'{{"error": "Failed to generate JSON export: {e}"}}'
    
    # Single-click download button
    json_content = generate_json_export()
    
    st.download_button(
        label="📊 Download JSON Data",
        data=json_content,
        file_name=filename,
        mime="application/json",
        use_container_width=True,
        help="Export results as structured JSON"
    )

def handle_summary_export(results: Dict[str, Any], uploaded_file: Optional[st.runtime.uploaded_file_manager.UploadedFile]):
    """Handle summary export - single click download."""
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"compliance_summary_{timestamp}.txt"
    
    # Function to generate summary content when button is clicked
    @st.cache_data
    def generate_summary_export():
        try:
            return generate_summary_content(results, uploaded_file)
        except Exception as e:
            return f"Error generating summary: {e}"
    
    # Single-click download button
    summary_content = generate_summary_export()
    
    st.download_button(
        label="📋 Download Summary",
        data=summary_content,
        file_name=filename,
        mime="text/plain",
        use_container_width=True,
        help="Export executive summary"
    )

def generate_summary_content(results: Dict[str, Any], uploaded_file: Optional[st.runtime.uploaded_file_manager.UploadedFile]) -> str:
    """Generate executive summary content."""
    
    findings = results["findings"]
    config = results["config"]
    metadata = results["metadata"]
    
    # Count issues by regulation
    regulation_counts = {}
    for finding in findings:
        reg = finding.get("regulation", "Unknown")
        regulation_counts[reg] = regulation_counts.get(reg, 0) + 1
    
    # Generate summary
    summary_lines = [
        "REGULATORY COMPLIANCE ANALYSIS - EXECUTIVE SUMMARY",
        "=" * 60,
        "",
        f"Document: {uploaded_file.name if uploaded_file else 'Unknown'}",
        f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Framework: {config['framework'].upper()}",
        f"Analysis Type: {config['analysis_type']}",
        "",
        "OVERVIEW:",
        f"• Total Issues Found: {len(findings)}",
        f"• Regulations Affected: {len(regulation_counts)}",
        f"• Document Type: {metadata.get('document_type', 'Unknown')}",
        f"• Sections Analysed: {config['analysed_sections']} of {config['total_sections']}",
        "",
    ]
    
    if findings:
        summary_lines.extend([
            "ISSUES BY REGULATION:",
            "-" * 30,
        ])
        
        for regulation, count in sorted(regulation_counts.items(), key=lambda x: x[1], reverse=True):
            summary_lines.append(f"• {regulation}: {count} issues")
        
        summary_lines.extend([
            "",
            "TOP ISSUES:",
            "-" * 15,
        ])
        
        # Show top 5 issues
        for i, finding in enumerate(findings[:5], 1):
            issue = finding.get("issue", "Unknown issue")
            regulation = finding.get("regulation", "Unknown")
            summary_lines.append(f"{i}. {issue} ({regulation})")
        
        if len(findings) > 5:
            summary_lines.append(f"   ... and {len(findings) - 5} more issues")
        
        summary_lines.extend([
            "",
            "RECOMMENDATIONS:",
            "-" * 20,
            "• Review all identified issues with legal counsel",
            "• Prioritize issues based on regulation severity",
            "• Implement corrective measures for critical violations",
            "• Consider regular compliance audits",
        ])
    else:
        summary_lines.extend([
            "COMPLIANCE STATUS:",
            "✅ No compliance issues detected",
            "",
            "RECOMMENDATIONS:",
            "• Maintain current compliance practices",
            "• Consider periodic reviews to ensure ongoing compliance",
            "• Stay updated on regulation changes",
        ])
    
    summary_lines.extend([
        "",
        "ANALYSIS CONFIGURATION:",
        f"• Model: {config['model']}",
        f"• Performance Preset: {config['preset']}",
        f"• RAG Articles: {config.get('rag_articles', 'N/A')}",
        f"• Risk Threshold: {config.get('risk_threshold', 'N/A')}",
        "",
        "This summary was generated by the Regulatory Compliance Analyser."
    ])
    
    return "\n".join(summary_lines)