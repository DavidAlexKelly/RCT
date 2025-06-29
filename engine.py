# engine.py - Simplified Engine (674 → 200 lines)

import os
import tempfile
import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime

from utils.document_processor import DocumentProcessor
from utils.embeddings_handler import EmbeddingsHandler
from utils.llm_handler import LLMHandler
from utils.progressive_analyzer import ProgressiveAnalyzer
from utils.prompt_manager import PromptManager
from utils.report_generator import ReportGenerator
from config import MODELS, DEFAULT_MODEL, apply_preset, config

class ComplianceAnalyzer:
    """Framework-agnostic compliance analysis engine."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.knowledge_base_dir = Path(__file__).parent / "knowledge_base"
        assert self.knowledge_base_dir.exists(), f"Knowledge base not found: {self.knowledge_base_dir}"
        
        # Store applied configuration for results
        self.applied_config = {}
        
        # Components initialized during analysis
        self.doc_processor = None
        self.embeddings = None
        self.llm = None
        self.progressive_analyzer = None
        self.prompt_manager = None
        self.report_generator = None
    
    def analyze_document(self, 
                        file_path_or_content: Union[str, bytes],
                        regulation_framework: str,
                        config_dict: Optional[Dict[str, Any]] = None,
                        original_filename: Optional[str] = None,
                        progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """Analyze document for compliance issues."""
        
        # Apply configuration
        if config_dict:
            self._apply_config(config_dict)
        else:
            # Set defaults if no config provided
            self.applied_config = {
                'model': DEFAULT_MODEL,
                'preset': 'balanced',
                'progressive_enabled': True,
                'rag_articles': config.rag_articles,
                'risk_threshold': config.high_risk_threshold,
                'chunking_method': config.chunking_method,
                'chunk_size': config.chunk_size,
                'chunk_overlap': config.chunk_overlap
            }
        
        # Handle file input
        file_path = self._prepare_file(file_path_or_content, original_filename)
        
        try:
            # Step 1: Load knowledge base
            self._update_progress(progress_callback, 20, "Loading knowledge base...")
            self._setup_components(regulation_framework)
            
            # Step 2: Process document  
            self._update_progress(progress_callback, 40, "Processing document...")
            document_info = self.doc_processor.process_document(file_path)
            
            # Step 3: Run analysis
            self._update_progress(progress_callback, 60, "Analyzing compliance...")
            chunk_results = self._run_analysis(document_info["chunks"], progress_callback)
            
            # Step 4: Process results
            self._update_progress(progress_callback, 90, "Processing results...")
            findings = self.report_generator.process_results(chunk_results)[0]
            
            self._update_progress(progress_callback, 100, "Complete!")
            
            return self._build_results(findings, chunk_results, document_info, 
                                     original_filename or file_path, regulation_framework)
            
        finally:
            self._cleanup_temp_file(file_path, file_path_or_content)
    
    def _prepare_file(self, file_path_or_content: Union[str, bytes], original_filename: str) -> str:
        """Prepare file for processing, handling both paths and bytes."""
        if isinstance(file_path_or_content, bytes):
            # Create temp file from bytes
            suffix = Path(original_filename).suffix if original_filename else '.tmp'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_path_or_content)
                return tmp.name
        else:
            # Use provided path
            assert os.path.exists(file_path_or_content), f"File not found: {file_path_or_content}"
            return file_path_or_content
    
    def _setup_components(self, regulation_framework: str):
        """Initialize all analysis components."""
        # Setup embeddings and load knowledge base
        self.embeddings = EmbeddingsHandler()
        self._load_knowledge_base(regulation_framework)
        
        # Setup document processor
        self.doc_processor = DocumentProcessor(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            chunking_method=config.chunking_method
        )
        
        # Setup prompt manager and LLM
        self.prompt_manager = PromptManager(
            regulation_framework=regulation_framework,
            regulation_context="",
            regulation_patterns=""
        )
        
        model_config = MODELS[DEFAULT_MODEL]
        self.llm = LLMHandler(model_config, self.prompt_manager, self.debug)
        
        # Setup progressive analyzer
        self.progressive_analyzer = ProgressiveAnalyzer(
            self.llm, self.embeddings, regulation_framework, 
            model_config["batch_size"], self.debug
        )
        
        # Setup report generator
        self.report_generator = ReportGenerator(self.debug)
    
    def _run_analysis(self, chunks: List[Dict], progress_callback: callable) -> List[Dict]:
        """Run progressive or batch analysis on document chunks."""
        if config.progressive_enabled:
            return self._run_progressive_analysis(chunks, progress_callback)
        else:
            return self._run_batch_analysis(chunks, progress_callback)
    
    def _run_progressive_analysis(self, chunks: List[Dict], progress_callback: callable) -> List[Dict]:
        """Run progressive analysis with smart filtering."""
        analyze_chunks, skip_chunks = self.progressive_analyzer.classify_chunks(chunks)
        
        results = []
        total = len(analyze_chunks)
        
        # Analyze high-risk chunks
        for i, (chunk_index, chunk, _) in enumerate(analyze_chunks):
            self._update_progress(progress_callback, 60 + (i / total) * 25, f"Analyzing chunk {i+1}/{total}")
            
            similar_regs = self.embeddings.find_similar(chunk["text"])
            result = self.llm.analyze_compliance(chunk, similar_regs)
            result.update({
                "chunk_index": chunk_index,
                "position": chunk.get("position", f"Section {chunk_index + 1}"),
                "should_analyze": True
            })
            results.append((chunk_index, result))
        
        # Add skipped chunks
        for chunk_index, chunk, _ in skip_chunks:
            result = {
                "chunk_index": chunk_index,
                "position": chunk.get("position", f"Section {chunk_index + 1}"),
                "text": chunk["text"],
                "issues": [],
                "should_analyze": False
            }
            results.append((chunk_index, result))
        
        # Sort and return
        results.sort(key=lambda x: x[0])
        return [r[1] for r in results]
    
    def _run_batch_analysis(self, chunks: List[Dict], progress_callback: callable) -> List[Dict]:
        """Run batch analysis on all chunks."""
        results = []
        
        for i, chunk in enumerate(chunks):
            self._update_progress(progress_callback, 60 + (i / len(chunks)) * 25, 
                                f"Analyzing chunk {i+1}/{len(chunks)}")
            
            similar_regs = self.embeddings.find_similar(chunk["text"])
            result = self.llm.analyze_compliance(chunk, similar_regs)
            result.update({
                "chunk_index": i,
                "position": chunk.get("position", f"Section {i + 1}"),
                "should_analyze": True
            })
            results.append(result)
        
        return results
    
    def _load_knowledge_base(self, regulation_framework: str):
        """Load knowledge base for the specified framework."""
        framework_dir = self.knowledge_base_dir / regulation_framework
        assert framework_dir.exists(), f"Framework not found: {regulation_framework}"
        
        articles_path = framework_dir / "articles.txt"
        assert articles_path.exists(), f"Articles file not found: {articles_path}"
        
        self.embeddings.build_knowledge_base(str(articles_path))
    
    def _build_results(self, findings: List[Dict], chunk_results: List[Dict], 
                      document_info: Dict, document_name: str, framework: str) -> Dict[str, Any]:
        """Build final results dictionary."""
        return {
            "document_name": os.path.basename(document_name),
            "regulation_framework": framework,
            "analysis_date": datetime.now().isoformat(),
            "findings": findings,
            "chunk_results": chunk_results,
            "metadata": document_info["metadata"],
            "config": {
                "framework": framework,
                "model": self.applied_config.get('model', DEFAULT_MODEL),
                "preset": self.applied_config.get('preset', 'balanced'),
                "analysis_type": "Progressive" if self.applied_config.get('progressive_enabled', True) else "Standard",
                "analyzed_sections": len([c for c in chunk_results if c.get("should_analyze", True)]),
                "total_sections": len(chunk_results),
                "rag_articles": self.applied_config.get('rag_articles', config.rag_articles),
                "risk_threshold": self.applied_config.get('risk_threshold', config.high_risk_threshold),
                "chunking_method": self.applied_config.get('chunking_method', config.chunking_method),
                "chunk_size": self.applied_config.get('chunk_size', config.chunk_size),
                "chunk_overlap": self.applied_config.get('chunk_overlap', config.chunk_overlap)
            },
            "summary": f"Found {len(findings)} potential compliance issues",
            "report_generator": self.report_generator
        }
    
    def get_available_frameworks(self) -> List[Dict[str, str]]:
        """Get list of available regulation frameworks."""
        frameworks = []
        
        for item in self.knowledge_base_dir.iterdir():
            if item.is_dir() and item.name != "__pycache__":
                # Check for required files
                required_files = ["articles.txt", "classification.yaml", "context.yaml", "handler.py"]
                if all((item / f).exists() for f in required_files):
                    
                    # Get name and description from context
                    try:
                        with open(item / "context.yaml", 'r') as f:
                            context = yaml.safe_load(f) or {}
                        name = context.get('name', item.name.upper())
                        description = context.get('description', f"{name} compliance framework")
                    except:
                        name = item.name.upper()
                        description = f"{name} compliance framework"
                    
                    frameworks.append({
                        "id": item.name,
                        "name": name,
                        "description": description
                    })
        
        return frameworks
    
    def _apply_config(self, config_dict: Dict[str, Any]):
        """Apply configuration settings."""
        # Store the config for later use in results
        self.applied_config = config_dict.copy()
        
        if 'preset' in config_dict:
            apply_preset(config_dict['preset'])
        
        # Apply individual overrides
        for key, value in config_dict.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    def _update_progress(self, callback: callable, percent: int, message: str):
        """Update progress if callback provided."""
        if callback:
            callback(percent, message, "")
    
    def _cleanup_temp_file(self, file_path: str, original_input: Union[str, bytes]):
        """Clean up temporary file if it was created."""
        if isinstance(original_input, bytes) and os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except:
                pass

# Convenience functions
def analyze_document(file_path: str, regulation_framework: str, 
                    config_dict: Optional[Dict[str, Any]] = None, debug: bool = False) -> Dict[str, Any]:
    """Simple function to analyze a document."""
    analyzer = ComplianceAnalyzer(debug=debug)
    return analyzer.analyze_document(file_path, regulation_framework, config_dict)

def get_available_frameworks() -> List[Dict[str, str]]:
    """Get list of available regulation frameworks."""
    analyzer = ComplianceAnalyzer()
    return analyzer.get_available_frameworks()