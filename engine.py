import os
import tempfile
import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime

from utils.document_processor import DocumentProcessor
from utils.embeddings_handler import EmbeddingsHandler
from utils.llm_handler import LLMHandler
from utils.progressive_analyser import ProgressiveAnalyser
from utils.prompt_manager import PromptManager
from utils.report_generator import ReportGenerator
from config import MODELS, DEFAULT_MODEL, config

class ComplianceAnalyser:
    """Compliance analysis engine with comprehensive violation reporting."""
    
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
        self.progressive_analyser = None
        self.prompt_manager = None
        self.report_generator = None
        self.handler = None
    
    def analyse_document(self, 
                        file_path_or_content: Union[str, bytes],
                        regulation_framework: str,
                        config_dict: Optional[Dict[str, Any]] = None,
                        original_filename: Optional[str] = None,
                        progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """Analyse document for compliance issues with comprehensive violation reporting."""
        
        # Store applied configuration for results
        self.applied_config = config_dict.copy() if config_dict else {}
        
        # Apply configuration
        if config_dict:
            self._apply_config(config_dict)
        
        # Handle file input
        file_path = self._prepare_file(file_path_or_content, original_filename)
        
        try:
            # Step 1: Setup components
            self._update_progress(progress_callback, 20, "Loading knowledge base...")
            self._setup_components(regulation_framework)
            
            # Step 2: Process document  
            self._update_progress(progress_callback, 40, "Processing document...")
            document_info = self.doc_processor.process_document(file_path)
            
            # Step 3: Run analysis
            self._update_progress(progress_callback, 60, "Analysing compliance...")
            chunk_results = self._run_comprehensive_analysis(document_info["chunks"], progress_callback)
            
            # Step 4: Process results (no deduplication)
            self._update_progress(progress_callback, 90, "Processing results...")
            findings = self.report_generator.process_results(chunk_results)[0]
            
            self._update_progress(progress_callback, 100, "Complete!")
            
            return self._build_results(findings, chunk_results, document_info, 
                                     original_filename or file_path, regulation_framework)
            
        finally:
            self._cleanup_temp_file(file_path, file_path_or_content)
    
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
        
        # Setup prompt manager and handler
        self.prompt_manager = PromptManager(regulation_framework=regulation_framework)
        self.handler = self.prompt_manager.handler
        
        # Setup LLM
        model_config = MODELS[DEFAULT_MODEL]
        self.llm = LLMHandler(model_config, debug=self.debug)
        
        # Setup progressive analyser
        self.progressive_analyser = ProgressiveAnalyser(
            self.handler, self.embeddings, self.debug
        )
        
        # Setup report generator
        self.report_generator = ReportGenerator(self.debug)
    
    def _run_comprehensive_analysis(self, chunks: List[Dict], progress_callback: callable) -> List[Dict]:
        """Run analysis with comprehensive violation reporting."""
        results = []
        
        # Pre-calculate how many sections will actually be analysed
        sections_to_analyse = []
        for i, chunk in enumerate(chunks):
            chunk_text = chunk["text"]
            if self.handler.should_analyse(chunk_text):
                sections_to_analyse.append(i)
        
        total_to_analyse = len(sections_to_analyse)
        analysed_count = 0
        
        if self.debug:
            print(f"Will analyse {total_to_analyse} of {len(chunks)} total sections")
        
        for i, chunk in enumerate(chunks):
            chunk_position = chunk.get("position", f"Section {i+1}")
            chunk_text = chunk["text"]
            
            # Risk assessment
            should_analyse = self.handler.should_analyse(chunk_text)
            risk_score = self.handler.calculate_risk_score(chunk_text)
            
            if should_analyse:
                analysed_count += 1
                # Show progress as "current/total" for sections being analysed
                self._update_progress(progress_callback, 60 + (i / len(chunks)) * 25, 
                                    f"Analysing section {analysed_count}/{total_to_analyse}")
                
                # Get relevant regulations via RAG
                similar_regs = self.embeddings.find_similar(chunk_text, k=config.rag_articles)
                
                # Create framework-specific prompt
                prompt = self.handler.create_prompt(chunk_text, chunk_position, similar_regs)
                
                # Get LLM response
                response = self.llm.invoke(prompt)
                
                # Parse violations using handler with document text for context
                violations = self.handler.parse_response(response, chunk_text)
                
                if self.debug:
                    print(f"Analysed {chunk_position}: {len(violations)} violations (score: {risk_score:.1f})")
                    if violations:
                        for v in violations:
                            print(f"  - {v['issue'][:50]}... | {v['regulation']} | {v['citation'][:30]}...")
                
                results.append({
                    "position": chunk_position,
                    "text": chunk_text,
                    "issues": violations,
                    "should_analyse": True,
                    "risk_score": risk_score
                })
            else:
                if self.debug:
                    print(f"Skipped {chunk_position} (score: {risk_score:.1f})")
                
                results.append({
                    "position": chunk_position,
                    "text": chunk_text,
                    "issues": [],
                    "should_analyse": False,
                    "risk_score": risk_score
                })
        
        return results
    
    def _prepare_file(self, file_path_or_content: Union[str, bytes], original_filename: str) -> str:
        """Prepare file for processing."""
        if isinstance(file_path_or_content, bytes):
            suffix = Path(original_filename).suffix if original_filename else '.tmp'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_path_or_content)
                return tmp.name
        else:
            assert os.path.exists(file_path_or_content), f"File not found: {file_path_or_content}"
            return file_path_or_content
    
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
                "model": self.applied_config.get("model", DEFAULT_MODEL),
                "preset": self.applied_config.get("preset", "balanced"),
                "analysis_type": "Comprehensive Analysis",
                "total_sections": len(chunk_results),
                "analysed_sections": len([c for c in chunk_results if c.get("should_analyse", False)]),
                "sections_with_issues": len([c for c in chunk_results if c.get("issues", [])]),
                "rag_articles": self.applied_config.get("rag_articles", config.rag_articles),
                "chunking_method": self.applied_config.get("chunking_method", config.chunking_method)
            },
            "summary": f"Found {len(findings)} compliance violations",
            "report_generator": self.report_generator
        }
    
    def get_available_frameworks(self) -> List[Dict[str, str]]:
        """Get list of available regulation frameworks, excluding examples."""
        frameworks = []
        
        for item in self.knowledge_base_dir.iterdir():
            if item.is_dir() and item.name != "__pycache__":
                # Check for required files
                required_files = ["articles.txt", "context.yaml", "handler.py"]
                if all((item / f).exists() for f in required_files):
                    
                    try:
                        with open(item / "context.yaml", 'r') as f:
                            context = yaml.safe_load(f) or {}
                        
                        # Skip example frameworks
                        if context.get('example_only', False):
                            if self.debug:
                                print(f"Skipping example framework: {item.name}")
                            continue
                        
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
def analyse_document(file_path: str, regulation_framework: str, 
                    config_dict: Optional[Dict[str, Any]] = None, debug: bool = False) -> Dict[str, Any]:
    """Simple function to analyse a document."""
    analyser = ComplianceAnalyser(debug=debug)
    return analyser.analyse_document(file_path, regulation_framework, config_dict)

def get_available_frameworks() -> List[Dict[str, str]]:
    """Get list of available regulation frameworks."""
    analyser = ComplianceAnalyser()
    return analyser.get_available_frameworks()