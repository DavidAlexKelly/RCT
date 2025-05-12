#!/usr/bin/env python
import os
import json
import click
import re
from typing import List, Dict, Any
from datetime import datetime

# Import modules
from utils.document_processor import DocumentProcessor
from utils.embeddings import EmbeddingsHandler
from utils.llm_handler import LLMHandler

# Import configuration
from config import MODELS, DEFAULT_MODEL, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP

@click.group()
def cli():
    """Regulatory Compliance Analysis Tool"""
    pass

@cli.command()
@click.option("--file", required=True, help="Path to the document file")
@click.option("--regulation-framework", default="gdpr", help="Regulation framework to use (gdpr, hipaa, ccpa, etc.)")
@click.option("--chunk-size", default=DEFAULT_CHUNK_SIZE, help="Size of document chunks for analysis")
@click.option("--overlap", default=DEFAULT_CHUNK_OVERLAP, help="Overlap between document chunks")
@click.option("--export", help="Export detailed findings to a text file (provide file path)")
@click.option("--model", default=DEFAULT_MODEL, help=f"Model to use: {', '.join(MODELS.keys())}")
@click.option("--batch-size", default=None, type=int, help="Override the recommended batch size for the model")
@click.option("--debug", is_flag=True, default=False, help="Enable detailed debug output")
def analyze(file, regulation_framework, chunk_size, overlap, export, model, batch_size, debug):
    """Analyze a document for compliance issues using specified regulation framework."""
    # Get model description if available
    model_description = ""
    if model in MODELS:
        model_description = f" ({MODELS[model]['description']})"
    
    click.echo(f"Analyzing {file} for {regulation_framework} compliance...")
    click.echo(f"Using model: {model}{model_description}")
    
    # Validate regulation framework exists
    script_dir = os.path.dirname(os.path.abspath(__file__))
    regulation_dir = os.path.join(script_dir, "knowledge_base", regulation_framework)
    
    if not os.path.exists(regulation_dir):
        # Check if regulation index exists
        index_path = os.path.join(script_dir, "knowledge_base", "regulation_index.json")
        available_frameworks = []
        
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r') as f:
                    index_data = json.load(f)
                    available_frameworks = [fw["id"] for fw in index_data.get("frameworks", [])]
            except Exception as e:
                click.echo(f"Error reading regulation index: {e}")
        
        click.echo(f"Error: Regulation framework '{regulation_framework}' not found")
        if available_frameworks:
            click.echo("Available frameworks:")
            for fw_id in available_frameworks:
                click.echo(f"  - {fw_id}")
        return
    
    # Initialize components
    doc_processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=overlap)
    embeddings = EmbeddingsHandler()
    llm = LLMHandler(model_key=model, debug=debug)
    
    # Use recommended batch size from model config if not overridden
    if batch_size is None:
        batch_size = llm.get_batch_size()
        
    click.echo(f"Using batch size: {batch_size}")
    
    # Determine knowledge base paths
    articles_path = os.path.join(regulation_dir, "articles.txt")
    context_path = os.path.join(regulation_dir, "context.txt")
    patterns_path = os.path.join(regulation_dir, "common_patterns.txt")
    
    # Verify articles file exists
    if not os.path.exists(articles_path):
        click.echo(f"Error: Articles file not found at {articles_path}")
        click.echo(f"Please ensure the file exists and contains the necessary regulatory information.")
        return
    
    # Load articles (required)
    click.echo(f"Loading {regulation_framework} articles from {articles_path}...")
    embeddings.build_knowledge_base(articles_path)
    
    # Load context (optional)
    regulation_context = ""
    if os.path.exists(context_path):
        try:
            with open(context_path, 'r') as f:
                regulation_context = f.read()
                click.echo(f"Loaded {regulation_framework} context information")
        except Exception as e:
            click.echo(f"Warning: Could not load context file: {e}")
    
    # Load patterns (optional)
    regulation_patterns = ""
    if os.path.exists(patterns_path):
        try:
            with open(patterns_path, 'r') as f:
                regulation_patterns = f.read()
                click.echo(f"Loaded {regulation_framework} common patterns")
        except Exception as e:
            click.echo(f"Warning: Could not load patterns file: {e}")
    
    # Set regulation context in LLM handler
    llm.set_regulation_context(regulation_context, regulation_patterns, regulation_framework)
    
    # Process document
    click.echo("Processing document...")
    processed_document = doc_processor.process_document(file)
    document_chunks = processed_document["chunks"]
    document_metadata = processed_document["metadata"]
    
    click.echo(f"Extracted {len(document_chunks)} chunks from the document")
    
    if len(document_chunks) > 0:
        click.echo(f"Sample chunk (first 100 chars): {document_chunks[0]['text'][:100]}...")
        click.echo(f"Document type detected: {document_metadata.get('document_type', 'unknown')}")
        click.echo(f"Potential data mentions: {', '.join(document_metadata.get('potential_data_mentions', []))}")
    else:
        click.echo("WARNING: No text was extracted from the document!")
        return

    # Analyze each chunk for compliance issues
    click.echo("Starting analysis of individual chunks...")
    all_chunk_results = analyze_chunks(llm, embeddings, document_chunks, batch_size, debug)
    
    # Combine all issues
    all_findings = []
    for chunk_result in all_chunk_results:
        for issue in chunk_result.get("issues", []):
            # Ensure each issue has section information
            if "section" not in issue:
                issue["section"] = chunk_result.get("position", "Unknown")
            # Add text to the issue
            issue["text"] = chunk_result.get("text", "")
            all_findings.append(issue)
    
    # Basic deduplication of similar findings
    deduplicated_findings = deduplicate_issues(all_findings)
    
    # Output results
    output = {
        "document": os.path.basename(file),
        "document_type": document_metadata.get("document_type", "unknown"),
        "regulation_framework": regulation_framework,
        "findings": deduplicated_findings,
        "summary": f"The document contains {len(deduplicated_findings)} potential compliance issue(s) related to {regulation_framework}."
    }
    
    click.echo(json.dumps(output, indent=2))
    
    # Export detailed findings if requested
    if export:
        success = export_detailed_report(export, file, regulation_framework, deduplicated_findings, document_metadata, all_chunk_results)
        if success:
            click.echo(f"\nDetailed report exported to: {export}")
        else:
            click.echo(f"\nFailed to export report to: {export}")

