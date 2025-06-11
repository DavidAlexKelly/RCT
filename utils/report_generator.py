# utils/report_generator.py

import os
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime
from utils.reconciliation_handler import ReconciliationHandler

class ReportGenerator:
    """Handles processing of analysis results and report generation."""
    
    def __init__(self, debug=False, llm_handler=None, show_detailed_reconciliation=True):
        """Initialize the report generator."""
        self.debug = debug
        self.llm_handler = llm_handler
        self.reconciliation_analysis = ""
        self.show_detailed_reconciliation = show_detailed_reconciliation
        # Track counts for reporting
        self.original_issues_count = 0
        self.deduplicated_issues_count = 0
        self.reconciled_issues_count = 0
        self.original_points_count = 0 
        self.deduplicated_points_count = 0
        self.reconciled_points_count = 0
    
    def process_results(self, chunk_results: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Process analysis results to extract and deduplicate findings,
        with additional reconciliation to handle cross-section contradictions.
        
        Args:
            chunk_results: List of chunk analysis results
            
        Returns:
            Tuple of (deduplicated_findings, deduplicated_compliance_points)
        """
        # Extract all issues and compliance points
        all_findings = []
        all_compliance_points = []
        
        for chunk_result in chunk_results:
            # Process issues
            for issue in chunk_result.get("issues", []):
                # Ensure issue has all required fields
                issue_copy = issue.copy()
                if "section" not in issue_copy:
                    issue_copy["section"] = chunk_result.get("position", "Unknown")
                if "text" not in issue_copy:
                    issue_copy["text"] = chunk_result.get("text", "")
                if "risk_level" not in issue_copy:
                    issue_copy["risk_level"] = chunk_result.get("risk_level", "unknown")
                
                all_findings.append(issue_copy)
            
            # Process compliance points
            for point in chunk_result.get("compliance_points", []):
                # Ensure point has all required fields
                point_copy = point.copy()
                if "section" not in point_copy:
                    point_copy["section"] = chunk_result.get("position", "Unknown")
                if "text" not in point_copy:
                    point_copy["text"] = chunk_result.get("text", "")
                if "risk_level" not in point_copy:
                    point_copy["risk_level"] = chunk_result.get("risk_level", "unknown")
                
                all_compliance_points.append(point_copy)
        
        # Store original counts
        self.original_issues_count = len(all_findings)
        self.original_points_count = len(all_compliance_points)
        
        # Deduplicate findings and compliance points
        deduplicated_findings = self.deduplicate_issues(all_findings)
        deduplicated_compliance_points = self.deduplicate_compliance_points(all_compliance_points)
        
        # Store deduplicated counts
        self.deduplicated_issues_count = len(deduplicated_findings)
        self.deduplicated_points_count = len(deduplicated_compliance_points)
        
        if self.debug:
            print(f"\nInitial processing complete:")
            print(f"  - Raw findings: {self.original_issues_count}")
            print(f"  - After deduplication: {self.deduplicated_issues_count}")
            print(f"  - Raw compliance points: {self.original_points_count}")
            print(f"  - After deduplication: {self.deduplicated_points_count}")
        
        # Extract document metadata from the first chunk or use defaults
        document_metadata = {
            "document_type": chunk_results[0].get("document_type", "unknown") if chunk_results else "unknown",
            "title": "Document Analysis",  # This could be improved to extract a better title
        }
        
        # Extract section headings for document context
        section_headings = [chunk.get("position", "Unknown section") for chunk in chunk_results]
        
        # Perform reconciliation of findings if LLM handler is available
        if self.llm_handler:
            try:
                reconciliation_handler = ReconciliationHandler(self.llm_handler, self.debug)
                reconciled_results = reconciliation_handler.reconcile_findings(
                    deduplicated_findings,
                    deduplicated_compliance_points,
                    document_metadata,
                    section_headings
                )
                
                # Replace with reconciled findings
                final_findings = reconciled_results.get("issues", deduplicated_findings)
                final_compliance_points = reconciled_results.get("compliance_points", deduplicated_compliance_points)
                
                # Store reconciliation analysis for the report
                self.reconciliation_analysis = reconciled_results.get("reconciliation_analysis", "")
                
                # Store reconciled counts
                self.reconciled_issues_count = len(final_findings)
                self.reconciled_points_count = len(final_compliance_points)
                
                if self.debug:
                    print(f"\nReconciliation complete:")
                    print(f"  - After reconciliation: {self.reconciled_issues_count} issues, {self.reconciled_points_count} compliance points")
                    if self.reconciliation_analysis:
                        print(f"  - Reconciliation analysis: {self.reconciliation_analysis[:100]}...")
                
                return final_findings, final_compliance_points
            
            except Exception as e:
                if self.debug:
                    print(f"Error during reconciliation: {e}")
                    import traceback
                    traceback.print_exc()
                print("Warning: Reconciliation failed. Using deduplicated findings without reconciliation.")
                # Set reconciled counts to match deduplicated if reconciliation fails
                self.reconciled_issues_count = self.deduplicated_issues_count
                self.reconciled_points_count = self.deduplicated_points_count
        else:
            if self.debug:
                print("\nSkipping reconciliation step - no LLM handler provided")
            # Set reconciled counts to match deduplicated if no reconciliation
            self.reconciled_issues_count = self.deduplicated_issues_count
            self.reconciled_points_count = self.deduplicated_points_count
        
        return deduplicated_findings, deduplicated_compliance_points
    
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
            risk_level = finding.get("risk_level", "unknown")
            
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
                    "risk_level": risk_level
                }
                if "citation" in finding:
                    unique_issues[key]["citation"] = finding["citation"]
            else:
                # Update existing entry
                existing = unique_issues[key]
                
                # Give priority to high-risk findings
                risk_value = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
                if risk_value.get(risk_level, 0) > risk_value.get(existing.get("risk_level", "unknown"), 0):
                    # Update the risk level and take other fields from this higher-risk finding
                    existing["risk_level"] = risk_level
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
        
        # Convert dictionary to list and sort by risk level and confidence
        result = list(unique_issues.values())
        result.sort(key=lambda x: (
            -{"high": 3, "medium": 2, "low": 1, "unknown": 0}.get(x.get("risk_level", "unknown"), 0),
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
    
    def deduplicate_compliance_points(self, compliance_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate compliance points using semantic grouping."""
        if not compliance_points:
            return []
        
        # Group by regulation and normalized point description
        unique_points = {}
        
        for point in compliance_points:
            # Skip points without descriptions
            if not point.get("point"):
                continue
                
            # Get key components
            regulation = point.get("regulation", "Unknown regulation")
            point_text = point.get("point", "")
            section = point.get("section", "Unknown")
            risk_level = point.get("risk_level", "unknown")
            
            # Normalize the point text to catch similar points
            normalized_point = self._normalize_for_deduplication(point_text)
            
            # Also normalize the regulation reference
            normalized_regulation = self._normalize_regulation(regulation)
            
            # Create a key combining regulation and point
            key = f"{normalized_regulation}:{normalized_point[:40]}"
            
            # If this is a new unique point, add it
            if key not in unique_points:
                unique_points[key] = {
                    "point": point.get("point", "Unknown point"),
                    "regulation": regulation,
                    "confidence": point.get("confidence", "Medium"),
                    "explanation": point.get("explanation", ""),
                    "section": section,
                    "text": point.get("text", ""),
                    "risk_level": risk_level
                }
                if "citation" in point:
                    unique_points[key]["citation"] = point["citation"]
            else:
                # Update existing entry
                existing = unique_points[key]
                
                # Give priority to high-risk findings
                risk_value = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
                if risk_value.get(risk_level, 0) > risk_value.get(existing.get("risk_level", "unknown"), 0):
                    # Update the risk level and take other fields from this higher-risk finding
                    existing["risk_level"] = risk_level
                    existing["explanation"] = point.get("explanation", "")
                    if "citation" in point and point["citation"] != "No specific quote provided.":
                        existing["citation"] = point["citation"]
                
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
                if confidence_value.get(point.get("confidence", "").upper(), 0) > confidence_value.get(existing["confidence"].upper(), 0):
                    existing["confidence"] = point.get("confidence", "Medium")
        
        # Convert dictionary to list and sort by risk level and confidence
        result = list(unique_points.values())
        result.sort(key=lambda x: (
            -{"high": 3, "medium": 2, "low": 1, "unknown": 0}.get(x.get("risk_level", "unknown"), 0),
            {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x.get("confidence", "").upper(), 3),
            x.get("regulation", "")
        ))
        
        return result
    
    def export_report(self, export_path, analyzed_file, regulation_framework, findings, 
                  compliance_points, document_metadata, chunk_results):
        """Export a detailed report of findings and compliance points."""
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
            
            # Count total issues and compliance points
            total_issues = len(findings)
            total_compliance_points = len(compliance_points)
            
            report_lines.append(f"Total Issues Found: {total_issues}")
            
            # Add analysis method to report
            has_progressive = any("risk_level" in chunk for chunk in chunk_results)
            if has_progressive:
                report_lines.append("Analysis Method: Progressive (focused on high-risk sections)")
                
                # Count issues by risk level
                high_risk_issues = sum(1 for f in findings if f.get("risk_level") == "high")
                medium_risk_issues = sum(1 for f in findings if f.get("risk_level") == "medium")
                low_risk_issues = sum(1 for f in findings if f.get("risk_level") == "low")
                
                report_lines.append(f"- High-Risk Issues: {high_risk_issues}")
                report_lines.append(f"- Medium-Risk Issues: {medium_risk_issues}")
                report_lines.append(f"- Low-Risk Issues: {low_risk_issues}")
            
            # Add reconciliation information
            if hasattr(self, 'reconciliation_analysis') and self.reconciliation_analysis and self.reconciliation_analysis.strip():
                report_lines.append("\nANALYSIS RECONCILIATION: Performed")
                report_lines.append(f"- Original issues: {self.original_issues_count} → Deduplicated: {self.deduplicated_issues_count} → Final: {self.reconciled_issues_count}")
                report_lines.append(f"- Original compliance points: {self.original_points_count} → Deduplicated: {self.deduplicated_points_count} → Final: {self.reconciled_points_count}")
                report_lines.append("- See reconciliation analysis section for details on changes made")
            
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
                        risk_level = issue.get("risk_level", "unknown")
                        
                        # Format risk level indicator
                        if risk_level in ["high", "medium", "low"]:
                            display_risk = f" ({risk_level.upper()} risk)"
                        else:
                            display_risk = ""
                        
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
                                "risk_level": risk_level
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
                        risk_level = details.get("risk_level", "unknown")
                        
                        # Format risk level indicator
                        if risk_level in ["high", "medium", "low"]:
                            display_risk = f" ({risk_level.upper()} risk)"
                        else:
                            display_risk = ""
                        
                        # Ensure all sections are strings
                        sections = [str(s) for s in sections]
                        
                        # Format sections nicely
                        if len(sections) <= 2:
                            section_text = ", ".join(sections)
                        else:
                            section_text = f"{sections[0]}, {sections[1]} and {len(sections)-2} more"
                        
                        report_lines.append(f"  - {issue_desc}{display_risk} (in {section_text}, {confidence} confidence)")
                    
                    report_lines.append("")
                
                report_lines.append("-" * 80 + "\n")
            
            # If there are compliance points, include a summary
            if total_compliance_points > 0:
                # Count by confidence
                high_confidence = sum(1 for p in compliance_points if p.get("confidence", "").upper() == "HIGH")
                medium_confidence = sum(1 for p in compliance_points if p.get("confidence", "").upper() == "MEDIUM")
                low_confidence = sum(1 for p in compliance_points if p.get("confidence", "").upper() == "LOW")
                
                report_lines.append("CONFIDENCE BREAKDOWN OF COMPLIANCE POINTS:")
                report_lines.append(f"- High Confidence Points: {high_confidence}")
                report_lines.append(f"- Medium Confidence Points: {medium_confidence}")
                report_lines.append(f"- Low Confidence Points: {low_confidence}\n")
                
                # Group compliance points by regulation for summary
                report_lines.append("SUMMARY OF COMPLIANCE STRENGTHS:")
                report_lines.append("-" * 80 + "\n")
                
                # Group compliance points by regulation
                by_regulation = {}
                for point in compliance_points:
                    regulation = point.get("regulation", "Unknown regulation")
                    if regulation not in by_regulation:
                        by_regulation[regulation] = []
                    by_regulation[regulation].append(point)
                
                # Display regulations with their compliance points
                for regulation, reg_points in by_regulation.items():
                    report_lines.append(f"{regulation}:")
                    
                    # Group sections for this regulation
                    section_mentions = {}
                    for point in reg_points:
                        point_desc = point.get("point", "Unknown point")
                        section = point.get("section", "Unknown section")
                        confidence = point.get("confidence", "Medium")
                        risk_level = point.get("risk_level", "unknown")
                        
                        # Format risk level indicator
                        if risk_level in ["high", "medium", "low"]:
                            display_risk = f" ({risk_level.upper()} risk)"
                        else:
                            display_risk = ""
                        
                        # Normalize section to ensure it's a string
                        if isinstance(section, list):
                            # Flatten nested lists
                            flat_sections = []
                            for s in section:
                                if isinstance(s, list):
                                    flat_sections.extend(str(item) for item in s)
                                else:
                                    flat_sections.append(str(s))
                            section = flat_sections
                        
                        if point_desc not in section_mentions:
                            section_mentions[point_desc] = {
                                "sections": [section] if isinstance(section, str) else section,
                                "confidence": confidence,
                                "risk_level": risk_level
                            }
                        else:
                            if isinstance(section, str):
                                if section not in section_mentions[point_desc]["sections"]:
                                    section_mentions[point_desc]["sections"].append(section)
                            else:
                                # Add each item from the list
                                for s in section:
                                    if s not in section_mentions[point_desc]["sections"]:
                                        section_mentions[point_desc]["sections"].append(s)
                    
                    # Display compliance points with their sections
                    for point_desc, details in section_mentions.items():
                        sections = details["sections"]
                        confidence = details["confidence"]
                        risk_level = details.get("risk_level", "unknown")
                        
                        # Format risk level indicator
                        if risk_level in ["high", "medium", "low"]:
                            display_risk = f" ({risk_level.upper()} risk)"
                        else:
                            display_risk = ""
                        
                        # Ensure all sections are strings
                        sections = [str(s) for s in sections]
                        
                        # Format sections nicely
                        if len(sections) <= 2:
                            section_text = ", ".join(sections)
                        else:
                            section_text = f"{sections[0]}, {sections[1]} and {len(sections)-2} more"
                        
                        report_lines.append(f"  - {point_desc}{display_risk} (in {section_text}, {confidence} confidence)")
                    
                    report_lines.append("")
                
                report_lines.append("-" * 80 + "\n")
            
            # Add reconciliation analysis section if available and enabled
            if hasattr(self, 'reconciliation_analysis') and self.reconciliation_analysis and self.reconciliation_analysis.strip():
                report_lines.append("RECONCILIATION ANALYSIS:")
                report_lines.append("-" * 80 + "\n")
                report_lines.append(self.reconciliation_analysis)
                report_lines.append("\n" + "-" * 80 + "\n")
            
            # Add detailed section-by-section analysis
            report_lines.append("DETAILED ANALYSIS BY SECTION:")
            report_lines.append("=" * 80 + "\n")
            
            # Process all chunks in order, with or without issues
            for chunk_index, chunk in enumerate(chunk_results):
                section = chunk.get("position", "Unknown section")
                text = chunk.get("text", "Text not available")
                issues = chunk.get("issues", [])
                compliance_points = chunk.get("compliance_points", [])
                risk_level = chunk.get("risk_level", "unknown")
                
                # Add risk level to section title if available
                risk_display = ""
                if risk_level in ["high", "medium", "low"]:
                    risk_display = f" [RISK: {risk_level.upper()}]"
                
                report_lines.append(f"SECTION #{chunk_index + 1} - {section}{risk_display}")
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
                    if risk_level == "low":
                        report_lines.append("NO COMPLIANCE ISSUES DETECTED IN THIS LOW-RISK SECTION")
                    else:
                        report_lines.append("NO COMPLIANCE ISSUES DETECTED IN THIS SECTION")
                
                # Display compliance points if any
                if compliance_points:
                    if issues:
                        # Add a spacing if we already displayed issues
                        report_lines.append("\n")
                    
                    report_lines.append("COMPLIANCE POINTS:\n")
                    
                    for i, point in enumerate(compliance_points):
                        point_title = point.get("point", "Unknown point")
                        regulation = point.get("regulation", "Unknown regulation")
                        confidence = point.get("confidence", "Medium")
                        citation = point.get("citation", "")
                        
                        # Clean up any asterisks from point descriptions
                        point_title = re.sub(r'\*+', '', point_title)
                        
                        report_lines.append(f"Point {i+1}: {point_title}")
                        report_lines.append(f"Regulation: {regulation}")
                        report_lines.append(f"Confidence: {confidence}")
                        
                        if citation:
                            # Clean up citation formatting
                            if citation.strip() == "None" or citation.strip() == "":
                                citation = "No specific quote provided."
                            elif not citation.startswith('"') and not citation.endswith('"'):
                                citation = f'"{citation}"'
                            report_lines.append(f"Citation: {citation}")
                        
                        if i < len(compliance_points) - 1:
                            report_lines.append("-" * 40 + "\n")
                else:
                    if issues:
                        # Add a spacing if we already displayed issues
                        report_lines.append("\n")
                    if risk_level == "low":
                        report_lines.append("NO COMPLIANCE POINTS DETECTED IN THIS LOW-RISK SECTION")
                    else:
                        report_lines.append("NO COMPLIANCE POINTS DETECTED IN THIS SECTION")
                
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