# engine.py - Unified Compliance Analysis Engine

"""
Central analysis engine for regulatory compliance analysis.
Handles all document processing, knowledge base loading, and LLM analysis.
"""

import os
import json
import tempfile
import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime

# Import core components
from utils.document_processor import DocumentProcessor
from utils.embeddings_handler import EmbeddingsHandler
from utils.llm_handler import LLMHandler
from utils.progressive_analyzer import ProgressiveAnalyzer
from utils.prompt_manager import PromptManager
from utils.report_generator import ReportGenerator

# Import configuration
from config import (
    MODELS, DEFAULT_MODEL, PERFORMANCE_PRESETS,
    apply_preset, get_current_config, RAGConfig, ProgressiveConfig
)

class ComplianceAnalyzer:
    """
    Main compliance analysis engine.
    Handles the complete analysis pipeline from document to results.
    """
    
    def __init__(self, debug: bool = False):
        """Initialize the compliance analyzer."""
        self.debug = debug
        self.knowledge_base_dir = self._get_knowledge_base_dir()
        
        # Initialize components (will be set up during analysis)
        self.doc_processor = None
        self.embeddings = None
        self.llm = None
        self.progressive_analyzer = None
        self.prompt_manager = None
        self.report_generator = None
        
    def analyze_document(self, 
                        file_path_or_content: Union[str, bytes],
                        regulation_framework: str,
                        config: Optional[Dict[str, Any]] = None,
                        original_filename: Optional[str] = None,
                        progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Analyze a document for compliance issues.
        
        Args:
            file_path_or_content: Path to file or file content (bytes)
            regulation_framework: Regulation framework to use (e.g., 'gdpr')
            config: Analysis configuration
            original_filename: Original filename (for extension detection when using bytes)
            progress_callback: Optional function to call with progress updates (progress, status, details)
            
        Returns:
            Dictionary with analysis results
        """
        
        # Apply configuration
        config = config or self._get_default_config()
        self._apply_configuration(config)
        
        if self.debug:
            print(f"Starting analysis with framework: {regulation_framework}")
            print(f"Configuration: {config}")
        
        if progress_callback:
            progress_callback(10, "🔍 Loading knowledge base...", "")
        
        # Handle file input (string path vs bytes content)
        temp_file_path = None
        try:
            if isinstance(file_path_or_content, bytes):
                # Create temporary file from bytes with correct extension
                if original_filename:
                    # Extract extension from original filename
                    file_extension = Path(original_filename).suffix
                    if not file_extension:
                        file_extension = '.tmp'
                else:
                    file_extension = '.tmp'
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
                    tmp_file.write(file_path_or_content)
                    temp_file_path = tmp_file.name
                    file_path = temp_file_path
            else:
                # Use provided file path
                file_path = file_path_or_content
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found: {file_path}")
            
            # Step 1: Load knowledge base
            if self.debug:
                print("Loading knowledge base...")
            
            self.embeddings = EmbeddingsHandler()
            knowledge_base = self._load_knowledge_base(regulation_framework)
            if not knowledge_base:
                raise ValueError(f"Failed to load knowledge base for {regulation_framework}")
            
            if progress_callback:
                progress_callback(20, "📄 Processing document...", f"Loaded {regulation_framework} knowledge base")
            
            # Step 2: Process document
            if self.debug:
                print("Processing document...")
            
            self.doc_processor = DocumentProcessor(
                chunk_size=config.get('chunk_size', 800),
                chunk_overlap=config.get('chunk_overlap', 100),
                chunking_method=config.get('chunking_method', 'smart')
            )
            
            document_info = self.doc_processor.process_document(
                file_path, 
                optimize_chunks=config.get('optimize_chunks', True)
            )
            
            document_chunks = document_info["chunks"]
            document_metadata = document_info["metadata"]
            
            if not document_chunks:
                raise ValueError("No text extracted from document")
            
            if self.debug:
                print(f"Created {len(document_chunks)} chunks")
            
            if progress_callback:
                progress_callback(30, "⚙️ Initializing analysis components...", f"Created {len(document_chunks)} chunks using {config.get('chunking_method', 'smart')} method")
            
            # Step 3: Initialize analysis components
            if self.debug:
                print("Initializing analysis components...")
            
            self.prompt_manager = PromptManager(
                regulation_framework=regulation_framework,
                regulation_context=knowledge_base.get("context", ""),
                regulation_patterns=knowledge_base.get("patterns", "")
            )
            
            model_config = MODELS.get(config.get('model', DEFAULT_MODEL))
            self.llm = LLMHandler(
                model_config=model_config,
                prompt_manager=self.prompt_manager,
                debug=self.debug
            )
            
            # Step 4: Run analysis
            if self.debug:
                print("Running analysis...")
            
            self.progressive_analyzer = ProgressiveAnalyzer(
                llm_handler=self.llm,
                embeddings_handler=self.embeddings,
                regulation_framework=regulation_framework,
                batch_size=self.llm.get_batch_size(),
                debug=self.debug
            )
            
            if progress_callback:
                progress_callback(40, "🔍 Analyzing document for compliance issues...", "Starting analysis...")
            
            # Choose analysis method with progress tracking
            if config.get('progressive_enabled', True):
                if self.debug:
                    print("Using progressive analysis")
                chunk_results = self._analyze_with_progress(document_chunks, True, progress_callback)
            else:
                if self.debug:
                    print("Using batch analysis")
                chunk_results = self._analyze_with_progress(document_chunks, False, progress_callback)
            
            # Step 5: Process results
            if self.debug:
                print("Processing results...")
            
            if progress_callback:
                progress_callback(90, "📊 Processing results...", "Deduplicating findings...")
            
            self.report_generator = ReportGenerator(debug=self.debug)
            (deduplicated_findings,) = self.report_generator.process_results(chunk_results)
            
            if progress_callback:
                progress_callback(95, "✅ Analysis complete!", f"Found {len(deduplicated_findings)} potential compliance issues")
            
            # Step 6: Build final results
            document_name = original_filename or (os.path.basename(file_path) if isinstance(file_path_or_content, str) else "uploaded_document")
            
            results = {
                "document_name": document_name,
                "regulation_framework": regulation_framework,
                "analysis_date": datetime.now().isoformat(),
                "findings": deduplicated_findings,
                "chunk_results": chunk_results,
                "metadata": document_metadata,
                "config": {
                    "framework": regulation_framework,
                    "model": config.get('model', DEFAULT_MODEL),
                    "preset": config.get('preset', 'balanced'),
                    "analysis_type": "Progressive" if config.get('progressive_enabled', True) else "Standard",
                    "analyzed_sections": len([c for c in chunk_results if c.get("should_analyze", True)]),
                    "total_sections": len(chunk_results),
                    "rag_articles": config.get('rag_articles', RAGConfig.ARTICLES_COUNT),
                    "risk_threshold": config.get('risk_threshold', ProgressiveConfig.HIGH_RISK_THRESHOLD),
                    "chunking_method": config.get('chunking_method', 'smart'),
                    "chunk_size": config.get('chunk_size', 800),
                    "chunk_overlap": config.get('chunk_overlap', 100)
                },
                "summary": f"Found {len(deduplicated_findings)} potential compliance issues",
                "report_generator": self.report_generator  # For exports
            }
            
            if self.debug:
                print(f"Analysis complete: {len(deduplicated_findings)} issues found")
            
            return results
            
        except Exception as e:
            if self.debug:
                import traceback
                traceback.print_exc()
            raise e
            
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
    
    def export_report(self, 
                     results: Dict[str, Any], 
                     export_path: str, 
                     report_type: str = "detailed") -> bool:
        """
        Export analysis results to a file.
        
        Args:
            results: Analysis results from analyze_document()
            export_path: Path to save the report
            report_type: "detailed", "summary", or "json"
            
        Returns:
            True if export succeeded
        """
        try:
            if report_type == "json":
                # Export as JSON
                export_data = {k: v for k, v in results.items() if k != "report_generator"}
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
                return True
                
            elif report_type == "summary":
                # Export summary
                summary = self._generate_summary(results)
                with open(export_path, 'w', encoding='utf-8') as f:
                    f.write(summary)
                return True
                
            else:  # detailed
                # Export detailed report
                report_generator = results.get("report_generator")
                if not report_generator:
                    report_generator = ReportGenerator(debug=self.debug)
                
                return report_generator.export_report(
                    export_path=export_path,
                    analyzed_file=results["document_name"],
                    regulation_framework=results["regulation_framework"],
                    findings=results["findings"],
                    document_metadata=results["metadata"],
                    chunk_results=results["chunk_results"]
                )
                
        except Exception as e:
            if self.debug:
                print(f"Export failed: {e}")
            return False
    
    def get_available_frameworks(self) -> List[Dict[str, str]]:
        """Get list of available regulation frameworks."""
        try:
            index_path = self.knowledge_base_dir / "regulation_index.json"
            
            if index_path.exists():
                with open(index_path, 'r') as f:
                    index_data = json.load(f)
                    return index_data.get("frameworks", [])
            else:
                # Scan directories and check for required files
                frameworks = []
                for item in self.knowledge_base_dir.iterdir():
                    if item.is_dir() and item.name != "__pycache__":
                        # Check if it has required files
                        validation = self.validate_framework(item.name)
                        if validation["valid"]:
                            # Try to get name from context.yaml
                            name = item.name.upper()
                            description = f"{name} compliance framework"
                            
                            try:
                                context_path = item / "context.yaml"
                                if context_path.exists():
                                    with open(context_path, 'r', encoding='utf-8') as f:
                                        context_data = yaml.safe_load(f)
                                        name = context_data.get('name', name)
                                        description = context_data.get('description', description)
                            except:
                                pass
                                
                            frameworks.append({
                                "id": item.name,
                                "name": name,
                                "description": description
                            })
                return frameworks
                
        except Exception as e:
            if self.debug:
                print(f"Error loading frameworks: {e}")
            return []
    
    def validate_framework(self, framework_id: str) -> Dict[str, Any]:
        """Validate that a regulation framework has all required files."""
        framework_dir = self.knowledge_base_dir / framework_id
        
        required_files = [
            "articles.txt",
            "classification.yaml", 
            "context.yaml",
            "handler.py",
            "README.md"
        ]
        
        validation = {
            "framework_id": framework_id,
            "valid": framework_dir.exists(),
            "missing_files": []
        }
        
        if framework_dir.exists():
            for filename in required_files:
                if not (framework_dir / filename).exists():
                    validation["missing_files"].append(filename)
                    validation["valid"] = False
        else:
            validation["missing_files"] = required_files
            validation["valid"] = False
        
        if self.debug and not validation["valid"]:
            print(f"Framework {framework_id} validation failed. Missing: {validation['missing_files']}")
        
        return validation
    
    def _get_knowledge_base_dir(self) -> Path:
        """Get the knowledge base directory path."""
        script_dir = Path(__file__).parent
        return script_dir / "knowledge_base"
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default analysis configuration."""
        return {
            'model': DEFAULT_MODEL,
            'preset': 'balanced',
            'progressive_enabled': True,
            'rag_articles': RAGConfig.ARTICLES_COUNT,
            'risk_threshold': ProgressiveConfig.HIGH_RISK_THRESHOLD,
            'chunking_method': 'smart',
            'chunk_size': 800,
            'chunk_overlap': 100,
            'optimize_chunks': True,
            'debug': self.debug
        }
    
    def _apply_configuration(self, config: Dict[str, Any]):
        """Apply configuration settings to global config."""
        # Apply preset if specified
        if 'preset' in config and config['preset'] in PERFORMANCE_PRESETS:
            preset_config = apply_preset(config['preset'])
            if self.debug:
                print(f"Applied preset '{config['preset']}': {preset_config}")
        
        # Apply individual overrides
        if 'rag_articles' in config:
            RAGConfig.ARTICLES_COUNT = config['rag_articles']
        
        if 'risk_threshold' in config:
            ProgressiveConfig.HIGH_RISK_THRESHOLD = config['risk_threshold']
        
        if 'progressive_enabled' in config:
            ProgressiveConfig.ENABLED = config['progressive_enabled']
    
    def _load_knowledge_base(self, regulation_framework: str) -> Optional[Dict[str, Any]]:
        """Load knowledge base from required YAML files."""
        try:
            framework_dir = self.knowledge_base_dir / regulation_framework
            
            if self.debug:
                print(f"Loading knowledge base from {framework_dir}")
            
            # Load articles (required)
            articles_path = framework_dir / "articles.txt"
            self.embeddings.build_knowledge_base(str(articles_path))
            
            # Load context from YAML (required)
            with open(framework_dir / "context.yaml", 'r', encoding='utf-8') as f:
                context_data = yaml.safe_load(f)
                context_summary = context_data.get('description', '')
                
                # Add key principles if available
                principles = context_data.get('key_principles', [])
                if principles:
                    principle_text = "Key principles: " + ", ".join([
                        p.get('principle', '') for p in principles[:3]
                    ])
                    context_summary += f" {principle_text}"
            
            # Load patterns from classification YAML (required)
            with open(framework_dir / "classification.yaml", 'r', encoding='utf-8') as f:
                classification_data = yaml.safe_load(f)
                
            # Convert violation patterns to text format for backward compatibility
            violation_patterns = classification_data.get('violation_patterns', [])
            pattern_lines = []
            for pattern in violation_patterns:
                pattern_lines.append(f"Pattern: {pattern.get('pattern', '')}")
                pattern_lines.append(f"Description: {pattern.get('description', '')}")
                indicators = pattern.get('indicators', [])
                if indicators:
                    pattern_lines.append(f"Indicators: {', '.join(indicators)}")
                related = pattern.get('related_articles', [])
                if related:
                    pattern_lines.append(f"Related Articles: {', '.join(related)}")
                pattern_lines.append("")
            
            if self.debug:
                print(f"Loaded {len(violation_patterns)} violation patterns")
            
            return {
                "articles": True,
                "context": context_summary,
                "patterns": "\n".join(pattern_lines)
            }
            
        except Exception as e:
            if self.debug:
                print(f"Error loading knowledge base for {regulation_framework}: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def _generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate a text summary of analysis results."""
        findings = results["findings"]
        config = results["config"]
        metadata = results["metadata"]
        
        # Count issues by regulation
        regulation_counts = {}
        for finding in findings:
            reg = finding.get("regulation", "Unknown")
            regulation_counts[reg] = regulation_counts.get(reg, 0) + 1
        
        summary_lines = [
            "REGULATORY COMPLIANCE ANALYSIS - SUMMARY",
            "=" * 60,
            "",
            f"Document: {results['document_name']}",
            f"Framework: {results['regulation_framework'].upper()}",
            f"Analysis Date: {results['analysis_date'][:19]}",
            f"Analysis Type: {config['analysis_type']}",
            "",
            "RESULTS:",
            f"• Total Issues: {len(findings)}",
            f"• Regulations Affected: {len(regulation_counts)}",
            f"• Document Type: {metadata.get('document_type', 'Unknown')}",
            f"• Sections Analyzed: {config['analyzed_sections']} of {config['total_sections']}",
            "",
        ]
        
        if regulation_counts:
            summary_lines.extend([
                "ISSUES BY REGULATION:",
                "-" * 30,
            ])
            for regulation, count in sorted(regulation_counts.items(), key=lambda x: x[1], reverse=True):
                summary_lines.append(f"• {regulation}: {count} issues")
        
        summary_lines.extend([
            "",
            f"Configuration: {config['model']} model, {config['preset']} preset",
            results["summary"]
        ])
        
        return "\n".join(summary_lines)

    def _analyze_with_progress(self, document_chunks: List[Dict], progressive: bool, progress_callback: Optional[callable]) -> List[Dict]:
        """Run analysis with detailed progress reporting."""
        
        if progressive:
            # Progressive analysis with progress tracking
            if progress_callback:
                progress_callback(45, "🔍 Classifying sections by risk level...", "")
            
            # Classify chunks
            analyze_chunks, skip_chunks = self.progressive_analyzer.classify_chunks(document_chunks)
            
            if progress_callback:
                progress_callback(50, "📊 Classification complete", f"{len(analyze_chunks)} to analyze, {len(skip_chunks)} to skip")
            
            all_chunk_results = []
            total_to_analyze = len(analyze_chunks)
            
            # Process chunks marked for analysis with progress
            for i, (chunk_index, chunk, _) in enumerate(analyze_chunks):
                chunk_position = chunk.get("position", f"Section {chunk_index + 1}")
                
                # Calculate progress (50% to 85% for analysis)
                analysis_progress = 50 + int((i / max(total_to_analyze, 1)) * 35)
                
                if progress_callback:
                    progress_callback(analysis_progress, f"🔍 Analyzing sections...", f"Chunk {i + 1}/{total_to_analyze}: {chunk_position}")
                
                try:
                    # Analyze this chunk
                    similar_regulations = self.progressive_analyzer.embeddings.find_similar(chunk["text"])
                    chunk_result = self.progressive_analyzer.llm.analyze_compliance(chunk, similar_regulations)
                    
                    chunk_result.update({
                        "chunk_index": chunk_index,
                        "position": chunk_position,
                        "text": chunk["text"],
                        "should_analyze": True
                    })
                    
                    all_chunk_results.append((chunk_index, chunk_result))
                    
                    # Brief progress update with results
                    issues_found = len(chunk_result.get("issues", []))
                    if progress_callback and issues_found > 0:
                        progress_callback(analysis_progress, f"⚠️ Issues found", f"Chunk {i + 1}/{total_to_analyze}: {issues_found} issues in {chunk_position}")
                    
                except Exception as e:
                    if self.debug:
                        print(f"Error analyzing chunk {i + 1}: {e}")
                    empty_result = {
                        "chunk_index": chunk_index,
                        "position": chunk_position,
                        "text": chunk["text"],
                        "issues": [],
                        "should_analyze": True
                    }
                    all_chunk_results.append((chunk_index, empty_result))
            
            # Process skipped chunks (quick)
            if progress_callback:
                progress_callback(85, "⏭️ Processing skipped sections...", f"Processing {len(skip_chunks)} skipped sections")
            
            for chunk_index, chunk, _ in skip_chunks:
                chunk_position = chunk.get("position", f"Section {chunk_index + 1}")
                skip_result = {
                    "chunk_index": chunk_index,
                    "position": chunk_position,
                    "text": chunk["text"],
                    "issues": [],
                    "should_analyze": False
                }
                all_chunk_results.append((chunk_index, skip_result))
            
            # Sort by original order and extract results
            all_chunk_results.sort(key=lambda x: x[0])
            return [result for _, result in all_chunk_results]
            
        else:
            # Batch analysis with progress tracking
            all_chunk_results = []
            total_chunks = len(document_chunks)
            
            for i, chunk in enumerate(document_chunks):
                chunk_position = chunk.get("position", f"Section {i + 1}")
                
                # Calculate progress (50% to 85% for analysis)
                analysis_progress = 50 + int((i / max(total_chunks, 1)) * 35)
                
                if progress_callback:
                    progress_callback(analysis_progress, f"🔍 Analyzing all sections...", f"Chunk {i + 1}/{total_chunks}: {chunk_position}")
                
                try:
                    # Find relevant regulations
                    similar_regulations = self.progressive_analyzer.embeddings.find_similar(chunk["text"])
                    
                    # Analyze compliance
                    chunk_result = self.progressive_analyzer.llm.analyze_compliance(chunk, similar_regulations)
                    
                    # Add chunk info to result
                    chunk_result.update({
                        "chunk_index": i,
                        "position": chunk_position,
                        "text": chunk["text"],
                        "should_analyze": True
                    })
                    
                    all_chunk_results.append(chunk_result)
                    
                    # Brief progress update with results
                    issues_found = len(chunk_result.get("issues", []))
                    if progress_callback and issues_found > 0:
                        progress_callback(analysis_progress, f"⚠️ Issues found", f"Chunk {i + 1}/{total_chunks}: {issues_found} issues found")
                    
                except Exception as e:
                    if self.debug:
                        print(f"Error analyzing chunk {i + 1}: {e}")
                    empty_result = {
                        "chunk_index": i,
                        "position": chunk_position,
                        "text": chunk["text"],
                        "issues": [],
                        "should_analyze": True
                    }
                    all_chunk_results.append(empty_result)
            
            return all_chunk_results


# Convenience functions for simple usage
def analyze_document(file_path: str, 
                    regulation_framework: str = "gdpr",
                    config: Optional[Dict[str, Any]] = None,
                    debug: bool = False) -> Dict[str, Any]:
    """
    Simple function to analyze a document.
    
    Args:
        file_path: Path to the document file
        regulation_framework: Regulation framework to use
        config: Optional configuration overrides
        debug: Enable debug output
        
    Returns:
        Analysis results dictionary
    """
    analyzer = ComplianceAnalyzer(debug=debug)
    return analyzer.analyze_document(file_path, regulation_framework, config)

def get_available_frameworks() -> List[Dict[str, str]]:
    """Get list of available regulation frameworks."""
    analyzer = ComplianceAnalyzer()
    return analyzer.get_available_frameworks()