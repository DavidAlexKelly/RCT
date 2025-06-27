# compliance_analyzer.py - UPDATED CLI to match simplified config

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
    DocumentConfig, 
    # Performance tuning
    PerformancePresets, apply_preset, get_current_config, 
    print_config_summary, RAGConfig, ProgressiveConfig,
    # Chunking support
    ChunkingPresets, apply_chunking_preset, get_chunking_methods
)

@click.group()
def cli():
    """Regulatory Compliance Analysis Tool"""
    pass

@cli.command()
@click.option("--file", required=True, help="Path to the document file")
@click.option("--regulation-framework", default="gdpr", help="Regulation framework to use (gdpr, hipaa, ccpa, etc.)")

# Simplified options - only the core 4 settings plus export
@click.option("--model", default=DEFAULT_MODEL, help=f"Model to use: {', '.join(MODELS.keys())}")
@click.option("--preset", default="balanced", 
              type=click.Choice(['accuracy', 'speed', 'balanced', 'comprehensive']), 
              help="Performance preset (controls speed vs thoroughness)")
@click.option("--chunking-method", default="smart",
              type=click.Choice(['smart', 'paragraph', 'sentence', 'simple']),
              help="Method for splitting document into chunks")
@click.option("--export", help="Export detailed findings to a text file (provide file path)")

# Advanced options for power users (hidden behind debug flag)
@click.option("--debug", is_flag=True, default=False, help="Enable detailed debug output and show all options")
@click.option("--batch-size", default=None, type=int, help="Override the recommended batch size for the model (debug only)")
def analyze(file, regulation_framework, model, preset, chunking_method, export, debug, batch_size):
    """Analyze a document for compliance issues using specified regulation framework."""
    
    # Apply performance preset to get all technical parameters
    click.echo(f"Applying {preset} performance preset...")
    try:
        preset_config = apply_preset(preset)
        click.echo(f"✅ Preset applied")
        if debug:
            click.echo(f"Preset configuration: {preset_config}")
    except Exception as e:
        click.echo(f"❌ Error applying preset: {e}")
        return
    
    # Display current configuration
    if debug:
        print_config_summary()
        click.echo(f"\nChunking Method: {chunking_method}")
    
    # Get model description safely
    model_description = ""
    if model in MODELS:
        model_description = f" ({MODELS[model].get('description', 'No description')})"
    
    click.echo(f"Analyzing {file} for {regulation_framework} compliance...")
    click.echo(f"Using model: {model}{model_description}")
    click.echo(f"Performance: {preset} preset")
    click.echo(f"Chunking: {chunking_method} method")
    
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
    
    # Get chunking parameters from preset
    chunk_size = preset_config.get('chunk_size', DocumentConfig.DEFAULT_CHUNK_SIZE)
    chunk_overlap = preset_config.get('chunk_overlap', DocumentConfig.DEFAULT_CHUNK_OVERLAP)
    optimize_chunks = preset_config.get('optimize_chunks', DocumentConfig.OPTIMIZE_CHUNK_SIZE)
    enable_progressive = preset_config.get('progressive_enabled', ProgressiveConfig.ENABLED)
    
    # Initialize components
    doc_processor = DocumentProcessor(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunking_method=chunking_method  # User choice overrides preset
    )
    
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
        
    if debug:
        click.echo(f"Using batch size: {batch_size}")
        click.echo(f"Configuration: RAG articles={RAGConfig.ARTICLES_COUNT}, Risk threshold={ProgressiveConfig.HIGH_RISK_THRESHOLD}")
        click.echo(f"Progressive analysis: {enable_progressive}")
    
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
    
    # Enhanced chunking feedback
    chunk_info = f"Extracted {len(document_chunks)} chunks from the document using {chunking_method} method"
    if debug and document_chunks:
        chunk_sizes = [len(chunk.get("text", "")) for chunk in document_chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes)
        chunk_info += f" (average size: {avg_size:.0f} characters, range: {min(chunk_sizes)}-{max(chunk_sizes)})"
    
    click.echo(chunk_info)
    click.echo(f"Document type detected: {document_metadata.get('document_type', 'unknown')}")
    
    if debug:
        click.echo(f"Sample chunk (first 100 chars): {document_chunks[0]['text'][:100]}...")
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
    if enable_progressive:
        click.echo(f"Using progressive analysis...")
        all_chunk_results = progressive_analyzer.analyze(document_chunks)
    else:
        click.echo("Using comprehensive batch analysis...")
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
        "analysis_type": "progressive" if enable_progressive else "comprehensive",
        "configuration": {
            "framework": regulation_framework,
            "model": model,
            "preset": preset,
            "chunking_method": chunking_method,
            "rag_articles": RAGConfig.ARTICLES_COUNT,
            "risk_threshold": ProgressiveConfig.HIGH_RISK_THRESHOLD,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap
        },
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

