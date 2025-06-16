# ui/utils/analysis_runner.py

import streamlit as st
import tempfile
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path for imports
current_dir = Path(__file__).parent.parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from utils.document_processor import DocumentProcessor
from utils.embeddings_handler import EmbeddingsHandler
from utils.llm_handler import LLMHandler
from utils.progressive_analyzer import ProgressiveAnalyzer
from utils.prompt_manager import PromptManager
from utils.report_generator import ReportGenerator
from config import MODELS, apply_preset, RAGConfig, ProgressiveConfig

def load_knowledge_base(regulation_framework: str, embeddings, debug: bool = False) -> Optional[Dict]:
    """Load knowledge base for a regulation framework."""
    try:
        knowledge_base = {}
        
        # Get paths relative to project root
        project_root = Path(__file__).parent.parent.parent
        knowledge_base_dir = project_root / "knowledge_base"
        
        articles_path = knowledge_base_dir / regulation_framework / "articles.txt"
        context_path = knowledge_base_dir / regulation_framework / "context.txt"
        patterns_path = knowledge_base_dir / regulation_framework / "common_patterns.txt"
        
        if not articles_path.exists():
            st.error(f"❌ Articles file not found for {regulation_framework}")
            return None
        
        # Load articles (required)
        if debug:
            st.info(f"Loading {regulation_framework} articles...")
        embeddings.build_knowledge_base(str(articles_path))
        knowledge_base["articles"] = True
        
        # Load context (optional)
        knowledge_base["context"] = ""
        if context_path.exists():
            with open(context_path, 'r', encoding='utf-8') as f:
                knowledge_base["context"] = f.read()
                if debug:
                    st.info(f"Loaded {regulation_framework} context")
        
        # Load patterns (optional)
        knowledge_base["patterns"] = ""
        if patterns_path.exists():
            with open(patterns_path, 'r', encoding='utf-8') as f:
                knowledge_base["patterns"] = f.read()
                pattern_count = knowledge_base["patterns"].count("Pattern:")
                if debug:
                    st.info(f"Loaded {pattern_count} violation patterns")
        
        return knowledge_base
        
    except Exception as e:
        st.error(f"❌ Error loading knowledge base: {e}")
        if debug:
            st.exception(e)
        return None

