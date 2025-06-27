#!/usr/bin/env python
"""
Regulatory Compliance Analysis Tool - Command Line Interface

A CLI tool for analyzing documents against regulatory frameworks like GDPR.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

import click

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Import modules
from utils.document_processor import DocumentProcessor
from utils.embeddings_handler import EmbeddingsHandler
from utils.llm_handler import LLMHandler
from utils.progressive_analyzer import ProgressiveAnalyzer
from utils.prompt_manager import PromptManager
from utils.report_generator import ReportGenerator

# Import unified configuration
from config import (
    MODELS, DEFAULT_MODEL,
    DocumentConfig, 
    PerformancePresets, apply_preset, get_current_config, 
    print_config_summary, RAGConfig, ProgressiveConfig,
    ChunkingPresets, apply_chunking_preset, get_chunking_methods
)


@click.group()
def cli():
    """Regulatory Compliance Analysis Tool"""
    pass


@cli.command()
@click.option("--file", required=True, help="Path to the document file")
@click.option("--regulation-framework", default="gdpr", help="Regulation framework to use")
@click.option("--model", default=DEFAULT_MODEL, help=f"Model to use: {', '.join(MODELS.keys())}")
@click.option("--preset", default="balanced", 
              type=click.Choice(['accuracy', 'speed', 'balanced', 'comprehensive']), 
              help="Performance preset (controls speed vs thoroughness)")
@click.option("--chunking-method", default="smart",
              type=click.Choice(['smart', 'paragraph', 'sentence', 'simple']),
              help="Method for splitting document into chunks")
@click.option("--export", help="Export detailed findings to a text file")
@click.option("--debug", is_flag=True, default=False, help="Enable detailed debug output")
@click.option("--batch-size", default=None, type=int, help="Override batch size (debug only)")
def analyze(file: str, regulation_framework: str, model: str, preset: str, 
           chunking_method: str, export: Optional[str], debug: bool, 
           batch_size: Optional[int]) -> None:
    """Analyze a document for compliance issues using specified regulation framework."""
    
    # Configure logging level based on debug flag
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Apply performance preset
    logger.info(f"Applying {preset} performance preset...")
    try:
        preset_config = apply_preset(preset)
        logger.info("✅ Preset applied successfully")
        if debug:
            logger.debug(f"Preset configuration: {preset_config}")
    except Exception as e:
        logger.error(f"Failed to apply preset: {e}")
        return
    
    # Display configuration in debug mode
    if debug:
        print_config_summary()
        logger.debug(f"Chunking Method: {chunking_method}")
    
    # Log analysis start
    model_description = MODELS.get(model, {}).get('description', 'No description')
    logger.info(f"Analyzing {file} for {regulation_framework} compliance...")
    logger.info(f"Using model: {model} ({model_description})")
    logger.info(f"Performance: {preset} preset, Chunking: {chunking_method} method")
    
    # Validate regulation framework
    if not _validate_regulation_framework(regulation_framework):
        return
    
    try:
        # Initialize components
        components = _initialize_components(
            file, regulation_framework, model, preset_config, 
            chunking_method, batch_size, debug
        )
        if not components:
            return
            
        # Run analysis
        results = _run_analysis(components, debug)
        if not results:
            return
            
        # Generate and display output
        _generate_output(file, regulation_framework, model, preset, 
                        chunking_method, results, export, debug)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        if debug:
            import traceback
            traceback.print_exc()


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
        'fast': ChunkingPresets.fast_processing(),
        'balanced': ChunkingPresets.balanced(),
        'context': ChunkingPresets.high_context(),
        'compliance': ChunkingPresets.compliance_focused()
    }
    
    for preset_name, preset_config in presets.items():
        descriptions = {
            'fast': 'Optimized for speed - smaller chunks, simple method',
            'balanced': 'Balanced approach - good speed and context', 
            'context': 'Optimized for accuracy - larger chunks, better context',
            'compliance': 'Optimized for compliance documents - section-aware'
        }
        
        click.echo(f"{preset_name}: {descriptions[preset_name]}")
        click.echo(f"  Method: {preset_config['chunking_method']}, "
                  f"Size: {preset_config['chunk_size']}, "
                  f"Overlap: {preset_config['chunk_overlap']}")


@cli.command()
@click.option("--method", type=click.Choice(['smart', 'paragraph', 'sentence', 'simple']), 
              help="Chunking method to test")
@click.option("--size", type=int, default=800, help="Chunk size to test")
@click.option("--file", required=True, help="Test file to chunk")
def test_chunking(method: Optional[str], size: int, file: str) -> None:
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
    knowledge_base_dir = _get_knowledge_base_dir()
    index_path = knowledge_base_dir / "regulation_index.json"
    
    if not index_path.exists():
        index_path = knowledge_base_dir / "regulation_index"
        if not index_path.exists():
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
            fw_dir = knowledge_base_dir / fw.get('id', '')
            if fw_dir.exists():
                files = []
                for filename in ["articles.txt", "context.txt", "common_patterns.txt", 
                               "prompts.json", "handler.py"]:
                    if (fw_dir / filename).exists():
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
def preset(preset_name: str) -> None:
    """Apply a performance preset and show the configuration."""
    click.echo(f"Applying {preset_name} preset...")
    config = apply_preset(preset_name)
    click.echo(f"Applied configuration: {config}")
    print_config_summary()


@cli.command()
@click.argument("framework_name")
def validate(framework_name: str) -> None:
    """Validate a regulation framework knowledge base."""
    try:
        import subprocess
        import sys
        
        result = subprocess.run(
            [sys.executable, "validate_knowledge_base.py", framework_name], 
            capture_output=True, text=True
        )
        click.echo(result.stdout)
        if result.stderr:
            click.echo("Errors:", err=True)
            click.echo(result.stderr, err=True)
        sys.exit(result.returncode)
    except FileNotFoundError:
        click.echo("Error: validate_knowledge_base.py not found. "
                  "Make sure it's in the current directory.")
        sys.exit(1)


def _get_knowledge_base_dir() -> Path:
    """Get the path to the knowledge base directory."""
    script_dir = Path(__file__).parent.absolute()
    return script_dir / "knowledge_base"


def _validate_regulation_framework(regulation_framework: str) -> bool:
    """Validate that the regulation framework exists."""
    knowledge_base_dir = _get_knowledge_base_dir()
    regulation_dir = knowledge_base_dir / regulation_framework
    
    if not regulation_dir.exists():
        index_path = knowledge_base_dir / "regulation_index.json"
        available_frameworks = []
        
        if index_path.exists():
            try:
                with open(index_path, 'r') as f:
                    index_data = json.load(f)
                    available_frameworks = [fw["id"] for fw in index_data.get("frameworks", [])]
            except Exception as e:
                logger.error(f"Error reading regulation index: {e}")
        
        logger.error(f"Regulation framework '{regulation_framework}' not found")
        if available_frameworks:
            logger.info("Available frameworks:")
            for fw_id in available_frameworks:
                logger.info(f"  - {fw_id}")
        return False
    
    return True


def _initialize_components(file: str, regulation_framework: str, model: str, 
                         preset_config: Dict[str, Any], chunking_method: str,
                         batch_size: Optional[int], debug: bool) -> Optional[Dict[str, Any]]:
    """Initialize all analysis components."""
    try:
        # Get chunking parameters from preset
        chunk_size = preset_config.get('chunk_size', DocumentConfig.DEFAULT_CHUNK_SIZE)
        chunk_overlap = preset_config.get('chunk_overlap', DocumentConfig.DEFAULT_CHUNK_OVERLAP)
        optimize_chunks = preset_config.get('optimize_chunks', DocumentConfig.OPTIMIZE_CHUNK_SIZE)
        
        # Initialize document processor
        doc_processor = DocumentProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunking_method=chunking_method
        )
        
        # Initialize embeddings handler
        embeddings = EmbeddingsHandler()
        
        # Load knowledge base
        knowledge_base = _load_knowledge_base(regulation_framework, embeddings, debug)
        if not knowledge_base:
            logger.error(f"Failed to load knowledge base for {regulation_framework}")
            return None
        
        # Create prompt manager
        prompt_manager = PromptManager(
            regulation_framework=regulation_framework,
            regulation_context=knowledge_base.get("context", ""),
            regulation_patterns=knowledge_base.get("patterns", "")
        )
        
        # Create LLM handler
        model_config = MODELS.get(model, MODELS[DEFAULT_MODEL])
        llm = LLMHandler(
            model_config=model_config, 
            prompt_manager=prompt_manager,
            debug=debug
        )
        
        # Use recommended batch size if not overridden
        if batch_size is None:
            batch_size = llm.get_batch_size()
        
        # Process document
        document_info = doc_processor.process_document(file, optimize_chunks)
        document_chunks = document_info["chunks"]
        document_metadata = document_info["metadata"]
        
        if not document_chunks:
            logger.error("No text was extracted from the document!")
            return None
        
        # Log document info
        chunk_info = (f"Extracted {len(document_chunks)} chunks using {chunking_method} method")
        if debug and document_chunks:
            chunk_sizes = [len(chunk.get("text", "")) for chunk in document_chunks]
            avg_size = sum(chunk_sizes) / len(chunk_sizes)
            chunk_info += f" (average size: {avg_size:.0f} characters)"
        
        logger.info(chunk_info)
        logger.info(f"Document type detected: {document_metadata.get('document_type', 'unknown')}")
        
        return {
            'doc_processor': doc_processor,
            'embeddings': embeddings,
            'llm': llm,
            'prompt_manager': prompt_manager,
            'document_chunks': document_chunks,
            'document_metadata': document_metadata,
            'batch_size': batch_size,
            'regulation_framework': regulation_framework,
            'preset_config': preset_config
        }
        
    except Exception as e:
        logger.error(f"Error initializing components: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return None


def _run_analysis(components: Dict[str, Any], debug: bool) -> Optional[Dict[str, Any]]:
    """Run the analysis with the initialized components."""
    try:
        enable_progressive = components['preset_config'].get('progressive_enabled', True)
        
        # Create progressive analyzer
        progressive_analyzer = ProgressiveAnalyzer(
            llm_handler=components['llm'],
            embeddings_handler=components['embeddings'],
            regulation_framework=components['regulation_framework'],
            batch_size=components['batch_size'],
            debug=debug
        )
        
        # Run analysis
        if enable_progressive:
            logger.info("Using progressive analysis...")
            all_chunk_results = progressive_analyzer.analyze(components['document_chunks'])
        else:
            logger.info("Using comprehensive batch analysis...")
            all_chunk_results = progressive_analyzer.analyze_batch(components['document_chunks'])
        
        # Process findings
        report_generator = ReportGenerator(debug=debug)
        (deduplicated_findings,) = report_generator.process_results(all_chunk_results)
        
        return {
            'findings': deduplicated_findings,
            'chunk_results': all_chunk_results,
            'report_generator': report_generator,
            'document_metadata': components['document_metadata'],
            'analysis_type': 'progressive' if enable_progressive else 'comprehensive'
        }
        
    except Exception as e:
        logger.error(f"Analysis execution failed: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return None


def _generate_output(file: str, regulation_framework: str, model: str, preset: str,
                    chunking_method: str, results: Dict[str, Any], 
                    export: Optional[str], debug: bool) -> None:
    """Generate and display analysis output."""
    # Create output structure
    output = {
        "document": os.path.basename(file),
        "document_type": results['document_metadata'].get("document_type", "unknown"),
        "regulation_framework": regulation_framework,
        "findings": results['findings'],
        "analysis_type": results['analysis_type'],
        "configuration": {
            "framework": regulation_framework,
            "model": model,
            "preset": preset,
            "chunking_method": chunking_method,
            "rag_articles": RAGConfig.ARTICLES_COUNT,
            "risk_threshold": ProgressiveConfig.HIGH_RISK_THRESHOLD
        },
        "summary": f"The document contains {len(results['findings'])} potential compliance issue(s) related to {regulation_framework}."
    }
    
    # Display JSON output
    click.echo(json.dumps(output, indent=2))
    
    # Export detailed report if requested
    if export:
        _export_detailed_report(export, file, regulation_framework, results)


def _export_detailed_report(export: str, file: str, regulation_framework: str, 
                           results: Dict[str, Any]) -> None:
    """Export detailed findings to a text file."""
    export_path = Path(export)
    export_dir = export_path.parent
    
    if export_dir != Path('.') and not export_dir.exists():
        try:
            export_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {export_dir}")
        except Exception as e:
            logger.warning(f"Could not create directory {export_dir}: {e}")
    
    # Generate and export report
    success = results['report_generator'].export_report(
        export_path=str(export_path),
        analyzed_file=file,
        regulation_framework=regulation_framework,
        findings=results['findings'],
        document_metadata=results['document_metadata'],
        chunk_results=results['chunk_results']
    )
    
    if success:
        logger.info(f"Detailed report exported to: {export}")
    else:
        logger.error(f"Failed to export report to: {export}")


def _load_knowledge_base(regulation_framework: str, embeddings: EmbeddingsHandler, 
                        debug: bool = False) -> Optional[Dict[str, Any]]:
    """Load knowledge base for a regulation framework."""
    knowledge_base = {}
    
    # Determine knowledge base paths
    knowledge_base_dir = _get_knowledge_base_dir()
    articles_path = knowledge_base_dir / regulation_framework / "articles.txt"
    context_path = knowledge_base_dir / regulation_framework / "context.txt"
    patterns_path = knowledge_base_dir / regulation_framework / "common_patterns.txt"
    handler_path = knowledge_base_dir / regulation_framework / "handler.py"
    
    # Log available files
    if debug:
        logger.debug(f"Looking for {regulation_framework} knowledge base files:")
        logger.debug(f"  Articles: {'FOUND' if articles_path.exists() else 'NOT FOUND'}")
        logger.debug(f"  Context: {'FOUND' if context_path.exists() else 'NOT FOUND'}")
        logger.debug(f"  Patterns: {'FOUND' if patterns_path.exists() else 'NOT FOUND'}")
        logger.debug(f"  Handler: {'FOUND' if handler_path.exists() else 'NOT FOUND'}")
    
    # Verify articles file exists (required)
    if not articles_path.exists():
        logger.error(f"Articles file not found at {articles_path}")
        return None
    
    # Load articles
    try:
        logger.info(f"Loading {regulation_framework} articles...")
        embeddings.build_knowledge_base(str(articles_path))
        knowledge_base["articles"] = True
    except Exception as e:
        logger.error(f"Error loading articles: {e}")
        return None
    
    # Load context (optional)
    knowledge_base["context"] = ""
    if context_path.exists():
        try:
            with open(context_path, 'r', encoding='utf-8') as f:
                knowledge_base["context"] = f.read()
                logger.info(f"Loaded {regulation_framework} context information")
        except Exception as e:
            logger.warning(f"Could not load context file: {e}")
    
    # Load patterns (optional)
    knowledge_base["patterns"] = ""
    if patterns_path.exists():
        try:
            with open(patterns_path, 'r', encoding='utf-8') as f:
                knowledge_base["patterns"] = f.read()
                pattern_count = knowledge_base["patterns"].count("Pattern:")
                logger.info(f"Loaded {regulation_framework} patterns ({pattern_count} patterns)")
        except Exception as e:
            logger.warning(f"Could not load patterns file: {e}")
    
    # Check handler availability
    if handler_path.exists():
        try:
            with open(handler_path, 'r', encoding='utf-8') as f:
                handler_code = f.read()
                if "RegulationHandler" in handler_code:
                    logger.info(f"Found {regulation_framework} handler")
                    knowledge_base["has_handler"] = True
                else:
                    logger.warning(f"{regulation_framework} handler missing RegulationHandler class")
                    knowledge_base["has_handler"] = False
        except Exception as e:
            logger.warning(f"Could not check handler file: {e}")
            knowledge_base["has_handler"] = False
    else:
        logger.info(f"No custom handler for {regulation_framework}")
        knowledge_base["has_handler"] = False
    
    return knowledge_base


if __name__ == "__main__":
    cli()