# Keep all existing commands unchanged
@cli.command()
def chunking():
    """Display available chunking methods and presets."""
    click.echo("Available chunking methods:")
    click.echo("-" * 40)
    
    methods = get_chunking_methods()
    for method, description in methods.items():
        click.echo(f"{method}: {description}")
    
    click.echo("\nAvailable chunking presets:")
    click.echo("-" * 40)
    
    presets = {
        'fast': 'Optimized for speed - smaller chunks, simple method',
        'balanced': 'Balanced approach - good speed and context', 
        'context': 'Optimized for accuracy - larger chunks, better context',
        'compliance': 'Optimized for compliance documents - section-aware'
    }
    
    for preset, description in presets.items():
        preset_config = {
            'fast': ChunkingPresets.fast_processing(),
            'balanced': ChunkingPresets.balanced(),
            'context': ChunkingPresets.high_context(),
            'compliance': ChunkingPresets.compliance_focused()
        }[preset]
        
        click.echo(f"{preset}: {description}")
        click.echo(f"  Method: {preset_config['chunking_method']}, Size: {preset_config['chunk_size']}, Overlap: {preset_config['chunk_overlap']}")

@cli.command()
@click.option("--method", type=click.Choice(['smart', 'paragraph', 'sentence', 'simple']), help="Chunking method to test")
@click.option("--size", type=int, default=800, help="Chunk size to test")
@click.option("--file", required=True, help="Test file to chunk")
def test_chunking(method, size, file):
    """Test chunking on a file without running analysis."""
    
    click.echo(f"Testing chunking on {file}")
    click.echo(f"Method: {method or 'smart'}, Size: {size}")
    click.echo("-" * 40)
    
    try:
        doc_processor = DocumentProcessor(
            chunk_size=size,
            chunk_overlap=100,
            chunking_method=method or 'smart'
        )
        
        document_info = doc_processor.process_document(file, optimize_chunks=False)
        document_chunks = document_info["chunks"]
        
        click.echo(f"Created {len(document_chunks)} chunks")
        
        if document_chunks:
            chunk_sizes = [len(chunk.get("text", "")) for chunk in document_chunks]
            click.echo(f"Average size: {sum(chunk_sizes)/len(chunk_sizes):.0f} characters")
            click.echo(f"Size range: {min(chunk_sizes)} - {max(chunk_sizes)} characters")
            
            # Show first few chunk positions
            click.echo("\nFirst few chunks:")
            for i, chunk in enumerate(document_chunks[:5]):
                position = chunk.get("position", f"Chunk {i+1}")
                size = len(chunk.get("text", ""))
                chunk_type = chunk.get("type", "unknown")
                click.echo(f"  {i+1}. {position} ({size} chars, type: {chunk_type})")
                
                # Show first line of text
                text = chunk.get("text", "")
                first_line = text.split('\n')[0][:60]
                if len(first_line) < len(text.split('\n')[0]):
                    first_line += "..."
                click.echo(f"     \"{first_line}\"")
                
            if len(document_chunks) > 5:
                click.echo(f"     ... and {len(document_chunks) - 5} more chunks")
        
    except Exception as e:
        click.echo(f"Error testing chunking: {e}")

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

# Keep existing helper functions
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