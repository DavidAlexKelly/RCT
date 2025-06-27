"""
Report Generator Module

Handles processing of analysis results and comprehensive report generation.
Manages deduplication, formatting, and export of compliance findings.
"""

import os
import re
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Processes analysis results and generates comprehensive compliance reports.
    
    Handles deduplication of findings, result formatting, and export to various formats.
    """
    
    def __init__(self, debug: bool = False) -> None:
        """
        Initialize the report generator.
        
        Args:
            debug: Enable debug logging (deprecated, use logging configuration)
        """
        self.debug = debug
        self.original_issues_count = 0
        self.deduplicated_issues_count = 0
        
        logger.info("ReportGenerator initialized")
    
    def process_results(self, chunk_results: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]]]:
        """
        Process analysis results to extract and deduplicate findings.
        
        Args:
            chunk_results: List of chunk analysis results
            
        Returns:
            Tuple containing deduplicated findings
        """
        # Extract all issues from chunk results
        all_findings = []
        
        for chunk_result in chunk_results:
            # Process issues from this chunk
            for issue in chunk_result.get("issues", []):
                # Ensure issue has all required fields
                issue_copy = issue.copy()
                if "section" not in issue_copy:
                    issue_copy["section"] = chunk_result.get("position", "Unknown")
                if "text" not in issue_copy:
                    issue_copy["text"] = chunk_result.get("text", "")
                if "should_analyze" not in issue_copy:
                    issue_copy["should_analyze"] = chunk_result.get("should_analyze", True)
                
                all_findings.append(issue_copy)
        
        # Store original counts
        self.original_issues_count = len(all_findings)
        
        # Deduplicate findings
        deduplicated_findings = self.deduplicate_issues(all_findings)
        
        # Store deduplicated counts
        self.deduplicated_issues_count = len(deduplicated_findings)
        
        logger.info(f"Processing complete: {self.original_issues_count} raw findings → "
                   f"{self.deduplicated_issues_count} deduplicated")
        
        return (deduplicated_findings,)
    
    def deduplicate_issues(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate issues using semantic grouping.
        
        Args:
            findings: List of findings to deduplicate
            
        Returns:
            List of deduplicated findings
        """
        if not findings:
            return []
        
        logger.debug(f"Deduplicating {len(findings)} findings")
        
        # Group by regulation and normalized issue description
        unique_issues = {}
        
        for finding in findings:
            # Skip findings without issues
            if not finding.get("issue"):
                continue
                
            # Get key components
            regulation = finding.get("regulation", "Unknown regulation")
            issue_text = finding.get("issue", "")
            section = finding.get("section", "Unknown")
            should_analyze = finding.get("should_analyze", True)
            
            # Normalize the issue text for better deduplication
            normalized_issue = self._normalize_for_deduplication(issue_text)
            normalized_regulation = self._normalize_regulation(regulation)
            
            # Create a key combining normalized regulation and issue
            key = f"{normalized_regulation}:{normalized_issue[:40]}"
            
            # If this is a new unique issue, add it
            if key not in unique_issues:
                unique_issues[key] = {
                    "issue": finding.get("issue", "Unknown issue"),
                    "regulation": regulation,
                    "explanation": finding.get("explanation", ""),
                    "section": section,
                    "text": finding.get("text", ""),
                    "should_analyze": should_analyze
                }
                if "citation" in finding:
                    unique_issues[key]["citation"] = finding["citation"]
            else:
                # Update existing entry
                existing = unique_issues[key]
                
                # Give priority to analyzed findings over skipped ones
                if should_analyze and not existing.get("should_analyze", True):
                    existing["should_analyze"] = True
                    existing["explanation"] = finding.get("explanation", "")
                    if "citation" in finding and finding["citation"] != "No specific quote provided.":
                        existing["citation"] = finding["citation"]
                
                # Combine sections
                existing["section"] = self._combine_sections(existing["section"], section)
        
        # Convert dictionary to list and sort by regulation
        result = list(unique_issues.values())
        result.sort(key=lambda x: x.get("regulation", ""))
        
        logger.debug(f"Deduplication complete: {len(result)} unique issues")
        return result
    
    def export_report(self, export_path: str, analyzed_file: str, 
                     regulation_framework: str, findings: List[Dict[str, Any]], 
                     document_metadata: Dict[str, Any], 
                     chunk_results: List[Dict[str, Any]]) -> bool:
        """
        Export a detailed compliance report.
        
        Args:
            export_path: Path to export the report to
            analyzed_file: Original file that was analyzed
            regulation_framework: Regulation framework used
            findings: Deduplicated findings
            document_metadata: Document metadata
            chunk_results: Original chunk analysis results
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            logger.info(f"Exporting report to {export_path}")
            
            # Generate report content
            report_content = self._generate_report_content(
                analyzed_file, regulation_framework, findings, 
                document_metadata, chunk_results
            )
            
            # Write to file
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"Report exported successfully to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            return False
    
    def _normalize_for_deduplication(self, text: str) -> str:
        """
        Normalize text for better deduplication.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove stopwords
        stopwords = {
            "the", "a", "an", "is", "are", "will", "shall", "should", "may", 
            "might", "can", "could", "this", "that", "these", "those", "with", 
            "from", "have", "does", "would", "about", "which"
        }
        
        words = text.split()
        words = [word for word in words if word not in stopwords]
        text = " ".join(words)
        
        # Remove punctuation and extra whitespace
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _normalize_regulation(self, regulation: str) -> str:
        """
        Normalize regulation references for better deduplication.
        
        Args:
            regulation: Regulation reference to normalize
            
        Returns:
            Normalized regulation reference
        """
        if not regulation:
            return "unknown"
            
        # Convert to lowercase
        normalized = regulation.lower()
        
        # Remove punctuation and extra whitespace
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Extract regulation/article numbers if present
        pattern = re.compile(r'(?:article|regulation|section|rule)\s+(\d+)', re.I)
        match = pattern.search(normalized)
        if match:
            section_type = "article" if "article" in normalized else "regulation"
            section_num = match.group(1)
            return f"{section_type}{section_num}"
            
        return normalized
    
    def _combine_sections(self, existing_section: Any, new_section: str) -> Any:
        """
        Combine section references for deduplicated findings.
        
        Args:
            existing_section: Existing section reference (string or list)
            new_section: New section to add
            
        Returns:
            Combined section reference
        """
        if isinstance(existing_section, list):
            # Already a list, add new section if not present
            if new_section not in existing_section:
                existing_section.append(new_section)
            return existing_section
        else:
            # Convert to list if adding a different section
            if new_section != existing_section:
                return [existing_section, new_section]
            return existing_section
    
    def _generate_report_content(self, analyzed_file: str, regulation_framework: str,
                                findings: List[Dict[str, Any]], document_metadata: Dict[str, Any],
                                chunk_results: List[Dict[str, Any]]) -> str:
        """
        Generate the complete report content.
        
        Args:
            analyzed_file: File that was analyzed
            regulation_framework: Regulation framework used
            findings: Deduplicated findings
            document_metadata: Document metadata
            chunk_results: Chunk analysis results
            
        Returns:
            Complete report as string
        """
        lines = []
        
        # Header
        lines.extend([
            "=" * 80,
            f"{regulation_framework.upper()} COMPLIANCE ANALYSIS REPORT",
            "=" * 80,
            "",
            f"Document: {os.path.basename(analyzed_file)}",
            f"Document Type: {document_metadata.get('document_type', 'Unknown')}",
            f"Regulation: {regulation_framework}",
            f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ])
        
        # Data context
        lines.extend([
            "POTENTIAL DATA CONTEXT:",
            f"Data mentions: {', '.join(document_metadata.get('potential_data_mentions', ['None detected']))}",
            f"Compliance indicators: {', '.join(document_metadata.get('compliance_indicators', ['None detected']))}",
            ""
        ])
        
        # Summary statistics
        total_issues = len(findings)
        has_progressive = any("should_analyze" in chunk for chunk in chunk_results)
        
        lines.append(f"Total Issues Found: {total_issues}")
        
        if has_progressive:
            lines.append("Analysis Method: Progressive (focused on relevant sections)")
            analyzed_issues = sum(1 for f in findings if f.get("should_analyze", True))
            skipped_issues = total_issues - analyzed_issues
            lines.extend([
                f"- From analyzed sections: {analyzed_issues}",
                f"- From skipped sections: {skipped_issues}"
            ])
        
        lines.extend([
            "",
            f"PROCESSING SUMMARY:",
            f"- Original issues: {self.original_issues_count} → Final: {self.deduplicated_issues_count}",
            ""
        ])
        
        # Issues summary
        if total_issues > 0:
            lines.extend([
                "SUMMARY OF COMPLIANCE CONCERNS:",
                "-" * 80,
                ""
            ])
            
            # Group findings by regulation
            by_regulation = {}
            for finding in findings:
                regulation = finding.get("regulation", "Unknown regulation")
                if regulation not in by_regulation:
                    by_regulation[regulation] = []
                by_regulation[regulation].append(finding)
            
            # Display regulations with their issues
            for regulation in sorted(by_regulation.keys()):
                reg_issues = by_regulation[regulation]
                lines.append(f"{regulation}:")
                
                for issue in reg_issues:
                    issue_desc = issue.get("issue", "Unknown issue")
                    sections = issue.get("section", "Unknown section")
                    should_analyze = issue.get("should_analyze", True)
                    
                    # Format analysis indicator
                    analysis_indicator = "" if should_analyze else " (SKIPPED)"
                    
                    # Format sections
                    if isinstance(sections, list):
                        if len(sections) <= 2:
                            section_text = ", ".join(str(s) for s in sections)
                        else:
                            section_text = f"{sections[0]}, {sections[1]} and {len(sections)-2} more"
                    else:
                        section_text = str(sections)
                    
                    lines.append(f"  - {issue_desc}{analysis_indicator} (in {section_text})")
                
                lines.append("")
            
            lines.extend(["-" * 80, ""])
        
        # Detailed section-by-section analysis
        lines.extend([
            "DETAILED ANALYSIS BY SECTION:",
            "=" * 80,
            ""
        ])
        
        for chunk_index, chunk in enumerate(chunk_results):
            section = chunk.get("position", "Unknown section")
            text = chunk.get("text", "Text not available")
            issues = chunk.get("issues", [])
            should_analyze = chunk.get("should_analyze", True)
            
            # Section header
            analysis_display = "" if should_analyze else " [SKIPPED]"
            lines.extend([
                f"SECTION #{chunk_index + 1} - {section}{analysis_display}",
                "-" * 80,
                "",
                "DOCUMENT TEXT:",
                f"{text}",
                ""
            ])
            
            # Issues for this section
            if issues:
                lines.append("COMPLIANCE ISSUES:")
                lines.append("")
                
                for i, finding in enumerate(issues):
                    issue = finding.get("issue", "Unknown issue")
                    regulation = finding.get("regulation", "Unknown regulation")
                    citation = finding.get("citation", "")
                    
                    # Clean up issue description
                    issue = re.sub(r'\*+', '', issue)
                    
                    lines.extend([
                        f"Issue {i+1}: {issue}",
                        f"Regulation: {regulation}"
                    ])
                    
                    if citation:
                        if citation.strip() in ["None", ""]:
                            citation = "No specific quote provided."
                        elif not citation.startswith('"') and not citation.endswith('"'):
                            citation = f'"{citation}"'
                        lines.append(f"Citation: {citation}")
                    
                    if i < len(issues) - 1:
                        lines.append("-" * 40)
                    lines.append("")
            else:
                if not should_analyze:
                    lines.append("NO COMPLIANCE ISSUES DETECTED IN THIS SKIPPED SECTION")
                else:
                    lines.append("NO COMPLIANCE ISSUES DETECTED IN THIS SECTION")
            
            lines.extend(["", "=" * 80, ""])
        
        return "\n".join(lines)