import os
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

class ReportGenerator:
    """Handles analysis results processing and report generation."""
    
    def __init__(self, debug=False):
        self.debug = debug
        self.original_issues_count = 0
        self.deduplicated_issues_count = 0
    
    def process_results(self, chunk_results: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]]]:
        """Process analysis results and deduplicate findings."""
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
                issue_copy.setdefault("should_analyze", chunk_result.get("should_analyze", True))
                
                all_findings.append(issue_copy)
        
        self.original_issues_count = len(all_findings)
        
        # Deduplicate
        deduplicated = self.deduplicate_issues(all_findings)
        self.deduplicated_issues_count = len(deduplicated)
        
        if self.debug:
            print(f"Results: {self.original_issues_count} → {self.deduplicated_issues_count} after dedup")
        
        return (deduplicated,)
    
    def deduplicate_issues(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate issues using simple text similarity."""
        if not findings:
            return []
        
        unique_issues = {}
        
        for finding in findings:
            issue_text = finding.get("issue", "")
            regulation = finding.get("regulation", "Unknown")
            
            # Create normalized key for deduplication
            normalized_issue = self._normalize_text(issue_text)
            normalized_reg = self._normalize_text(regulation)
            key = f"{normalized_reg}:{normalized_issue[:50]}"
            
            if key not in unique_issues:
                unique_issues[key] = finding.copy()
            else:
                # Merge sections if different
                existing = unique_issues[key]
                self._merge_sections(existing, finding)
        
        # Sort by regulation
        result = list(unique_issues.values())
        result.sort(key=lambda x: x.get("regulation", ""))
        
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        
        # Remove punctuation and extra whitespace
        text = re.sub(r'[^\w\s]', '', text.lower())
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common words
        stopwords = ["the", "a", "an", "is", "are", "will", "shall", "this", "that"]
        for word in stopwords:
            text = re.sub(r'\b' + word + r'\b', '', text)
        
        return text[:50]  # Limit length
    
    def _merge_sections(self, existing: Dict, new: Dict):
        """Merge section information between similar issues."""
        existing_section = existing.get("section", "")
        new_section = new.get("section", "")
        
        if new_section and new_section != existing_section:
            if isinstance(existing_section, list):
                if new_section not in existing_section:
                    existing_section.append(new_section)
            else:
                existing["section"] = [existing_section, new_section]
    
    def export_report(self, export_path, analyzed_file, regulation_framework, findings, 
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
        lines.append(f"Document: {os.path.basename(analyzed_file)}")
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
            should_analyze = chunk.get("should_analyze", True)
            
            status = "" if should_analyze else " [SKIPPED]"
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