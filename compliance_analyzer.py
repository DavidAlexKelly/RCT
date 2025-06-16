# compliance_analyzer.py

#!/usr/bin/env python
import os
import json
import click
import re
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

# Import modules
from utils.document_processor import DocumentProcessor
from utils.embeddings_handler import EmbeddingsHandler
from utils.llm_handler import LLMHandler
from utils.progressive_analyzer import ProgressiveAnalyzer
from utils.prompt_manager import PromptManager
from utils.report_generator import ReportGenerator

# Import unified configuration
from config import (
    # Model configuration
    MODELS, DEFAULT_MODEL,
    # Document processing
    DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP, 
    PROGRESSIVE_ANALYSIS_ENABLED,
    # Performance tuning
    PerformancePresets, apply_preset, get_current_config, 
    print_config_summary, RAGConfig, ProgressiveConfig
)

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
@click.option("--optimize-chunks", is_flag=True, default=True, help="Optimize chunking strategy based on document size")
@click.option("--no-progressive", is_flag=True, default=False, help="Disable progressive analysis (not recommended)")
@click.option("--debug", is_flag=True, default=False, help="Enable detailed debug output")
@click.option("--preset", type=click.Choice(['accuracy', 'speed', 'balanced', 'comprehensive']), 
              help="Use performance preset (overrides other settings)")
