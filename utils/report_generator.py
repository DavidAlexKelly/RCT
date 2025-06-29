# utils/report_generator.py - Proper error handling without fallbacks

import os
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

class ReportGenerator:
    """Handles processing of analysis results and report generation with proper error handling."""
    
    def __init__(self, debug=False):
        """Initialize the report generator with validation."""
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
        # Validate input
        if not chunk_results:
            raise ValueError("chunk_results cannot be empty")
        
        if not isinstance(chunk_results, list):
            raise ValueError("chunk_results must be a list")
        
        # Validate chunk structure
        for i, chunk_result in enumerate(chunk_results):
            if not isinstance(chunk_result, dict):
                raise ValueError(f"Chunk result {i+1} must be a dictionary")
        
        # Extract all issues with validation
        all_findings = []
        
        for i, chunk_result in enumerate(chunk_results):
            try:
                # Process issues from this chunk
                chunk_issues = chunk_result.get("issues", [])
                
                if not isinstance(chunk_issues, list):
                    if self.debug:
                        print(f"Warning: Chunk {i+1} has non-list issues field")
                    continue
                
                for j, issue in enumerate(chunk_issues):
                    if not isinstance(issue, dict):
                        if self.debug:
                            print(f"Warning: Skipping non-dict issue {j+1} in chunk {i+1}")
                        continue
                    
                    # Ensure issue has all required fields
                    issue_copy = issue.copy()
                    
                    # Add metadata from chunk if missing
                    if "section" not in issue_copy:
                        issue_copy["section"] = chunk_result.get("position", f"Chunk {i+1}")
                    
                    if "text" not in issue_copy:
                        issue_copy["text"] = chunk_result.get("text", "")
                    
                    if "should_analyze" not in issue_copy:
                        issue_copy["should_analyze"] = chunk_result.get("should_analyze", True)
                    
                    # Validate required fields
                    if not issue_copy.get("issue", "").strip():
                        if self.debug:
                            print(f"Warning: Skipping empty issue in chunk {i+1}")
                        continue
                    
                    all_findings.append(issue_copy)
                    
            except Exception as e:
                if self.debug:
                    print(f"Error processing chunk {i+1}: {e}")
                # Don't fail completely, but log the issue
                continue
        
        # Store original counts
        self.original_issues_count = len(all_findings)
        
        if self.debug:
            print(f"Extracted {self.original_issues_count} total findings")
        
        # Deduplicate findings
        try:
            deduplicated_findings = self.deduplicate_issues(all_findings)
        except Exception as e:
            raise RuntimeError(f"Failed to deduplicate issues: {e}")
        
        # Store deduplicated counts
        self.deduplicated_issues_count = len(deduplicated_findings)
        
        if self.debug:
            print(f"Processing complete:")
            print(f"  - Raw findings: {self.original_issues_count}")
            print(f"  - After deduplication: {self.deduplicated_issues_count}")
        
        return (deduplicated_findings,)  # Return tuple with single element for backward compatibility
    
    def _normalize_for_deduplication(self, text: str) -> str:
        """Normalize text for better deduplication with validation."""
        if not text:
            return ""
        
        if not isinstance(text, str):
            text = str(text)
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove stopwords
        stopwords = ["the", "a", "an", "is", "are", "will", "shall", "should", "may", 
                   "might", "can", "could", "this", "that", "these", "those", "with", 
                   "from", "have", "does", "would", "about", "which"]
        
        try:
            for word in stopwords:
                text = re.sub(r'\b' + re.escape(word) + r'\b', '', text)
        except Exception as e:
            if self.debug:
                print(f"Warning: Error removing stopwords: {e}")
            # Continue with original text
        
        try:
            # Remove punctuation and extra whitespace
            text = re.sub(r'[^\w\s]', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
        except Exception as e:
            if self.debug:
                print(f"Warning: Error normalizing text: {e}")
            # Return whatever we have
        
        return text
    
    def deduplicate_issues(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate issues using semantic grouping with proper validation."""
        if not findings:
            return []
        
        if not isinstance(findings, list):
            raise ValueError("findings must be a list")
        
        # Group by regulation and normalized issue description
        unique_issues = {}
        processed_count = 0
        
        for finding in findings:
            try:
                # Skip findings without issues
                issue_text = finding.get("issue", "")
                if not issue_text or not issue_text.strip():
                    continue
                
                # Get key components with validation
                regulation = finding.get("regulation", "Unknown regulation")
                section = finding.get("section", "Unknown")
                should_analyze = finding.get("should_analyze", True)
                
                # Ensure components are strings
                if not isinstance(regulation, str):
                    regulation = str(regulation)
                if not isinstance(section, str):
                    section = str(section)
                
                # Normalize the issue text for better deduplication
                normalized_issue = self._normalize_for_deduplication(issue_text)
                
                # Also normalize the regulation reference
                normalized_regulation = self._normalize_regulation(regulation)
                
                # Create a key combining normalized regulation and issue
                key = f"{normalized_regulation}:{normalized_issue[:40]}"
                
                # If this is a new unique issue, add it
                if key not in unique_issues:
                    unique_issues[key] = {
                        "issue": issue_text,
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
                        # Update with the analyzed version
                        existing["should_analyze"] = True
                        existing["explanation"] = finding.get("explanation", "")
                        if "citation" in finding and finding["citation"] != "No specific quote provided.":
                            existing["citation"] = finding["citation"]
                    
                    # Combine sections with validation
                    try:
                        existing_section = existing["section"]
                        
                        if isinstance(existing_section, list):
                            # Already a list, add new section if not present
                            if isinstance(section, list):
                                for s in section:
                                    if str(s) not in [str(es) for es in existing_section]:
                                        existing_section.append(s)
                            elif str(section) not in [str(es) for es in existing_section]:
                                existing_section.append(section)
                        else:
                            # Convert to list if adding a different section
                            if isinstance(section, list):
                                existing["section"] = [existing_section] + section
                            elif str(section) != str(existing_section):
                                existing["section"] = [existing_section, section]
                    except Exception as e:
                        if self.debug:
                            print(f"Warning: Error combining sections: {e}")
                        # Keep existing section
                
                processed_count += 1
                
            except Exception as e:
                if self.debug:
                    print(f"Warning: Error processing finding for deduplication: {e}")
                continue
        
        if self.debug:
            print(f"Deduplication: processed {processed_count} findings into {len(unique_issues)} unique issues")
        
        # Convert dictionary to list and sort by regulation (alphabetically)
        try:
            result = list(unique_issues.values())
            result.sort(key=lambda x: x.get("regulation", ""))
        except Exception as e:
            if self.debug:
                print(f"Warning: Error sorting deduplicated results: {e}")
            result = list(unique_issues.values())
        
        return result
    
    def _normalize_regulation(self, regulation: str) -> str:
        """Normalize regulation references for better deduplication with validation."""
        if not regulation:
            return "unknown"
        
        if not isinstance(regulation, str):
            regulation = str(regulation)
            
        try:
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
                section_type_match = re.search(r'(article|regulation|section|rule)', normalized, re.I)
                if section_type_match:
                    section_type = section_type_match.group(1).lower()
                    section_num = match.group(1)
                    return f"{section_type}{section_num}"
                    
        except Exception as e:
            if self.debug:
                print(f"Warning: Error normalizing regulation '{regulation}': {e}")
            # Return a safe fallback
            return re.sub(r'[^\w]', '', regulation.lower())[:20]
        
        return normalized[:50]  # Limit length
    
    def export_report(self, export_path, analyzed_file, regulation_framework, findings, 
                      document_metadata, chunk_results):
        """Export a detailed report of compliance issues with proper error handling."""
        
        # Validate inputs
        if not export_path:
            raise ValueError("export_path cannot be empty")
        
        if not analyzed_file:
            raise ValueError("analyzed_file cannot be empty")
        
        if not regulation_framework:
            raise ValueError("regulation_framework cannot be empty")
        
        if not isinstance(findings, list):
            raise ValueError("findings must be a list")
        
        if not isinstance(document_metadata, dict):
            raise ValueError("document_metadata must be a dictionary")
        
        if not isinstance(chunk_results, list):
            raise ValueError("chunk_results must be a list")
        
        # Validate export path
        export_path = Path(export_path)
        try:
            # Ensure parent directory exists
            export_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"Cannot create export directory {export_path.parent}: {e}")
        
        try:
            # Use string buffer for more efficient string operations
            report_lines = []
            
            # Write report header
            report_lines.append("=" * 80)
            report_lines.append(f"{regulation_framework.upper()} COMPLIANCE ANALYSIS REPORT")
            report_lines.append("=" * 80 + "\n")
            
            # Document information with validation
            try:
                analyzed_file_name = os.path.basename(analyzed_file) if analyzed_file else "Unknown"
                doc_type = document_metadata.get('document_type', 'Unknown')
                analysis_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                report_lines.append(f"Document: {analyzed_file_name}")
                report_lines.append(f"Document Type: {doc_type}")
                report_lines.append(f"Regulation: {regulation_framework}")
                report_lines.append(f"Analysis Date: {analysis_date}\n")
            except Exception as e:
                if self.debug:
                    print(f"Warning: Error formatting document info: {e}")
                report_lines.append("Document information: Error formatting details\n")
            
            # Data context with validation
            try:
                data_mentions = document_metadata.get('potential_data_mentions', [])
                compliance_indicators = document_metadata.get('compliance_indicators', [])
                
                if not isinstance(data_mentions, list):
                    data_mentions = []
                if not isinstance(compliance_indicators, list):
                    compliance_indicators = []
                
                data_mentions_str = ', '.join(data_mentions) if data_mentions else 'None detected'
                compliance_indicators_str = ', '.join(compliance_indicators) if compliance_indicators else 'None detected'
                
                report_lines.append("POTENTIAL DATA CONTEXT:")
                report_lines.append(f"Data mentions: {data_mentions_str}")
                report_lines.append(f"Compliance indicators: {compliance_indicators_str}\n")
            except Exception as e:
                if self.debug:
                    print(f"Warning: Error formatting data context: {e}")
                report_lines.append("POTENTIAL DATA CONTEXT: Error formatting data context\n")
            
            # Count total issues
            total_issues = len(findings)
            
            report_lines.append(f"Total Issues Found: {total_issues}")
            
            # Add analysis method to report
            try:
                has_progressive = any("should_analyze" in chunk for chunk in chunk_results)
                if has_progressive:
                    report_lines.append("Analysis Method: Progressive (focused on relevant sections)")
                    
                    # Count issues by analysis type
                    analyzed_issues = sum(1 for f in findings if f.get("should_analyze", True))
                    skipped_issues = total_issues - analyzed_issues
                    
                    report_lines.append(f"- From analyzed sections: {analyzed_issues}")
                    report_lines.append(f"- From skipped sections: {skipped_issues}")
                else:
                    report_lines.append("Analysis Method: Standard (all sections analyzed)")
            except Exception as e:
                if self.debug:
                    print(f"Warning: Error determining analysis method: {e}")
                report_lines.append("Analysis Method: Unknown")
            
            # Add processing information
            report_lines.append(f"\nPROCESSING SUMMARY:")
            report_lines.append(f"- Original issues: {self.original_issues_count} → Final: {self.deduplicated_issues_count}")
            
            if total_issues > 0:
                try:
                    # Group issues by regulation for summary
                    report_lines.append("\nSUMMARY OF COMPLIANCE CONCERNS:")
                    report_lines.append("-" * 80 + "\n")
                    
                    # Group findings by regulation
                    by_regulation = {}
                    for finding in findings:
                        regulation = finding.get("regulation", "Unknown regulation")
                        if not isinstance(regulation, str):
                            regulation = str(regulation)
                        
                        if regulation not in by_regulation:
                            by_regulation[regulation] = []
                        by_regulation[regulation].append(finding)
                    
                    # Display regulations with their issues (sorted alphabetically)
                    for regulation in sorted(by_regulation.keys()):
                        reg_issues = by_regulation[regulation]
                        report_lines.append(f"{regulation}:")
                        
                        # Group sections for this regulation
                        section_mentions = {}
                        for issue in reg_issues:
                            issue_desc = issue.get("issue", "Unknown issue")
                            section = issue.get("section", "Unknown section")
                            should_analyze = issue.get("should_analyze", True)
                            
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
                            else:
                                section = str(section)
                            
                            if issue_desc not in section_mentions:
                                section_mentions[issue_desc] = {
                                    "sections": [section] if isinstance(section, str) else section,
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
                            should_analyze = details.get("should_analyze", True)
                            
                            # Format analysis indicator
                            display_analysis = "" if should_analyze else " (SKIPPED)"
                            
                            # Ensure all sections are strings
                            sections = [str(s) for s in sections]
                            
                            # Format sections nicely
                            if len(sections) <= 2:
                                section_text = ", ".join(sections)
                            else:
                                section_text = f"{sections[0]}, {sections[1]} and {len(sections)-2} more"
                            
                            report_lines.append(f"  - {issue_desc}{display_analysis} (in {section_text})")
                        
                        report_lines.append("")
                    
                    report_lines.append("-" * 80 + "\n")
                    
                except Exception as e:
                    if self.debug:
                        print(f"Warning: Error generating issues summary: {e}")
                    report_lines.append("Error generating issues summary\n")
            
            # Add detailed section-by-section analysis
            try:
                report_lines.append("DETAILED ANALYSIS BY SECTION:")
                report_lines.append("=" * 80 + "\n")
                
                # Process all chunks in order, with or without issues
                for chunk_index, chunk in enumerate(chunk_results):
                    section = chunk.get("position", f"Section {chunk_index + 1}")
                    text = chunk.get("text", "Text not available")
                    issues = chunk.get("issues", [])
                    should_analyze = chunk.get("should_analyze", True)
                    
                    # Add analysis status to section title
                    analysis_display = "" if should_analyze else " [SKIPPED]"
                    
                    report_lines.append(f"SECTION #{chunk_index + 1} - {section}{analysis_display}")
                    report_lines.append("-" * 80 + "\n")
                    
                    # Display section text (truncated for readability)
                    try:
                        report_lines.append("DOCUMENT TEXT:")
                        display_text = text[:2000] + "..." if len(text) > 2000 else text
                        report_lines.append(f"{display_text}\n")
                    except Exception as e:
                        report_lines.append("DOCUMENT TEXT: Error displaying text\n")
                    
                    # Display issues if any
                    if issues:
                        report_lines.append("COMPLIANCE ISSUES:\n")
                        
                        for i, finding in enumerate(issues):
                            try:
                                issue = finding.get("issue", "Unknown issue")
                                regulation = finding.get("regulation", "Unknown regulation")
                                citation = finding.get("citation", "")
                                
                                # Clean up any asterisks from issue descriptions
                                issue = re.sub(r'\*+', '', issue)
                                
                                report_lines.append(f"Issue {i+1}: {issue}")
                                report_lines.append(f"Regulation: {regulation}")
                                
                                if citation:
                                    # Clean up citation formatting
                                    if citation.strip() in ["None", ""]:
                                        citation = "No specific quote provided."
                                    elif not citation.startswith('"') and not citation.endswith('"'):
                                        citation = f'"{citation}"'
                                    report_lines.append(f"Citation: {citation}")
                                
                                if i < len(issues) - 1:
                                    report_lines.append("-" * 40 + "\n")
                                    
                            except Exception as e:
                                if self.debug:
                                    print(f"Warning: Error formatting issue {i+1}: {e}")
                                report_lines.append(f"Issue {i+1}: Error formatting issue")
                    else:
                        if not should_analyze:
                            report_lines.append("NO COMPLIANCE ISSUES DETECTED IN THIS SKIPPED SECTION")
                        else:
                            report_lines.append("NO COMPLIANCE ISSUES DETECTED IN THIS SECTION")
                    
                    report_lines.append("")
                    report_lines.append("=" * 80 + "\n")
                    
            except Exception as e:
                if self.debug:
                    print(f"Warning: Error generating detailed analysis: {e}")
                report_lines.append("Error generating detailed section analysis\n")
            
            # Write the entire report to the file
            try:
                with open(export_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(report_lines))
            except Exception as e:
                raise RuntimeError(f"Failed to write report to {export_path}: {e}")
            
            if self.debug:
                print(f"Report exported successfully to {export_path}")
            
            return True
            
        except Exception as e:
            if self.debug:
                print(f"Error exporting report: {e}")
                import traceback
                traceback.print_exc()
            raise RuntimeError(f"Failed to export report: {e}")