@cli.command()
def models():
    """Display available models and their capabilities."""
    click.echo("Available models:")
    click.echo("-" * 80)
    for key, model in MODELS.items():
        click.echo(f"{key}: {model['name']}")
        click.echo(f"  Description: {model.get('description', 'No description')}")
        click.echo(f"  Batch Size: {model.get('batch_size', 1)}")
        click.echo(f"  Context Window: {model.get('context_window', 'Unknown')}")
        click.echo("-" * 80)
    click.echo(f"Default model: {DEFAULT_MODEL}")

@cli.command()
def frameworks():
    """Display available regulation frameworks."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(script_dir, "knowledge_base", "regulation_index.json")
    
    if not os.path.exists(index_path):
        click.echo("No regulation frameworks found. The index file is missing.")
        return
    
    try:
        with open(index_path, 'r') as f:
            index_data = json.load(f)
            frameworks = index_data.get("frameworks", [])
            
        if not frameworks:
            click.echo("No regulation frameworks are defined in the index.")
            return
            
        click.echo("Available regulation frameworks:")
        click.echo("-" * 80)
        
        for fw in frameworks:
            click.echo(f"ID: {fw.get('id', 'Unknown')}")
            click.echo(f"Name: {fw.get('name', 'Unknown')}")
            click.echo(f"Version: {fw.get('version', 'Unknown')}")
            click.echo(f"Region: {fw.get('region', 'Unknown')}")
            click.echo(f"Description: {fw.get('description', 'No description')}")
            
            # Check if framework files exist
            fw_dir = os.path.join(script_dir, "knowledge_base", fw.get('id', ''))
            if os.path.exists(fw_dir):
                files = []
                if os.path.exists(os.path.join(fw_dir, "articles.txt")):
                    files.append("articles.txt")
                if os.path.exists(os.path.join(fw_dir, "context.txt")):
                    files.append("context.txt")
                if os.path.exists(os.path.join(fw_dir, "common_patterns.txt")):
                    files.append("common_patterns.txt")
                if os.path.exists(os.path.join(fw_dir, "prompts.json")):
                    files.append("prompts.json")
                    
                click.echo(f"Available files: {', '.join(files)}")
            else:
                click.echo("Warning: Framework directory not found")
                
            click.echo("-" * 80)
            
    except Exception as e:
        click.echo(f"Error reading regulation index: {e}")

def analyze_chunks(llm, embeddings, document_chunks, batch_size=None, debug=False):
    """Analyze each chunk independently for compliance issues with improved efficiency."""
    # Use model's recommended batch size if not specified
    if batch_size is None:
        batch_size = llm.get_batch_size()
    
    all_chunk_results = []
    
    # Process in batches for better efficiency
    for i in range(0, len(document_chunks), batch_size):
        batch = document_chunks[i:i + batch_size]
        batch_end = min(i + batch_size, len(document_chunks))
        print(f"Processing batch {i//batch_size + 1}/{(len(document_chunks) + batch_size - 1)//batch_size} (chunks {i+1}-{batch_end} of {len(document_chunks)})...")
        
        batch_results = []
        # Process each chunk in the batch
        for chunk_index, chunk in enumerate(batch):
            # Find relevant regulations
            similar_regulations = embeddings.find_similar(chunk["text"])
            
            # Analyze compliance
            chunk_result = llm.analyze_compliance_with_metadata(chunk, similar_regulations)
            
            # Add chunk info to result
            chunk_result.update({
                "chunk_index": i + chunk_index,
                "position": chunk.get("position", "Unknown"),
                "text": chunk["text"]
            })
            
            batch_results.append(chunk_result)
                
        # Add batch results to all results
        all_chunk_results.extend(batch_results)
        print(f"Processed {len(batch_results)} chunks in this batch")
        
    return all_chunk_results

def deduplicate_issues(findings: List[Dict]) -> List[Dict]:
    """Improved deduplication with better semantic grouping."""
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
        issue_text = finding.get("issue", "").lower()
        section = finding.get("section", "Unknown")
        
        # Normalize the issue text to catch similar issues
        normalized_issue = re.sub(r'\b(the|a|an|is|are|will|shall|should|may|might|can|could)\b', '', issue_text)
        normalized_issue = re.sub(r'\s+', ' ', normalized_issue).strip()
        
        # Create a key combining regulation and issue
        key = f"{regulation}:{normalized_issue[:40]}"
        
        # If this is a new unique issue, add it
        if key not in unique_issues:
            unique_issues[key] = {
                "issue": finding.get("issue", "Unknown issue"),
                "regulation": regulation,
                "confidence": finding.get("confidence", "Medium"),
                "explanation": finding.get("explanation", ""),
                "section": section,
                "text": finding.get("text", "")
            }
            if "citation" in finding:
                unique_issues[key]["citation"] = finding["citation"]
        else:
            # Update existing entry
            existing = unique_issues[key]
            
            # Combine sections
            if isinstance(existing["section"], list):
                if section not in existing["section"]:
                    existing["section"].append(section)
            else:
                if section != existing["section"]:
                    existing["section"] = [existing["section"], section]
            
            # Use higher confidence if available
            confidence_value = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
            if confidence_value.get(finding.get("confidence", "").upper(), 0) > confidence_value.get(existing["confidence"].upper(), 0):
                existing["confidence"] = finding.get("confidence", "Medium")
            
            # Use longer explanation if available
            if len(finding.get("explanation", "")) > len(existing["explanation"]):
                existing["explanation"] = finding.get("explanation", "")
                
            # Take citation if available
            if "citation" in finding and "citation" not in existing:
                existing["citation"] = finding["citation"]
    
    # Convert dictionary to list and sort by confidence
    result = list(unique_issues.values())
    result.sort(key=lambda x: (
        {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x.get("confidence", "").upper(), 3),
        x.get("regulation", "")
    ))
    
    return result

def export_detailed_report(export_path, analyzed_file, regulation_framework, findings, document_metadata, all_chunk_results):
    """Export a concise, focused report that shows issues by document section."""
    try:
        with open(export_path, 'w', encoding='utf-8') as f:
            # Write report header
            f.write("=" * 80 + "\n")
            f.write(f"{regulation_framework.upper()} COMPLIANCE ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            # Document information
            f.write(f"Document: {os.path.basename(analyzed_file)}\n")
            f.write(f"Document Type: {document_metadata.get('document_type', 'Unknown')}\n")
            f.write(f"Regulation: {regulation_framework}\n")
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Data context
            f.write("POTENTIAL DATA CONTEXT:\n")
            f.write(f"Data mentions: {', '.join(document_metadata.get('potential_data_mentions', ['None detected']))}\n")
            f.write(f"Compliance indicators: {', '.join(document_metadata.get('compliance_indicators', ['None detected']))}\n\n")
            
            # Count total issues
            total_issues = len(findings)
            f.write(f"Total Issues Found: {total_issues}\n\n")
            
            if total_issues == 0:
                f.write("NO COMPLIANCE ISSUES DETECTED\n")
                f.write("=" * 80 + "\n\n")
                return True
            
            # Count by confidence
            high_confidence = sum(1 for f in findings if f.get("confidence", "").upper() == "HIGH")
            medium_confidence = sum(1 for f in findings if f.get("confidence", "").upper() == "MEDIUM")
            low_confidence = sum(1 for f in findings if f.get("confidence", "").upper() == "LOW")
            
            f.write("CONFIDENCE BREAKDOWN:\n")
            f.write(f"- High Confidence Issues: {high_confidence}\n")
            f.write(f"- Medium Confidence Issues: {medium_confidence}\n")
            f.write(f"- Low Confidence Issues: {low_confidence}\n\n")
            
            # Group issues by regulation for summary
            f.write("SUMMARY OF COMPLIANCE CONCERNS:\n")
            f.write("-" * 80 + "\n\n")
            
            # Group findings by regulation
            by_regulation = {}
            for finding in findings:
                regulation = finding.get("regulation", "Unknown regulation")
                if regulation not in by_regulation:
                    by_regulation[regulation] = []
                by_regulation[regulation].append(finding)
            
            # Display regulations with their issues
            for regulation, reg_issues in by_regulation.items():
                f.write(f"{regulation}:\n")
                
                # Group sections for this regulation
                section_mentions = {}
                for issue in reg_issues:
                    issue_desc = issue.get("issue", "Unknown issue")
                    section = issue.get("section", "Unknown section")
                    confidence = issue.get("confidence", "Medium")
                    
                    if issue_desc not in section_mentions:
                        section_mentions[issue_desc] = {
                            "sections": [section],
                            "confidence": confidence
                        }
                    else:
                        if section not in section_mentions[issue_desc]["sections"]:
                            section_mentions[issue_desc]["sections"].append(section)
                
                # Display issues with their sections
                for issue_desc, details in section_mentions.items():
                    sections = details["sections"]
                    confidence = details["confidence"]
                    
                    # Format sections nicely
                    if len(sections) <= 2:
                        section_text = ", ".join(sections)
                    else:
                        section_text = f"{sections[0]}, {sections[1]} and {len(sections)-2} more"
                    
                    f.write(f"  - {issue_desc} (in {section_text}, {confidence} confidence)\n")
                
                f.write("\n")
            
            f.write("-" * 80 + "\n\n")
            
            # Organize results by section with their document text
            findings_by_section = {}
            for finding in findings:
                section = finding.get("section", "Unknown section") 
                if section not in findings_by_section:
                    findings_by_section[section] = []
                findings_by_section[section].append(finding)
            
            # Find the section text for each finding
            section_texts = {}
            for chunk in all_chunk_results:
                section = chunk.get("position", "Unknown")
                if section not in section_texts:
                    section_texts[section] = chunk.get("text", "")
            
            # Display detailed findings by section
            finding_counter = 1
            for section, section_findings in findings_by_section.items():
                if not section_findings:
                    continue
                    
                f.write(f"FINDING #{finding_counter} - {section}\n")
                f.write("-" * 80 + "\n\n")
                finding_counter += 1
                
                # Display section text
                text = section_texts.get(section, "Text not available")
                f.write("DOCUMENT TEXT:\n")
                f.write(f"{text}\n\n")
                
                # Display findings for this section
                f.write("COMPLIANCE ISSUE:\n\n")
                
                for i, finding in enumerate(section_findings):
                    issue = finding.get("issue", "Unknown issue")
                    regulation = finding.get("regulation", "Unknown regulation")
                    confidence = finding.get("confidence", "Medium")
                    explanation = finding.get("explanation", "No explanation provided")
                    citation = finding.get("citation", "")
                    
                    f.write(f"Issue: {issue}\n")
                    f.write(f"Regulation: {regulation}\n") 
                    f.write(f"Confidence: {confidence}\n")
                    f.write(f"Explanation: {explanation}\n")
                    
                    if citation:
                        f.write(f"Citation: \"{citation}\"\n")
                    
                    if i < len(section_findings) - 1:
                        f.write("\n" + "-" * 40 + "\n\n")
                
                f.write("\n")
                f.write("=" * 80 + "\n\n")
        
        return True
        
    except Exception as e:
        print(f"Error exporting report: {e}")
        return False

if __name__ == "__main__":
    cli()