@click.option("--rag-articles", type=int, help="Number of regulation articles to show LLM (overrides preset)")
@click.option("--risk-threshold", type=int, help="High risk threshold for progressive analysis (overrides preset)")
def analyze(file, regulation_framework, chunk_size, overlap, export, model, batch_size, 
           optimize_chunks, no_progressive, debug, preset, rag_articles, risk_threshold):
    """Analyze a document for compliance issues using specified regulation framework."""
    
    # Apply performance preset if specified
    if preset:
        click.echo(f"Applying {preset} performance preset...")
        preset_config = apply_preset(preset)
        click.echo(f"Preset applied: {preset_config}")
    
    # Apply individual overrides
    if rag_articles:
        RAGConfig.ARTICLES_COUNT = rag_articles
        click.echo(f"RAG articles count override: {rag_articles}")
    
    if risk_threshold:
        ProgressiveConfig.HIGH_RISK_THRESHOLD = risk_threshold
        click.echo(f"Risk threshold override: {risk_threshold}")
    
    # Display current configuration
    if debug:
        print_config_summary()
    
    # Get model description safely
    model_description = ""
    if model in MODELS:
        model_description = f" ({MODELS[model].get('description', 'No description')})"
    
    click.echo(f"Analyzing {file} for {regulation_framework} compliance...")
    click.echo(f"Using model: {model}{model_description}")
    
    # Progressive is now the default unless disabled or preset overrides
    progressive = not no_progressive and ProgressiveConfig.ENABLED
    if no_progressive:
        click.echo("Warning: Progressive analysis disabled - this may increase processing time")
    
    # Validate regulation framework exists
    knowledge_base_dir = get_knowledge_base_dir()
    regulation_dir = os.path.join(knowledge_base_dir, regulation_framework)
    
    if not os.path.exists(regulation_dir):
        # Check if regulation index exists
        index_path = os.path.join(knowledge_base_dir, "regulation_index.json")
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
    
    # Load knowledge base
    knowledge_base = load_knowledge_base(regulation_framework, embeddings, debug)
    if not knowledge_base:
        click.echo(f"Error: Failed to load knowledge base for {regulation_framework}")
        return
    
    # Create prompt manager
    prompt_manager = PromptManager(
        regulation_framework=regulation_framework,
        regulation_context=knowledge_base.get("context", ""),
        regulation_patterns=knowledge_base.get("patterns", "")
    )
    
    # Create LLM handler with prompt manager
    model_config = MODELS.get(model, MODELS[DEFAULT_MODEL])
    llm = LLMHandler(
        model_config=model_config, 
        prompt_manager=prompt_manager,
        debug=debug
    )
    
    # Use recommended batch size from model config if not overridden
    if batch_size is None:
        batch_size = llm.get_batch_size()
        
    click.echo(f"Using batch size: {batch_size}")
    
    # Display key configuration
    click.echo(f"Configuration: RAG articles={RAGConfig.ARTICLES_COUNT}, Risk threshold={ProgressiveConfig.HIGH_RISK_THRESHOLD}")
    
    # Process document and extract chunks
    try:
        document_info = doc_processor.process_document(file, optimize_chunks)
        document_chunks = document_info["chunks"]
        document_metadata = document_info["metadata"]
    except Exception as e:
        click.echo(f"Error processing document: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return
    
    if not document_chunks:
        click.echo("Error: No text was extracted from the document!")
        return
    
    click.echo(f"Extracted {len(document_chunks)} chunks from the document")
    click.echo(f"Sample chunk (first 100 chars): {document_chunks[0]['text'][:100]}...")
    click.echo(f"Document type detected: {document_metadata.get('document_type', 'unknown')}")
    click.echo(f"Potential data mentions: {', '.join(document_metadata.get('potential_data_mentions', []))}")
    
    # Create progressive analyzer
    progressive_analyzer = ProgressiveAnalyzer(
        llm_handler=llm,
        embeddings_handler=embeddings,
        regulation_framework=regulation_framework,
        batch_size=batch_size,
        debug=debug
    )
    
    # Analyze document with progressive or batch approach
    if progressive:
        click.echo(f"Using progressive analysis (threshold: {ProgressiveConfig.HIGH_RISK_THRESHOLD})...")
        all_chunk_results = progressive_analyzer.analyze(document_chunks)
    else:
        click.echo("Using traditional batch analysis...")
        all_chunk_results = progressive_analyzer.analyze_batch(document_chunks)
    
    # Process findings and generate output
    report_generator = ReportGenerator(debug=debug)
    
    # Extract and deduplicate issues only
    (deduplicated_findings,) = report_generator.process_results(all_chunk_results)
    
    # Generate output report
    output = {
        "document": os.path.basename(file),
        "document_type": document_metadata.get("document_type", "unknown"),
        "regulation_framework": regulation_framework,
        "findings": deduplicated_findings,
        "analysis_type": "progressive" if progressive else "standard",
        "configuration": get_current_config(),
        "summary": f"The document contains {len(deduplicated_findings)} potential compliance issue(s) related to {regulation_framework}."
    }
    
    click.echo(json.dumps(output, indent=2))
    
    # Export detailed findings if requested
    if export:
        # Ensure the directory exists
        export_dir = os.path.dirname(export)
        if export_dir and not os.path.exists(export_dir):
            try:
                os.makedirs(export_dir, exist_ok=True)
                click.echo(f"Created directory: {export_dir}")
            except Exception as e:
                click.echo(f"Warning: Could not create directory {export_dir}: {e}")
        
        # Generate and export report
        success = report_generator.export_report(
            export_path=export,
            analyzed_file=file,
            regulation_framework=regulation_framework,
            findings=deduplicated_findings,
            document_metadata=document_metadata,
            chunk_results=all_chunk_results
        )
        
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
    knowledge_base_dir = get_knowledge_base_dir()
    index_path = os.path.join(knowledge_base_dir, "regulation_index.json")
    
    if not os.path.exists(index_path):
        # Try alternative name
        index_path = os.path.join(knowledge_base_dir, "regulation_index")
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
            fw_dir = os.path.join(knowledge_base_dir, fw.get('id', ''))
            if os.path.exists(fw_dir):
                files = []
                for filename in ["articles.txt", "context.txt", "common_patterns.txt", "prompts.json", "handler.py"]:
                    if os.path.exists(os.path.join(fw_dir, filename)):
                        files.append(filename)
                    
                click.echo(f"Available files: {', '.join(files)}")
            else:
                click.echo("Warning: Framework directory not found")
                
            click.echo("-" * 80)
            
    except Exception as e:
        click.echo(f"Error reading regulation index: {e}")

@cli.command()
def config():
    """Display current performance configuration."""
    print_config_summary()
    current = get_current_config()
    click.echo("\nDetailed Configuration:")
    for key, value in current.items():
        click.echo(f"  {key}: {value}")

@cli.command()
@click.argument("preset_name", type=click.Choice(['accuracy', 'speed', 'balanced', 'comprehensive']))
def preset(preset_name):
    """Apply a performance preset and show the configuration."""
    click.echo(f"Applying {preset_name} preset...")
    config = apply_preset(preset_name)
    click.echo(f"Applied configuration: {config}")
    print_config_summary()

@cli.command()
@click.argument("framework_name")
def validate(framework_name):
    """Validate a regulation framework knowledge base."""
    import subprocess
    import sys
    
    try:
        result = subprocess.run([sys.executable, "validate_knowledge_base.py", framework_name], 
                              capture_output=True, text=True)
        click.echo(result.stdout)
        if result.stderr:
            click.echo("Errors:", err=True)
            click.echo(result.stderr, err=True)
        sys.exit(result.returncode)
    except FileNotFoundError:
        click.echo("Error: validate_knowledge_base.py not found. Make sure it's in the current directory.")
        sys.exit(1)

def get_knowledge_base_dir() -> str:
    """Get the path to the knowledge base directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "knowledge_base")

def load_knowledge_base(regulation_framework, embeddings, debug=False):
    """Load knowledge base for a regulation framework with better error handling."""
    knowledge_base = {}
    
    # Determine knowledge base paths
    knowledge_base_dir = get_knowledge_base_dir()
    articles_path = os.path.join(knowledge_base_dir, regulation_framework, "articles.txt")
    context_path = os.path.join(knowledge_base_dir, regulation_framework, "context.txt")
    patterns_path = os.path.join(knowledge_base_dir, regulation_framework, "common_patterns.txt")
    handler_path = os.path.join(knowledge_base_dir, regulation_framework, "handler.py")
    
    # Print available files for debugging
    if debug:
        print(f"Looking for {regulation_framework} knowledge base files:")
        print(f"  Articles: {'FOUND' if os.path.exists(articles_path) else 'NOT FOUND'}")
        print(f"  Context: {'FOUND' if os.path.exists(context_path) else 'NOT FOUND'}")
        print(f"  Patterns: {'FOUND' if os.path.exists(patterns_path) else 'NOT FOUND'}")
        print(f"  Handler: {'FOUND' if os.path.exists(handler_path) else 'NOT FOUND'}")
    
    # Verify articles file exists
    if not os.path.exists(articles_path):
        print(f"Error: Articles file not found at {articles_path}")
        return None
    
    # Load articles (required)
    try:
        print(f"Loading {regulation_framework} articles from {articles_path}...")
        embeddings.build_knowledge_base(articles_path)
        knowledge_base["articles"] = True
    except Exception as e:
        print(f"Error loading articles: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return None
    
    # Load context (optional)
    knowledge_base["context"] = ""
    if os.path.exists(context_path):
        try:
            with open(context_path, 'r', encoding='utf-8') as f:
                knowledge_base["context"] = f.read()
                print(f"Loaded {regulation_framework} context information")
        except Exception as e:
            print(f"Warning: Could not load context file: {e}")
            if debug:
                import traceback
                traceback.print_exc()
    
    # Load patterns (optional)
    knowledge_base["patterns"] = ""
    if os.path.exists(patterns_path):
        try:
            with open(patterns_path, 'r', encoding='utf-8') as f:
                knowledge_base["patterns"] = f.read()
                # Count patterns for better debugging
                pattern_count = knowledge_base["patterns"].count("Pattern:")
                print(f"Loaded {regulation_framework} common patterns ({pattern_count} patterns)")
        except Exception as e:
            print(f"Warning: Could not load patterns file: {e}")
            if debug:
                import traceback
                traceback.print_exc()
    
    # Check if handler can be imported
    if os.path.exists(handler_path):
        try:
            # Just check if the file can be read
            with open(handler_path, 'r', encoding='utf-8') as f:
                handler_code = f.read()
                if "RegulationHandler" in handler_code:
                    print(f"Found {regulation_framework} handler with RegulationHandler class")
                    knowledge_base["has_handler"] = True
                else:
                    print(f"Warning: {regulation_framework} handler exists but doesn't contain RegulationHandler class")
                    knowledge_base["has_handler"] = False
        except Exception as e:
            print(f"Warning: Could not check handler file: {e}")
            knowledge_base["has_handler"] = False
    else:
        print(f"No custom handler for {regulation_framework}")
        knowledge_base["has_handler"] = False
    
    return knowledge_base

if __name__ == "__main__":
    cli()