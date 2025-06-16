# utils/report_generator.py

import os
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime

class ReportGenerator:
    """Handles processing of analysis results and report generation - compliance issues only."""
    
    def __init__(self, debug=False):
        """Initialize the report generator."""
        self.debug = debug
        # Track counts for reporting
        self.original_issues_count = 0
        self.deduplicated_issues_count = 0
    
    def process_results(self, chunk_results: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]]]:
        """
        Process analysis results to extract and deduplicate findings.
        
        Args:
            chunk_results: List of chunk analysis results
            
        Returns:
            Tuple containing only deduplicated_findings
        """
        # Extract all issues
        all_findings = []
        
        for chunk_result in chunk_results:
            # Process issues only
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
        
        if self.debug:
            print(f"\nProcessing complete:")
            print(f"  - Raw findings: {self.original_issues_count}")
            print(f"  - After deduplication: {self.deduplicated_issues_count}")
        
        return (deduplicated_findings,)  # Return tuple with single element for backward compatibility
    
    def _normalize_for_deduplication(self, text: str) -> str:
        """Normalize text for better deduplication."""
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove stopwords
        stopwords = ["the", "a", "an", "is", "are", "will", "shall", "should", "may", 
                   "might", "can", "could", "this", "that", "these", "those", "with", 
                   "from", "have", "does", "would", "about", "which"]
        for word in stopwords:
            text = re.sub(r'\b' + word + r'\b', '', text)
            
        # Remove punctuation and extra whitespace
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def deduplicate_issues(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate issues using semantic grouping with improved normalization."""
        if not findings:
            return []
        
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
            
            # Also normalize the regulation reference
            normalized_regulation = self._normalize_regulation(regulation)
            
            # Create a key combining normalized regulation and issue
            key = f"{normalized_regulation}:{normalized_issue[:40]}"
            
            # If this is a new unique issue, add it
            if key not in unique_issues:
                unique_issues[key] = {
                    "issue": finding.get("issue", "Unknown issue"),
                    "regulation": regulation,
                    "confidence": finding.get("confidence", "Medium"),
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
                    # Update with the analyzed version
                    existing["should_analyze"] = True
                    existing["explanation"] = finding.get("explanation", "")
                    if "citation" in finding and finding["citation"] != "No specific quote provided.":
                        existing["citation"] = finding["citation"]
                
                # Combine sections
                if isinstance(existing["section"], list):
                    # Already a list, add new section if not present
                    if isinstance(section, list):
                        for s in section:
                            if s not in existing["section"]:
                                existing["section"].append(s)
                    elif section not in existing["section"]:
                        existing["section"].append(section)
                else:
                    # Convert to list if adding a different section
                    if isinstance(section, list):
                        existing["section"] = [existing["section"]] + section
                    elif section != existing["section"]:
                        existing["section"] = [existing["section"], section]
                
                # Use higher confidence if available
                confidence_value = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
                if confidence_value.get(finding.get("confidence", "").upper(), 0) > confidence_value.get(existing["confidence"].upper(), 0):
                    existing["confidence"] = finding.get("confidence", "Medium")
        
        # Convert dictionary to list and sort by confidence and regulation
        result = list(unique_issues.values())
        result.sort(key=lambda x: (
            {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x.get("confidence", "").upper(), 3),
            x.get("regulation", "")
        ))
        
        return result
    
    def _normalize_regulation(self, regulation: str) -> str:
        """Normalize regulation references for better deduplication."""
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
            # Keep just the regulation number for matching
            section_type = pattern.findall(normalized)[0].lower()
            section_num = match.group(1)
            return f"{section_type}{section_num}"
            
        return normalized
    
    def export_report(self, export_path, analyzed_file, regulation_framework, findings, 
                  document_metadata, chunk_results):
        """Export a detailed report of compliance issues only."""
        try:
            # Use string buffer for more efficient string operations
            report_lines = []
            
            # Write report header
            report_lines.append("=" * 80)
            report_lines.append(f"{regulation_framework.upper()} COMPLIANCE ANALYSIS REPORT")
            report_lines.append("=" * 80 + "\n")
            
            # Document information
            report_lines.append(f"Document: {os.path.basename(analyzed_file)}")
            report_lines.append(f"Document Type: {document_metadata.get('document_type', 'Unknown')}")
            report_lines.append(f"Regulation: {regulation_framework}")
            report_lines.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Data context
            report_lines.append("POTENTIAL DATA CONTEXT:")
            report_lines.append(f"Data mentions: {', '.join(document_metadata.get('potential_data_mentions', ['None detected']))}")
            report_lines.append(f"Compliance indicators: {', '.join(document_metadata.get('compliance_indicators', ['None detected']))}\n")
            
            # Count total issues
            total_issues = len(findings)
            
            report_lines.append(f"Total Issues Found: {total_issues}")
            
            # Add analysis method to report
            has_progressive = any("should_analyze" in chunk for chunk in chunk_results)
            if has_progressive:
                report_lines.append("Analysis Method: Progressive (focused on relevant sections)")
                
                # Count issues by analysis type
                analyzed_issues = sum(1 for f in findings if f.get("should_analyze", True))
                skipped_issues = total_issues - analyzed_issues
                
                report_lines.append(f"- From analyzed sections: {analyzed_issues}")
                report_lines.append(f"- From skipped sections: {skipped_issues}")
            
            # Add processing information
            report_lines.append(f"\nPROCESSING SUMMARY:")
            report_lines.append(f"- Original issues: {self.original_issues_count} → Final: {self.deduplicated_issues_count}")
            
            if total_issues > 0:
                # Count by confidence
                high_confidence = sum(1 for f in findings if f.get("confidence", "").upper() == "HIGH")
                medium_confidence = sum(1 for f in findings if f.get("confidence", "").upper() == "MEDIUM")
                low_confidence = sum(1 for f in findings if f.get("confidence", "").upper() == "LOW")
                
                report_lines.append("\nCONFIDENCE BREAKDOWN OF ISSUES:")
                report_lines.append(f"- High Confidence Issues: {high_confidence}")
                report_lines.append(f"- Medium Confidence Issues: {medium_confidence}")
                report_lines.append(f"- Low Confidence Issues: {low_confidence}\n")
                
                # Group issues by regulation for summary
                report_lines.append("SUMMARY OF COMPLIANCE CONCERNS:")
                report_lines.append("-" * 80 + "\n")
                
                # Group findings by regulation
                by_regulation = {}
                for finding in findings:
                    regulation = finding.get("regulation", "Unknown regulation")
                    if regulation not in by_regulation:
                        by_regulation[regulation] = []
                    by_regulation[regulation].append(finding)
                
                # Display regulations with their issues
                for regulation, reg_issues in by_regulation.items():
                    report_lines.append(f"{regulation}:")
                    
                    # Group sections for this regulation
                    section_mentions = {}
                    for issue in reg_issues:
                        issue_desc = issue.get("issue", "Unknown issue")
                        section = issue.get("section", "Unknown section")
                        confidence = issue.get("confidence", "Medium")
                        should_analyze = issue.get("should_analyze", True)
                        
                        # Format analysis indicator
                        if not should_analyze:
                            display_analysis = " (SKIPPED)"
                        else:
                            display_analysis = ""
                        
                        # Normalize section to ensure it's a string or list of strings
                        if isinstance(section, list):
                            # Flatten nested lists
                            flat_sections = []
                            for s in section:
                                if isinstance(s, list):
                                    flat_sections.extend(str(item) for item in s)
                                else:
                                    flat_sections.append(str(s))
                            section = flat_sections
                        
                        if issue_desc not in section_mentions:
                            section_mentions[issue_desc] = {
                                "sections": [section] if isinstance(section, str) else section,
                                "confidence": confidence,
                                "should_analyze": should_analyze
                            }
                        else:
                            if isinstance(section, str):
                                if section not in section_mentions[issue_desc]["sections"]:
                                    section_mentions[issue_desc]["sections"].append(section)
                            else:
                                # Add each item from the list
                                for s in section:
                                    if s not in section_mentions[issue_desc]["sections"]:
                                        section_mentions[issue_desc]["sections"].append(s)
                    
                    # Display issues with their sections
                    for issue_desc, details in section_mentions.items():
                        sections = details["sections"]
                        confidence = details["confidence"]
                        should_analyze = details.get("should_analyze", True)
                        
                        # Format analysis indicator
                        if not should_analyze:
                            display_analysis = " (SKIPPED)"
                        else:
                            display_analysis = ""
                        
                        # Ensure all sections are strings
                        sections = [str(s) for s in sections]
                        
                        # Format sections nicely
                        if len(sections) <= 2:
                            section_text = ", ".join(sections)
                        else:
                            section_text = f"{sections[0]}, {sections[1]} and {len(sections)-2} more"
                        
                        report_lines.append(f"  - {issue_desc}{display_analysis} (in {section_text}, {confidence} confidence)")
                    
                    report_lines.append("")
                
                report_lines.append("-" * 80 + "\n")
            
            # Add detailed section-by-section analysis
            report_lines.append("DETAILED ANALYSIS BY SECTION:")
            report_lines.append("=" * 80 + "\n")
            
            # Process all chunks in order, with or without issues
            for chunk_index, chunk in enumerate(chunk_results):
                section = chunk.get("position", "Unknown section")
                text = chunk.get("text", "Text not available")
                issues = chunk.get("issues", [])
                should_analyze = chunk.get("should_analyze", True)
                
                # Add analysis status to section title
                analysis_display = "" if should_analyze else " [SKIPPED]"
                
                report_lines.append(f"SECTION #{chunk_index + 1} - {section}{analysis_display}")
                report_lines.append("-" * 80 + "\n")
                
                # Display section text
                report_lines.append("DOCUMENT TEXT:")
                report_lines.append(f"{text}\n")
                
                # Display issues if any
                if issues:
                    report_lines.append("COMPLIANCE ISSUES:\n")
                    
                    for i, finding in enumerate(issues):
                        issue = finding.get("issue", "Unknown issue")
                        regulation = finding.get("regulation", "Unknown regulation")
                        confidence = finding.get("confidence", "Medium")
                        citation = finding.get("citation", "")
                        
                        # Clean up any asterisks from issue descriptions
                        issue = re.sub(r'\*+', '', issue)
                        
                        report_lines.append(f"Issue {i+1}: {issue}")
                        report_lines.append(f"Regulation: {regulation}")
                        report_lines.append(f"Confidence: {confidence}")
                        
                        if citation:
                            # Clean up citation formatting
                            if citation.strip() == "None" or citation.strip() == "":
                                citation = "No specific quote provided."
                            elif not citation.startswith('"') and not citation.endswith('"'):
                                citation = f'"{citation}"'
                            report_lines.append(f"Citation: {citation}")
                        
                        if i < len(issues) - 1:
                            report_lines.append("-" * 40 + "\n")
                else:
                    if not should_analyze:
                        report_lines.append("NO COMPLIANCE ISSUES DETECTED IN THIS SKIPPED SECTION")
                    else:
                        report_lines.append("NO COMPLIANCE ISSUES DETECTED IN THIS SECTION")
                
                report_lines.append("")
                report_lines.append("=" * 80 + "\n")
            
            # Write the entire report to the file
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(report_lines))
            
            return True
            
        except Exception as e:
            print(f"Error exporting report: {e}")
            import traceback
            traceback.print_exc()  # Print full traceback for better debugging
            return False