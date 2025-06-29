# engine.py - Truly Framework Agnostic Compliance Analysis Engine

"""
Central analysis engine for regulatory compliance analysis.
Handles all document processing, knowledge base loading, and LLM analysis.
FRAMEWORK AGNOSTIC - No hardcoded regulation references.
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
    Main compliance analysis engine - completely framework agnostic.
    Works with any regulatory framework that follows the required structure.
    """
    
    def __init__(self, debug: bool = False):
        """Initialize the compliance analyzer."""
        self.debug = debug
        self.knowledge_base_dir = self._get_knowledge_base_dir()
        
        # Validate critical configuration
        self._validate_configuration()
        
        # Initialize components (will be set up during analysis)
        self.doc_processor = None
        self.embeddings = None
        self.llm = None
        self.progressive_analyzer = None
        self.prompt_manager = None
        self.report_generator = None
    
    def _validate_configuration(self):
        """Validate critical configuration before starting."""
        # Check knowledge base directory exists
        if not self.knowledge_base_dir.exists():
            raise FileNotFoundError(
                f"Knowledge base directory not found: {self.knowledge_base_dir}\n"
                f"Expected: A 'knowledge_base' directory with regulatory frameworks"
            )
        
        # Check default model exists
        if DEFAULT_MODEL not in MODELS:
            available_models = list(MODELS.keys())
            raise ValueError(
                f"Default model '{DEFAULT_MODEL}' not found in MODELS configuration.\n"
                f"Available models: {available_models}"
            )
        
        # Check performance presets exist
        if 'balanced' not in PERFORMANCE_PRESETS:
            available_presets = list(PERFORMANCE_PRESETS.keys())
            raise ValueError(
                f"Default preset 'balanced' not found in PERFORMANCE_PRESETS.\n"
                f"Available presets: {available_presets}"
            )
    
    def analyze_document(self, 
                        file_path_or_content: Union[str, bytes],
                        regulation_framework: str,  # NO DEFAULT - Framework agnostic!
                        config: Optional[Dict[str, Any]] = None,
                        original_filename: Optional[str] = None,
                        progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        Analyze a document for compliance issues - works with ANY regulatory framework.
        
        Args:
            file_path_or_content: Path to file or file content (bytes)
            regulation_framework: Regulation framework to use (e.g., 'gdpr', 'hipaa', 'food_safety')
            config: Analysis configuration
            original_filename: Original filename (for extension detection when using bytes)
            progress_callback: Optional function to call with progress updates (progress, status, details)
            
        Returns:
            Dictionary with analysis results
        """
        
        # Validate inputs - framework agnostic validation
        if not regulation_framework:
            raise ValueError("regulation_framework cannot be empty")
        
        if not isinstance(regulation_framework, str):
            raise ValueError("regulation_framework must be a string")
        
        if isinstance(file_path_or_content, str) and not file_path_or_content.strip():
            raise ValueError("file_path_or_content cannot be empty")
        
        if isinstance(file_path_or_content, bytes) and len(file_path_or_content) == 0:
            raise ValueError("file_path_or_content cannot be empty")
        
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
                raise ValueError(f"No text content could be extracted from the document: {original_filename or file_path}")
            
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
            if not model_config:
                available_models = list(MODELS.keys())
                raise ValueError(f"Model '{config.get('model')}' not found. Available: {available_models}")
            
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
            
            # Provide more context for common errors
            if "No text content" in str(e):
                raise ValueError(f"Document processing failed: {e}. Check if the file is readable and contains text.")
            elif "knowledge base" in str(e).lower():
                raise RuntimeError(f"Knowledge base error: {e}. Check that {regulation_framework} framework is properly configured.")
            else:
                raise RuntimeError(f"Analysis failed: {e}")
            
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
        if not results:
            raise ValueError("Results dictionary cannot be empty")
        
        if not export_path:
            raise ValueError("Export path cannot be empty")
        
        if report_type not in ["detailed", "summary", "json"]:
            raise ValueError(f"Invalid report_type: {report_type}. Must be 'detailed', 'summary', or 'json'")
        
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
            raise RuntimeError(f"Failed to export {report_type} report to {export_path}: {e}")
    
    def get_available_frameworks(self) -> List[Dict[str, str]]:
        """Get list of available regulation frameworks - completely dynamic."""
        try:
            index_path = self.knowledge_base_dir / "regulation_index.json"
            
            if index_path.exists():
                with open(index_path, 'r') as f:
                    index_data = json.load(f)
                    frameworks = index_data.get("frameworks", [])
                    if not frameworks:
                        raise ValueError("regulation_index.json exists but contains no frameworks")
                    return frameworks
            else:
                # Scan directories and check for required files
                frameworks = []
                
                if not self.knowledge_base_dir.exists():
                    raise FileNotFoundError(f"Knowledge base directory does not exist: {self.knowledge_base_dir}")
                
                framework_dirs = [item for item in self.knowledge_base_dir.iterdir() 
                                if item.is_dir() and item.name != "__pycache__"]
                
                if not framework_dirs:
                    raise ValueError(f"No framework directories found in {self.knowledge_base_dir}")
                
                for item in framework_dirs:
                    framework_id = item.name
                    if self.debug:
                        print(f"Checking framework: {framework_id}")
                    
                    try:
                        # Validate this specific framework
                        validation = self.validate_framework(framework_id)
                        
                        if validation["valid"]:
                            # Try to get name and description from context.yaml
                            name = framework_id.upper()
                            description = f"{name} compliance framework"
                            
                            try:
                                context_path = item / "context.yaml"
                                if context_path.exists():
                                    with open(context_path, 'r', encoding='utf-8') as f:
                                        context_data = yaml.safe_load(f)
                                        if context_data:  # Check if YAML loaded successfully
                                            name = context_data.get('name', name)
                                            description = context_data.get('description', description)
                            except Exception as yaml_error:
                                if self.debug:
                                    print(f"Warning: Could not read context.yaml for {framework_id}: {yaml_error}")
                                # Continue with defaults
                            
                            frameworks.append({
                                "id": framework_id,
                                "name": name,
                                "description": description
                            })
                            
                            if self.debug:
                                print(f"✅ Added framework: {framework_id}")
                        else:
                            if self.debug:
                                missing = validation.get("missing_files", [])
                                print(f"❌ Skipping incomplete framework {framework_id}. Missing: {missing}")
                    
                    except Exception as framework_error:
                        if self.debug:
                            print(f"❌ Error processing framework {framework_id}: {framework_error}")
                        # Continue to next framework instead of failing
                        continue
                
                if not frameworks:
                    checked_dirs = [d.name for d in framework_dirs]
                    raise ValueError(
                        f"No valid frameworks found in {len(framework_dirs)} directories: {checked_dirs}\n"
                        f"Each framework needs: articles.txt, classification.yaml, context.yaml, handler.py"
                    )
                
                if self.debug:
                    print(f"Found {len(frameworks)} valid frameworks: {[f['id'] for f in frameworks]}")
                
                return frameworks
                
        except Exception as e:
            if self.debug:
                import traceback
                traceback.print_exc()
            raise RuntimeError(f"Failed to load regulatory frameworks: {e}")
    
    def validate_framework(self, framework_id: str) -> Dict[str, Any]:
        """Validate that a regulation framework has all required files."""
        if not framework_id:
            raise ValueError("framework_id cannot be empty")
        
        framework_dir = self.knowledge_base_dir / framework_id
        
        # Core required files (handler.py is most critical)
        critical_files = [
            "articles.txt",
            "classification.yaml", 
            "context.yaml",
            "handler.py"
        ]
        
        # Optional files that won't cause validation failure
        optional_files = [
            "README.md"
        ]
        
        validation = {
            "framework_id": framework_id,
            "valid": True,
            "missing_files": [],
            "missing_optional": [],
            "warnings": []
        }
        
        # Check if directory exists
        if not framework_dir.exists():
            validation["valid"] = False
            validation["missing_files"] = critical_files + optional_files
            return validation
        
        try:
            # Check critical files
            for filename in critical_files:
                file_path = framework_dir / filename
                if not file_path.exists():
                    validation["missing_files"].append(filename)
                    validation["valid"] = False
                elif file_path.stat().st_size == 0:
                    validation["warnings"].append(f"{filename} is empty")
            
            # Check optional files
            for filename in optional_files:
                if not (framework_dir / filename).exists():
                    validation["missing_optional"].append(filename)
            
            # Additional validation: try to load YAML files if they exist
            yaml_files = ["classification.yaml", "context.yaml"]
            for yaml_file in yaml_files:
                yaml_path = framework_dir / yaml_file
                if yaml_path.exists():
                    try:
                        with open(yaml_path, 'r', encoding='utf-8') as f:
                            data = yaml.safe_load(f)
                            if not data:
                                validation["warnings"].append(f"{yaml_file} is empty or invalid")
                    except Exception as yaml_error:
                        validation["warnings"].append(f"{yaml_file} has YAML syntax errors: {yaml_error}")
                        # Don't mark as invalid for YAML syntax errors, just warn
            
            # Try to validate handler.py
            handler_path = framework_dir / "handler.py"
            if handler_path.exists():
                try:
                    # Basic syntax check - try to read the file
                    with open(handler_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if "class RegulationHandler" not in content:
                            validation["warnings"].append("handler.py missing RegulationHandler class")
                except Exception as handler_error:
                    validation["warnings"].append(f"handler.py has issues: {handler_error}")
            
        except Exception as e:
            if self.debug:
                print(f"Error validating framework {framework_id}: {e}")
            validation["valid"] = False
            validation["warnings"].append(f"Validation error: {e}")
        
        if self.debug and not validation["valid"]:
            print(f"Framework {framework_id} validation failed. Missing: {validation['missing_files']}")
        elif self.debug and validation["warnings"]:
            print(f"Framework {framework_id} has warnings: {validation['warnings']}")
        
        return validation
    
    def get_first_available_framework(self) -> str:
        """Get the first available framework for use as a dynamic default."""
        try:
            frameworks = self.get_available_frameworks()
            if not frameworks:
                raise ValueError("No frameworks available")
            return frameworks[0]['id']
        except Exception as e:
            raise RuntimeError(f"Cannot determine available framework: {e}")
    
    def _get_knowledge_base_dir(self) -> Path:
        """Get the knowledge base directory path."""
        script_dir = Path(__file__).parent
        return script_dir / "knowledge_base"
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default analysis configuration with validation."""
        # Validate defaults exist before using them
        if DEFAULT_MODEL not in MODELS:
            available_models = list(MODELS.keys())
            raise ValueError(f"Default model '{DEFAULT_MODEL}' not found. Available: {available_models}")
        
        if 'balanced' not in PERFORMANCE_PRESETS:
            available_presets = list(PERFORMANCE_PRESETS.keys())
            raise ValueError(f"Default preset 'balanced' not found. Available: {available_presets}")
        
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
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")
        
        # Apply preset if specified
        preset = config.get('preset')
        if preset:
            if preset not in PERFORMANCE_PRESETS:
                available_presets = list(PERFORMANCE_PRESETS.keys())
                raise ValueError(f"Unknown preset '{preset}'. Available: {available_presets}")
            
            preset_config = apply_preset(preset)
            if self.debug:
                print(f"Applied preset '{preset}': {preset_config}")
        
        # Apply individual overrides with validation
        if 'rag_articles' in config:
            rag_articles = config['rag_articles']
            if not isinstance(rag_articles, int) or rag_articles < 1 or rag_articles > 20:
                raise ValueError("rag_articles must be an integer between 1 and 20")
            RAGConfig.ARTICLES_COUNT = rag_articles
        
        if 'risk_threshold' in config:
            risk_threshold = config['risk_threshold']
            if not isinstance(risk_threshold, int) or risk_threshold < 1 or risk_threshold > 50:
                raise ValueError("risk_threshold must be an integer between 1 and 50")
            ProgressiveConfig.HIGH_RISK_THRESHOLD = risk_threshold
        
        if 'progressive_enabled' in config:
            progressive_enabled = config['progressive_enabled']
            if not isinstance(progressive_enabled, bool):
                raise ValueError("progressive_enabled must be a boolean")
            ProgressiveConfig.ENABLED = progressive_enabled
    
    def _load_knowledge_base(self, regulation_framework: str) -> Dict[str, Any]:
        """Load knowledge base from required YAML files with proper error handling."""
        if not regulation_framework:
            raise ValueError("regulation_framework cannot be empty")
        
        framework_dir = self.knowledge_base_dir / regulation_framework
        
        if not framework_dir.exists():
            available_frameworks = [d.name for d in self.knowledge_base_dir.iterdir() 
                                  if d.is_dir() and d.name != "__pycache__"]
            raise FileNotFoundError(
                f"Framework directory not found: {framework_dir}\n"
                f"Available frameworks: {available_frameworks}"
            )
        
        # Check required files
        required_files = {
            "articles.txt": "Regulation articles for RAG",
            "classification.yaml": "Terms for progressive analysis", 
            "context.yaml": "Framework metadata"
        }
        
        missing_files = []
        for filename, description in required_files.items():
            file_path = framework_dir / filename
            if not file_path.exists():
                missing_files.append(f"{filename} ({description})")
            elif file_path.stat().st_size == 0:
                missing_files.append(f"{filename} (file is empty)")
        
        if missing_files:
            raise FileNotFoundError(
                f"Framework {regulation_framework} missing required files:\n" +
                "\n".join(f"  - {f}" for f in missing_files)
            )
        
        try:
            if self.debug:
                print(f"Loading knowledge base from {framework_dir}")
            
            # Load articles (required)
            articles_path = framework_dir / "articles.txt"
            self.embeddings.build_knowledge_base(str(articles_path))
            
            # Load context from YAML (required)
            try:
                with open(framework_dir / "context.yaml", 'r', encoding='utf-8') as f:
                    context_data = yaml.safe_load(f)
                    if not context_data:
                        raise ValueError("context.yaml is empty or invalid")
                    
                    context_summary = context_data.get('description', '')
                    
                    # Add key principles if available
                    principles = context_data.get('key_principles', [])
                    if principles:
                        principle_text = "Key principles: " + ", ".join([
                            p.get('principle', '') for p in principles[:3]
                        ])
                        context_summary += f" {principle_text}"
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML syntax in context.yaml: {e}")
            
            # Load patterns from classification YAML (required)
            try:
                with open(framework_dir / "classification.yaml", 'r', encoding='utf-8') as f:
                    classification_data = yaml.safe_load(f)
                    if not classification_data:
                        raise ValueError("classification.yaml is empty or invalid")
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML syntax in classification.yaml: {e}")
            
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
                import traceback
                traceback.print_exc()
            raise RuntimeError(f"Failed to load knowledge base for {regulation_framework}: {e}")
    
    def _generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate a text summary of analysis results."""
        if not results:
            raise ValueError("Results dictionary cannot be empty")
        
        findings = results.get("findings", [])
        config = results.get("config", {})
        metadata = results.get("metadata", {})
        
        # Count issues by regulation
        regulation_counts = {}
        for finding in findings:
            reg = finding.get("regulation", "Unknown")
            regulation_counts[reg] = regulation_counts.get(reg, 0) + 1
        
        summary_lines = [
            "REGULATORY COMPLIANCE ANALYSIS - SUMMARY",
            "=" * 60,
            "",
            f"Document: {results.get('document_name', 'Unknown')}",
            f"Framework: {results.get('regulation_framework', 'Unknown').upper()}",
            f"Analysis Date: {results.get('analysis_date', 'Unknown')[:19]}",
            f"Analysis Type: {config.get('analysis_type', 'Unknown')}",
            "",
            "RESULTS:",
            f"• Total Issues: {len(findings)}",
            f"• Regulations Affected: {len(regulation_counts)}",
            f"• Document Type: {metadata.get('document_type', 'Unknown')}",
            f"• Sections Analyzed: {config.get('analyzed_sections', 'Unknown')} of {config.get('total_sections', 'Unknown')}",
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
            f"Configuration: {config.get('model', 'Unknown')} model, {config.get('preset', 'Unknown')} preset",
            results.get("summary", "Analysis complete")
        ])
        
        return "\n".join(summary_lines)

    def _analyze_with_progress(self, document_chunks: List[Dict], progressive: bool, progress_callback: Optional[callable]) -> List[Dict]:
        """Run analysis with detailed progress reporting."""
        
        if not document_chunks:
            raise ValueError("document_chunks cannot be empty")
        
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
                    error_msg = f"Error analyzing chunk {i + 1} ({chunk_position}): {e}"
                    if self.debug:
                        print(error_msg)
                    raise RuntimeError(error_msg)
            
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
                    error_msg = f"Error analyzing chunk {i + 1} ({chunk_position}): {e}"
                    if self.debug:
                        print(error_msg)
                    raise RuntimeError(error_msg)
            
            return all_chunk_results


# Convenience functions for simple usage - NOW FRAMEWORK AGNOSTIC
def analyze_document(file_path: str, 
                    regulation_framework: str,  # NO DEFAULT! Must be specified
                    config: Optional[Dict[str, Any]] = None,
                    debug: bool = False) -> Dict[str, Any]:
    """
    Simple function to analyze a document - FRAMEWORK AGNOSTIC.
    
    Args:
        file_path: Path to the document file
        regulation_framework: Regulation framework to use (REQUIRED - no default)
        config: Optional configuration overrides
        debug: Enable debug output
        
    Returns:
        Analysis results dictionary
    """
    if not file_path:
        raise ValueError("file_path cannot be empty")
    
    if not regulation_framework:
        raise ValueError("regulation_framework is required and cannot be empty")
    
    analyzer = ComplianceAnalyzer(debug=debug)
    return analyzer.analyze_document(file_path, regulation_framework, config)

def get_available_frameworks() -> List[Dict[str, str]]:
    """Get list of available regulation frameworks - completely dynamic."""
    analyzer = ComplianceAnalyzer()
    return analyzer.get_available_frameworks()

def get_first_available_framework() -> str:
    """Get the first available framework as a dynamic default."""
    analyzer = ComplianceAnalyzer()
    return analyzer.get_first_available_framework()