def run_compliance_analysis(uploaded_file, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Run the compliance analysis with progress tracking."""
    
    if config is None:
        st.error("❌ Configuration is required")
        return None
    
    # Apply configuration
    try:
        apply_preset(config["preset"])
        RAGConfig.ARTICLES_COUNT = config["rag_articles"]
        ProgressiveConfig.HIGH_RISK_THRESHOLD = config["risk_threshold"]
        ProgressiveConfig.ENABLED = config["enable_progressive"]
    except Exception as e:
        st.error(f"❌ Error applying configuration: {e}")
        return None
    
    # Save uploaded file temporarily
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{uploaded_file.name}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
    except Exception as e:
        st.error(f"❌ Error saving uploaded file: {e}")
        return None
    
    # Enhanced progress tracking with dynamic updates
    progress_bar = st.progress(0)
    status_text = st.empty()
    detailed_status = st.empty()
    
    try:
        # Step 1: Load knowledge base
        status_text.text("🔍 Loading knowledge base...")
        detailed_status.text("")
        progress_bar.progress(10)
        
        embeddings = EmbeddingsHandler()
        knowledge_base = load_knowledge_base(config["framework"], embeddings, config["debug_mode"])
        
        if not knowledge_base:
            return None
        
        # Step 2: Process document
        status_text.text("📄 Processing document...")
        progress_bar.progress(30)
        
        doc_processor = DocumentProcessor(chunk_size=config["chunk_size"])
        document_info = doc_processor.process_document(tmp_file_path)
        document_chunks = document_info["chunks"]
        document_metadata = document_info["metadata"]
        
        if not document_chunks:
            st.error("❌ No text extracted from document!")
            return None
        
        if config["debug_mode"]:
            st.info(f"📊 Extracted {len(document_chunks)} chunks")
        
        # Step 3: Initialize analysis components
        status_text.text("⚙️ Initializing analysis components...")
        progress_bar.progress(50)
        
        prompt_manager = PromptManager(
            regulation_framework=config["framework"],
            regulation_context=knowledge_base.get("context", ""),
            regulation_patterns=knowledge_base.get("patterns", "")
        )
        
        model_config = MODELS.get(config["model"], MODELS["small"])
        llm = LLMHandler(
            model_config=model_config, 
            prompt_manager=prompt_manager, 
            debug=config["debug_mode"]
        )
        
        # Step 4: Run analysis with detailed progress
        status_text.text("🔍 Analyzing document for compliance issues...")
        detailed_status.text("Preparing analysis...")
        progress_bar.progress(70)
        
        progressive_analyzer = ProgressiveAnalyzer(
            llm_handler=llm,
            embeddings_handler=embeddings,
            regulation_framework=config["framework"],
            batch_size=llm.get_batch_size(),
            debug=config["debug_mode"]
        )
        
        # Enhanced analysis with chunk-by-chunk progress
        total_chunks = len(document_chunks)
        
        if config["enable_progressive"]:
            if config["debug_mode"]:
                st.info("Using progressive analysis")
            detailed_status.text("Classifying sections by risk level...")
            
            # Run progressive analysis with progress updates
            all_chunk_results = run_progressive_analysis_with_progress(
                progressive_analyzer, document_chunks, total_chunks, 
                status_text, detailed_status, progress_bar
            )
        else:
            if config["debug_mode"]:
                st.info("Using standard batch analysis")
            detailed_status.text("Analyzing all sections...")
            
            # Run batch analysis with progress updates  
            all_chunk_results = run_batch_analysis_with_progress(
                progressive_analyzer, document_chunks, total_chunks,
                status_text, detailed_status, progress_bar
            )
        
        # Step 5: Process results
        status_text.text("📊 Processing results...")
        progress_bar.progress(90)
        
        report_generator = ReportGenerator(debug=config["debug_mode"])
        (deduplicated_findings,) = report_generator.process_results(all_chunk_results)
        
        # Step 6: Complete
        progress_bar.progress(100)
        status_text.text("✅ Analysis complete!")
        detailed_status.text(f"🎉 Processed {len(all_chunk_results)} sections successfully")
        
        # Prepare results
        results = {
            "findings": deduplicated_findings,
            "chunk_results": all_chunk_results,
            "metadata": document_metadata,
            "config": {
                "framework": config["framework"],
                "model": config["model"],
                "preset": config["preset"],
                "analysis_type": "Progressive" if config["enable_progressive"] else "Standard",
                "analyzed_sections": len([c for c in all_chunk_results if c.get("should_analyze", True)]),
                "total_sections": len(all_chunk_results),
                "rag_articles": config["rag_articles"],
                "risk_threshold": config["risk_threshold"]
            },
            "report_generator": report_generator  # Store for exports
        }
        
        # Clear progress indicators after a brief delay
        import time
        time.sleep(1.5)  # Let users see the completion message
        progress_bar.empty()
        status_text.empty()
        detailed_status.empty()
        
        # Show completion message
        issues_count = len(deduplicated_findings)
        if issues_count == 0:
            st.success(f"✅ Analysis complete! No compliance issues detected.")
        else:
            st.warning(f"⚠️ Analysis complete! Found {issues_count} potential compliance issues.")
        
        return results
        
    except Exception as e:
        st.error(f"❌ Analysis failed: {str(e)}")
        if config["debug_mode"]:
            st.exception(e)
        return None
        
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_file_path)
        except:
            pass
        
        # Clear progress indicators on error
        progress_bar.empty()
        status_text.empty()
        detailed_status.empty()

def run_progressive_analysis_with_progress(progressive_analyzer, document_chunks, total_chunks, 
                                         status_text, detailed_status, progress_bar):
    """Run progressive analysis with detailed progress updates."""
    
    # Step 1: Classification phase
    detailed_status.text("🔍 Classifying sections by risk level...")
    
    # Classify chunks (this is fast, so we don't need chunk-by-chunk updates)
    analyze_chunks, skip_chunks = progressive_analyzer.classify_chunks(document_chunks)
    
    analyze_count = len(analyze_chunks)
    skip_count = len(skip_chunks)
    
    detailed_status.text(f"📊 Classification complete: {analyze_count} to analyze, {skip_count} to skip")
    
    # Step 2: Analysis phase with chunk-by-chunk updates
    all_chunk_results = []
    
    # Process chunks marked for analysis
    if analyze_chunks:
        status_text.text("🔍 Analyzing high-priority sections...")
        
        for i, (chunk_index, chunk, _) in enumerate(analyze_chunks):
            chunk_position = chunk.get("position", f"Section {chunk_index + 1}")
            
            # Update progress
            progress = 70 + int((i / len(analyze_chunks)) * 15)  # 70-85% for analysis
            progress_bar.progress(progress)
            detailed_status.text(f"📄 Analyzing chunk {i + 1}/{len(analyze_chunks)}: {chunk_position}")
            
            # Analyze this chunk
            try:
                similar_regulations = progressive_analyzer.embeddings.find_similar(chunk["text"])
                chunk_result = progressive_analyzer.llm.analyze_compliance(chunk, similar_regulations)
                
                chunk_result.update({
                    "chunk_index": chunk_index,
                    "position": chunk_position,
                    "text": chunk["text"],
                    "should_analyze": True
                })
                
                all_chunk_results.append((chunk_index, chunk_result))
                
                # Show brief result
                issues_found = len(chunk_result.get("issues", []))
                if issues_found > 0:
                    detailed_status.text(f"⚠️  Chunk {i + 1}/{len(analyze_chunks)}: {issues_found} issues found in {chunk_position}")
                else:
                    detailed_status.text(f"✅ Chunk {i + 1}/{len(analyze_chunks)}: No issues in {chunk_position}")
                
            except Exception as e:
                detailed_status.text(f"❌ Error analyzing chunk {i + 1}: {str(e)[:50]}...")
                empty_result = {
                    "chunk_index": chunk_index,
                    "position": chunk_position,
                    "text": chunk["text"],
                    "issues": [],
                    "should_analyze": True
                }
                all_chunk_results.append((chunk_index, empty_result))
    
    # Process skipped chunks (quick)
    if skip_chunks:
        progress_bar.progress(85)
        detailed_status.text(f"⏭️  Processing {len(skip_chunks)} skipped sections...")
        
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

def run_batch_analysis_with_progress(progressive_analyzer, document_chunks, total_chunks,
                                   status_text, detailed_status, progress_bar):
    """Run batch analysis with detailed progress updates."""
    
    all_chunk_results = []
    batch_size = progressive_analyzer.batch_size
    
    # Process in batches for better efficiency
    for batch_start in range(0, len(document_chunks), batch_size):
        batch_end = min(batch_start + batch_size, len(document_chunks))
        batch = document_chunks[batch_start:batch_end]
        
        # Update batch progress
        batch_num = batch_start // batch_size + 1
        total_batches = (len(document_chunks) + batch_size - 1) // batch_size
        batch_progress = 70 + int((batch_start / len(document_chunks)) * 15)  # 70-85%
        progress_bar.progress(batch_progress)
        
        status_text.text(f"🔍 Processing batch {batch_num}/{total_batches}")
        detailed_status.text(f"📦 Batch {batch_num}: chunks {batch_start + 1}-{batch_end} of {total_chunks}")
        
        # Process each chunk in the batch
        for chunk_index, chunk in enumerate(batch):
            current_chunk_index = batch_start + chunk_index
            chunk_position = chunk.get("position", f"Section {current_chunk_index + 1}")
            
            # Update individual chunk progress
            detailed_status.text(f"📄 Analyzing chunk {current_chunk_index + 1}/{total_chunks}: {chunk_position}")
            
            try:
                # Find relevant regulations
                similar_regulations = progressive_analyzer.embeddings.find_similar(chunk["text"])
                
                # Analyze compliance
                chunk_result = progressive_analyzer.llm.analyze_compliance(chunk, similar_regulations)
                
                # Add chunk info to result
                chunk_result.update({
                    "chunk_index": current_chunk_index,
                    "position": chunk_position,
                    "text": chunk["text"],
                    "should_analyze": True
                })
                
                all_chunk_results.append(chunk_result)
                
                # Show brief result
                issues_found = len(chunk_result.get("issues", []))
                if issues_found > 0:
                    detailed_status.text(f"⚠️  Chunk {current_chunk_index + 1}/{total_chunks}: {issues_found} issues found")
                
            except Exception as e:
                detailed_status.text(f"❌ Error in chunk {current_chunk_index + 1}: {str(e)[:50]}...")
                empty_result = {
                    "chunk_index": current_chunk_index,
                    "position": chunk_position,
                    "text": chunk["text"],
                    "issues": [],
                    "should_analyze": True
                }
                all_chunk_results.append(empty_result)
    
    return all_chunk_results

def validate_configuration(config: Dict[str, Any]) -> bool:
    """Validate the analysis configuration."""
    required_fields = ["framework", "model", "preset", "enable_progressive", "rag_articles", "risk_threshold"]
    
    for field in required_fields:
        if field not in config:
            st.error(f"❌ Missing configuration field: {field}")
            return False
    
    # Validate model exists
    if config["model"] not in MODELS:
        st.error(f"❌ Invalid model: {config['model']}")
        return False
    
    # Validate ranges
    if not (1 <= config["rag_articles"] <= 10):
        st.error("❌ RAG articles count must be between 1 and 10")
        return False
    
    if not (1 <= config["risk_threshold"] <= 20):
        st.error("❌ Risk threshold must be between 1 and 20")
        return False
    
    return True