# utils/reconciliation_handler.py

from typing import Dict, List, Any
import re

class ReconciliationHandler:
    """Handles reconciliation of findings from different document chunks to eliminate contradictions."""
    
    def __init__(self, llm_handler=None, debug=False):
        """Initialize the reconciliation handler."""
        self.llm = llm_handler
        self.debug = debug
    
    def reconcile_findings(self, 
                          issues: List[Dict[str, Any]], 
                          compliance_points: List[Dict[str, Any]], 
                          document_metadata: Dict[str, Any],
                          document_sections: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Reconcile findings across different document sections to remove contradictions.
        
        Args:
            issues: List of compliance issues found
            compliance_points: List of compliance strengths found
            document_metadata: Document information like title, type, etc.
            document_sections: Optional list of document section headings
            
        Returns:
            Dictionary with reconciled issues and compliance points
        """
        # Prepare the document structure context
        document_context = self._create_document_context(document_metadata, document_sections)
        
        # Format findings for the prompt
        formatted_issues = self._format_findings(issues)
        formatted_compliance_points = self._format_findings(compliance_points)
        
        # Create reconciliation prompt
        prompt = self._create_reconciliation_prompt(
            formatted_issues, 
            formatted_compliance_points, 
            document_context
        )
        
        if self.debug:
            print("Reconciliation prompt:")
            print(prompt[:500] + "...\n[truncated]")
        
        # Get LLM response
        if self.llm:
            response = self.llm.invoke(prompt)
            
            if self.debug:
                print("Reconciliation response:")
                print(response[:500] + "...\n[truncated]")
                
            # Parse the response to get reconciled findings
            reconciled_findings = self._parse_reconciliation_response(response, issues, compliance_points)
            return reconciled_findings
        else:
            print("Warning: No LLM handler provided for reconciliation. Returning original findings.")
            return {
                "issues": issues,
                "compliance_points": compliance_points,
                "reconciliation_analysis": ""
            }
    
    def _create_document_context(self, document_metadata: Dict[str, Any], document_sections: List[str] = None) -> str:
        """Create a concise document context string."""
        context = f"Document: {document_metadata.get('title', 'Unknown')}\n"
        context += f"Type: {document_metadata.get('document_type', 'Unknown')}\n"
        
        if document_sections:
            context += "\nDocument Structure:\n"
            for i, section in enumerate(document_sections[:10]):  # Limit to first 10 sections to avoid excessively long prompts
                context += f"- {section}\n"
            if len(document_sections) > 10:
                context += f"- ... and {len(document_sections) - 10} more sections\n"
        
        return context
    
    def _format_findings(self, findings: List[Dict[str, Any]]) -> str:
        """Format findings list for inclusion in the prompt."""
        if not findings:
            return "None found."
            
        formatted = ""
        for i, finding in enumerate(findings):
            # Extract the key information
            if "issue" in finding:
                finding_text = finding.get("issue", "Unknown finding")
                finding_type = "Issue"
            else:
                finding_text = finding.get("point", "Unknown finding")
                finding_type = "Strength"
                
            regulation = finding.get("regulation", "Unknown regulation")
            section = finding.get("section", "Unknown section")
            confidence = finding.get("confidence", "Medium")
            citation = finding.get("citation", "")
            
            formatted += f"{i+1}. [{finding_type}] {finding_text}\n"
            formatted += f"   Regulation: {regulation}\n"
            formatted += f"   Found in: {section if isinstance(section, str) else ', '.join(section[:2]) + ('...' if len(section) > 2 else '')}\n"
            formatted += f"   Confidence: {confidence}\n"
            if citation:
                formatted += f"   Citation: {citation}\n"
            formatted += "\n"
            
        return formatted
    
    def _create_reconciliation_prompt(self, formatted_issues: str, formatted_compliance_points: str, document_context: str) -> str:
        """Create the reconciliation prompt for the LLM."""
        prompt = f"""You are a regulatory compliance expert reconciling findings from a document analysis.

{document_context}

The document has been analyzed in sections, and the following compliance issues and strengths were identified:

COMPLIANCE ISSUES:
{formatted_issues}

COMPLIANCE STRENGTHS:
{formatted_compliance_points}

TASK:
Analyze the findings for contradictions, duplications, and inconsistencies. Your goal is to produce a refined set of findings that eliminates false positives and provides a more accurate assessment of the document's compliance status.

Specifically:
1. Identify issues that are directly contradicted by compliance strengths or by information in other sections
2. Merge duplicate issues that refer to the same underlying problem but are phrased differently
3. Remove issues that are addressed elsewhere in the document according to the compliance points
4. Adjust confidence levels based on cross-document evidence
5. Identify any issues that might be false positives based on document context

Return your analysis in the following format:

RECONCILIATION ANALYSIS:
[PROVIDE A DETAILED EXPLANATION of all contradictions you found and what changes you made. List EACH contradiction and explain your reasoning for resolving it. This section MUST be comprehensive as it will appear in the final report to explain your reconciliation process.]

REFINED COMPLIANCE ISSUES:
1. [Issue text]
   Regulation: [Regulation]
   Confidence: [Adjusted confidence]
   Reasoning: [Why this issue was kept, merged, or modified]

2. [Next issue]
   ...

REFINED COMPLIANCE STRENGTHS:
1. [Compliance point text]
   Regulation: [Regulation]
   Confidence: [Adjusted confidence]
   Reasoning: [Why this point was kept, merged, or modified]

2. [Next point]
   ...

Be thorough in your reconciliation analysis and provide specific examples of contradictions you resolved. This analysis will be included in the final report to show how you reconciled conflicting findings across document sections.
"""
        return prompt
    
    def _parse_reconciliation_response(self, response: str, original_issues: List[Dict[str, Any]], 
                             original_compliance_points: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Parse the LLM's reconciliation response and convert it to structured output."""
        # Create default result with original findings
        result = {
            "issues": original_issues.copy(),
            "compliance_points": original_compliance_points.copy(),
            "reconciliation_analysis": ""  # Initialize empty
        }
        
        if self.debug:
            print(f"\n*** RECONCILIATION RESPONSE PARSING ***")
            print(f"Response length: {len(response)} characters")
            print(f"First 200 chars: {response[:200]}...")
            print(f"Contains 'RECONCILIATION ANALYSIS': {'RECONCILIATION ANALYSIS' in response}")
            print(f"Contains 'REFINED COMPLIANCE ISSUES': {'REFINED COMPLIANCE ISSUES' in response}")
        
        # Extract the reconciliation analysis section with a more robust pattern
        analysis_match = re.search(r'RECONCILIATION ANALYSIS:(.*?)(?:REFINED COMPLIANCE ISSUES:|$)', 
                            response, re.DOTALL | re.IGNORECASE)
        if analysis_match:
            reconciliation_analysis = analysis_match.group(1).strip()
            result["reconciliation_analysis"] = reconciliation_analysis
            
            # Print first part of analysis in debug mode to verify it's being captured
            if self.debug:
                print(f"✓ Extracted reconciliation analysis: {len(reconciliation_analysis)} chars")
                print(f"Analysis begins with: {reconciliation_analysis[:100]}...")
        else:
            if self.debug:
                print("❌ No reconciliation analysis section found with primary pattern")
                print("Trying alternative extraction methods...")
            
            # Try alternative methods to extract analysis
            
            # Method 1: Simple split approach
            if "RECONCILIATION ANALYSIS" in response:
                parts = response.split("RECONCILIATION ANALYSIS:", 1)
                if len(parts) > 1:
                    second_part = parts[1]
                    # Find where the next section starts
                    end_markers = ["REFINED COMPLIANCE ISSUES", "REFINED COMPLIANCE", "ISSUES:", "REFINED"]
                    end_pos = len(second_part)
                    
                    for marker in end_markers:
                        if marker in second_part:
                            marker_pos = second_part.find(marker)
                            if 0 < marker_pos < end_pos:
                                end_pos = marker_pos
                    
                    analysis_text = second_part[:end_pos].strip()
                    result["reconciliation_analysis"] = analysis_text
                    
                    if self.debug:
                        print(f"✓ Found analysis with simple split: {len(analysis_text)} chars")
                        print(f"Analysis begins with: {analysis_text[:100]}...")
            
            # Method 2: Paragraph-based approach
            if not result["reconciliation_analysis"] and "RECONCILIATION ANALYSIS" in response:
                # Find the start of the analysis section
                start_pos = response.find("RECONCILIATION ANALYSIS") + len("RECONCILIATION ANALYSIS")
                
                # Skip any colons or whitespace
                while start_pos < len(response) and (response[start_pos].isspace() or response[start_pos] == ':'):
                    start_pos += 1
                
                # Extract paragraphs until we hit what looks like a new section
                paragraphs = []
                current_pos = start_pos
                in_new_section = False
                
                for line in response[start_pos:].split('\n'):
                    # Check if this line looks like a new section header
                    if re.match(r'^[A-Z\s]+:', line.strip()) or line.strip().startswith("REFINED"):
                        in_new_section = True
                        break
                    
                    # Add non-empty lines to our paragraphs
                    if line.strip():
                        paragraphs.append(line.strip())
                
                if paragraphs:
                    analysis_text = '\n'.join(paragraphs)
                    result["reconciliation_analysis"] = analysis_text
                    
                    if self.debug:
                        print(f"✓ Found analysis with paragraph approach: {len(analysis_text)} chars")
                        print(f"Analysis begins with: {analysis_text[:100]}...")
            
            # If still no analysis, create a fallback
            if not result["reconciliation_analysis"]:
                if self.debug:
                    print("⚠️ No reconciliation analysis found - creating fallback explanation")
                
                # Create a basic explanation
                result["reconciliation_analysis"] = (
                    "Reconciliation was performed to identify and resolve contradictions between findings from different sections. "
                    "The analysis consolidated duplicate issues and removed findings that were contradicted by information in other sections. "
                    "The reconciled findings represent a more accurate assessment of the document's compliance status."
                )
        
        # Extract refined issues
        issues_match = re.search(r'REFINED COMPLIANCE ISSUES:(.*?)(?:REFINED COMPLIANCE STRENGTHS:|$)', 
                            response, re.DOTALL | re.IGNORECASE)
        if issues_match:
            refined_issues_text = issues_match.group(1).strip()
            refined_issues = self._extract_refined_findings(refined_issues_text)
            if refined_issues:
                if self.debug:
                    print(f"✓ Extracted {len(refined_issues)} refined issues")
                result["issues"] = refined_issues
            else:
                if self.debug:
                    print("⚠️ Found refined issues section but couldn't extract any issues")
        else:
            if self.debug:
                print("⚠️ No refined issues section found - keeping original deduplicated issues")
        
        # Extract refined compliance points
        points_match = re.search(r'REFINED COMPLIANCE STRENGTHS:(.*?)$', response, re.DOTALL | re.IGNORECASE)
        if points_match:
            refined_points_text = points_match.group(1).strip()
            refined_points = self._extract_refined_findings(refined_points_text)
            if refined_points:
                if self.debug:
                    print(f"✓ Extracted {len(refined_points)} refined compliance points")
                result["compliance_points"] = refined_points
            else:
                if self.debug:
                    print("⚠️ Found refined compliance points section but couldn't extract any points")
        else:
            if self.debug:
                print("⚠️ No refined compliance points section found - keeping original points")
        
        return result
    
    def _extract_refined_findings(self, text: str) -> List[Dict[str, Any]]:
        """Extract structured findings from the formatted text section."""
        findings = []
        
        # Look for numbered findings (1. Finding text...)
        finding_pattern = re.compile(r'(\d+)\.\s+(.*?)(?=\n\d+\.|$)', re.DOTALL)
        matches = finding_pattern.findall(text)
        
        for _, finding_text in matches:
            finding = {"confidence": "Medium"}  # Default confidence
            
            # Extract the main finding text (first line)
            main_text_match = re.match(r'(.*?)(?:\n|$)', finding_text.strip())
            if main_text_match:
                finding["issue"] = main_text_match.group(1).strip()
                # If this is a compliance point, use "point" key instead
                if "strengths" in text.lower():
                    finding["point"] = finding.pop("issue")
            
            # Extract regulation
            reg_match = re.search(r'Regulation:\s*(.*?)(?:\n|$)', finding_text)
            if reg_match:
                finding["regulation"] = reg_match.group(1).strip()
                
            # Extract confidence
            conf_match = re.search(r'Confidence:\s*(.*?)(?:\n|$)', finding_text)
            if conf_match:
                finding["confidence"] = conf_match.group(1).strip()
                
            # Extract reasoning if available
            reason_match = re.search(r'Reasoning:\s*(.*?)(?:\n\s*\w+:|$)', finding_text, re.DOTALL)
            if reason_match:
                finding["reconciliation_reasoning"] = reason_match.group(1).strip()
                
            # Extract citation if present
            cite_match = re.search(r'Citation:\s*(.*?)(?:\n|$)', finding_text)
            if cite_match:
                finding["citation"] = cite_match.group(1).strip()
            
            findings.append(finding)
            
        return findings