import os
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

class ReportGenerator:
    """Handles analysis results processing and report generation."""
    
    def __init__(self, debug=False):
        self.debug = debug
        self.total_issues_count = 0
    
    def process_results(self, chunk_results: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]]]:
        """Process analysis results without deduplication."""
        assert chunk_results, "chunk_results cannot be empty"
        
        # Extract all issues
        all_findings = []
        for i, chunk_result in enumerate(chunk_results):
            issues = chunk_result.get("issues", [])
            if not isinstance(issues, list):
                continue
            
            for issue in issues:
                if not isinstance(issue, dict) or not issue.get("issue", "").strip():
                    continue
                
                # Add metadata
                issue_copy = issue.copy()
                issue_copy.setdefault("section", chunk_result.get("position", f"Chunk {i+1}"))
                issue_copy.setdefault("text", chunk_result.get("text", ""))
                issue_copy.setdefault("should_analyse", chunk_result.get("should_analyse", True))
                
                all_findings.append(issue_copy)
        
        self.total_issues_count = len(all_findings)
        
        if self.debug:
            print(f"Results: {self.total_issues_count} total violations found")
        
        return (all_findings,)
    
    def export_report(self, export_path, analysed_file, regulation_framework, findings, 
                      document_metadata, chunk_results):
        """Export detailed report to file."""
        export_path = Path(export_path)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build report content
        lines = []
        lines.append("=" * 80)
        lines.append(f"{regulation_framework.upper()} COMPLIANCE ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Document info
        lines.append(f"Document: {os.path.basename(analysed_file)}")
        lines.append(f"Framework: {regulation_framework}")
        lines.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total Issues: {len(findings)}")
        lines.append("")
        
        # Summary by regulation
        if findings:
            by_regulation = {}
            for finding in findings:
                reg = finding.get("regulation", "Unknown")
                by_regulation.setdefault(reg, []).append(finding)
            
            lines.append("ISSUES BY REGULATION:")
            lines.append("-" * 40)
            for reg, issues in sorted(by_regulation.items()):
                lines.append(f"{reg}: {len(issues)} issues")
                for issue in issues:
                    lines.append(f"  - {issue.get('issue', 'Unknown issue')}")
            lines.append("")
        
        # Detailed section analysis
        lines.append("DETAILED ANALYSIS:")
        lines.append("=" * 80)
        
        for i, chunk in enumerate(chunk_results):
            section = chunk.get("position", f"Section {i + 1}")
            text = chunk.get("text", "")
            issues = chunk.get("issues", [])
            should_analyse = chunk.get("should_analyse", True)
            
            status = "" if should_analyse else " [SKIPPED]"
            lines.append(f"SECTION {i + 1} - {section}{status}")
            lines.append("-" * 80)
            
            # Show text preview
            preview = text[:500] + "..." if len(text) > 500 else text
            lines.append(f"TEXT: {preview}")
            lines.append("")
            
            # Show issues
            if issues:
                lines.append("ISSUES:")
                for j, issue in enumerate(issues):
                    lines.append(f"{j+1}. {issue.get('issue', 'Unknown')}")
                    lines.append(f"   Regulation: {issue.get('regulation', 'Unknown')}")
                    citation = issue.get('citation', '')
                    if citation:
                        lines.append(f"   Citation: {citation}")
                    lines.append("")
            else:
                lines.append("No issues found in this section.")
            
            lines.append("=" * 80)
            lines.append("")
        
        # Write report
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            
            if self.debug:
                print(f"Report exported to {export_path}")
            
            return True
            
        except Exception as e:
            if self.debug:
                print(f"Export failed: {e}")
            raise RuntimeError(f"Failed to export report: {e}")