# utils/progressive_analyzer.py - Proper error handling without fallbacks

import re
from typing import List, Dict, Any, Tuple
from config import ProgressiveConfig, DocumentConfig

class ProgressiveAnalyzer:
    """Progressive analysis using handler classification terms with proper error handling."""
    
    def __init__(self, llm_handler, embeddings_handler, regulation_framework, batch_size=1, debug=False):
        """Initialize progressive analyzer with comprehensive validation."""
        
        # Validate required parameters
        if not llm_handler:
            raise ValueError("llm_handler cannot be None")
        
        if not embeddings_handler:
            raise ValueError("embeddings_handler cannot be None")
        
        if not regulation_framework:
            raise ValueError("regulation_framework cannot be empty")
        
        if not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        
        self.llm = llm_handler
        self.embeddings = embeddings_handler
        self.regulation_framework = regulation_framework
        self.batch_size = batch_size
        self.debug = debug
        
        # Validate LLM handler has required components
        if not hasattr(self.llm, 'prompt_manager') or not self.llm.prompt_manager:
            raise ValueError("LLM handler missing prompt_manager")
        
        if not hasattr(self.llm.prompt_manager, 'regulation_handler') or not self.llm.prompt_manager.regulation_handler:
            raise ValueError("Prompt manager missing regulation_handler")
        
        # Get terms from regulation handler with validation
        handler = self.llm.prompt_manager.regulation_handler
        
        # Validate handler has required methods
        required_methods = ['get_classification_terms']
        for method in required_methods:
            if not hasattr(handler, method):
                raise ValueError(f"Regulation handler missing required method: {method}")
        
        try:
            self.data_terms = handler.get_classification_terms("data_terms")
            self.regulatory_keywords = handler.get_classification_terms("regulatory_keywords")
            self.high_risk_patterns = handler.get_classification_terms("high_risk_patterns")
            self.priority_keywords = handler.get_classification_terms("priority_keywords")
        except Exception as e:
            raise RuntimeError(f"Failed to load classification terms from handler: {e}")
        
        # Validate that we got meaningful terms
        if not self.data_terms:
            raise ValueError(f"No data_terms found for framework {regulation_framework}")
        
        if not self.regulatory_keywords:
            raise ValueError(f"No regulatory_keywords found for framework {regulation_framework}")
        
        if not self.high_risk_patterns:
            raise ValueError(f"No high_risk_patterns found for framework {regulation_framework}")
        
        if not self.priority_keywords:
            raise ValueError(f"No priority_keywords found for framework {regulation_framework}")
        
        if self.debug:
            print(f"Loaded classification terms for {regulation_framework}:")
            print(f"  - {len(self.data_terms)} data terms")
            print(f"  - {len(self.regulatory_keywords)} regulatory keywords")
            print(f"  - {len(self.high_risk_patterns)} high risk patterns")
            print(f"  - {len(self.priority_keywords)} priority keywords")
    
    def analyze(self, document_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze with progressive classification and proper error handling."""
        
        # Validate input
        if not document_chunks:
            raise ValueError("document_chunks cannot be empty")
        
        if not isinstance(document_chunks, list):
            raise ValueError("document_chunks must be a list")
        
        # Validate chunk structure
        for i, chunk in enumerate(document_chunks):
            if not isinstance(chunk, dict):
                raise ValueError(f"Chunk {i+1} must be a dictionary")
            
            if not chunk.get("text", "").strip():
                raise ValueError(f"Chunk {i+1} missing text content")
        
        # Check if progressive analysis is enabled
        if not ProgressiveConfig.ENABLED:
            if self.debug:
                print("Progressive analysis disabled, using batch analysis")
            return self.analyze_batch(document_chunks)
        
        try:
            analyze_chunks, skip_chunks = self.classify_chunks(document_chunks)
            
            if self.debug:
                print(f"Progressive classification: {len(analyze_chunks)} to analyze, {len(skip_chunks)} to skip")
            
            all_results = []
            all_results.extend(self.process_chunks(analyze_chunks, should_analyze=True))
            all_results.extend(self.process_chunks(skip_chunks, should_analyze=False))
            
            # Sort by original chunk index
            all_results.sort(key=lambda x: x.get("chunk_index", 0))
            
            return all_results
            
        except Exception as e:
            raise RuntimeError(f"Progressive analysis failed: {e}")
    
    def analyze_batch(self, document_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze all chunks without classification with proper error handling."""
        
        if not document_chunks:
            raise ValueError("document_chunks cannot be empty")
        
        all_results = []
        
        # Apply document limits
        max_chunks = DocumentConfig.MAX_CHUNKS_PER_DOCUMENT
        if len(document_chunks) > max_chunks:
            if self.debug:
                print(f"Limiting analysis to {max_chunks} chunks (was {len(document_chunks)})")
            document_chunks = document_chunks[:max_chunks]
        
        for i, chunk in enumerate(document_chunks):
            chunk_position = chunk.get("position", f"Section {i+1}")
            
            if self.debug:
                print(f"\nCHUNK {i+1}/{len(document_chunks)}: {chunk_position}")
            
            try:
                # Validate embeddings handler is ready
                if not hasattr(self.embeddings, 'find_similar'):
                    raise RuntimeError("Embeddings handler not properly initialized")
                
                similar_regulations = self.embeddings.find_similar(chunk["text"])
                
                if not similar_regulations:
                    raise RuntimeError(f"No similar regulations found for chunk {i+1}")
                
                chunk_result = self.llm.analyze_compliance(chunk, similar_regulations)
                
                # Validate result structure
                if not isinstance(chunk_result, dict):
                    raise RuntimeError(f"Invalid result type from LLM for chunk {i+1}: {type(chunk_result)}")
                
                chunk_result.update({
                    "chunk_index": i,
                    "position": chunk_position,
                    "text": chunk["text"],
                    "should_analyze": True
                })
                
                all_results.append(chunk_result)
                
                issues = chunk_result.get("issues", [])
                if self.debug:
                    print(f"Issues found: {len(issues)}")
                
            except Exception as e:
                error_msg = f"Error analyzing chunk {i+1} ({chunk_position}): {e}"
                if self.debug:
                    print(error_msg)
                
                # Don't fall back to empty results - propagate the error
                raise RuntimeError(error_msg)
        
        if not all_results:
            raise RuntimeError("Batch analysis produced no results")
        
        return all_results
    
    def classify_chunks(self, document_chunks: List[Dict[str, Any]]) -> Tuple[List[Tuple], List[Tuple]]:
        """Classify chunks by risk level with proper validation."""
        
        if not document_chunks:
            raise ValueError("document_chunks cannot be empty")
        
        analyze_chunks = []
        skip_chunks = []
        
        for i, chunk in enumerate(document_chunks):
            try:
                chunk_text = chunk.get("text", "")
                if not chunk_text:
                    raise ValueError(f"Chunk {i+1} has no text content")
                
                chunk_text_lower = chunk_text.lower()
                
                # Skip very short chunks
                if len(chunk_text) < ProgressiveConfig.MIN_SECTION_LENGTH:
                    if self.debug:
                        print(f"Skipping chunk {i+1}: too short ({len(chunk_text)} chars)")
                    skip_chunks.append((i, chunk, []))
                    continue
                
                # Score using loaded terms with validation
                try:
                    data_score = sum(chunk_text_lower.count(term.lower()) for term in self.data_terms)
                    regulatory_score = sum(chunk_text_lower.count(term.lower()) for term in self.regulatory_keywords)
                    risk_score = sum(5 for pattern in self.high_risk_patterns if pattern.lower() in chunk_text_lower)
                    
                    total_score = data_score + regulatory_score + risk_score
                    
                    if self.debug:
                        chunk_pos = chunk.get("position", f"Chunk {i+1}")
                        print(f"Scoring {chunk_pos}: data={data_score}, regulatory={regulatory_score}, risk={risk_score}, total={total_score}")
                    
                except Exception as e:
                    raise RuntimeError(f"Error scoring chunk {i+1}: {e}")
                
                # Classify based on score
                if total_score >= ProgressiveConfig.HIGH_RISK_THRESHOLD:
                    analyze_chunks.append((i, chunk, []))
                else:
                    skip_chunks.append((i, chunk, []))
                    
            except Exception as e:
                # Don't silently skip problematic chunks - raise the error
                raise RuntimeError(f"Failed to classify chunk {i+1}: {e}")
        
        if self.debug:
            print(f"Classification complete: {len(analyze_chunks)} high-risk, {len(skip_chunks)} low-risk")
        
        return analyze_chunks, skip_chunks
    
    def process_chunks(self, chunks: List[Tuple], should_analyze: bool) -> List[Dict[str, Any]]:
        """Process chunks with specified analysis level and proper error handling."""
        
        if not isinstance(chunks, list):
            raise ValueError("chunks must be a list")
        
        if not isinstance(should_analyze, bool):
            raise ValueError("should_analyze must be a boolean")
        
        results = []
        
        for chunk_tuple in chunks:
            if not isinstance(chunk_tuple, tuple) or len(chunk_tuple) < 2:
                raise ValueError("Each chunk tuple must have at least (index, chunk)")
            
            i, chunk = chunk_tuple[0], chunk_tuple[1]
            chunk_position = chunk.get("position", f"Section {i+1}")
            
            try:
                if should_analyze:
                    # Validate embeddings handler
                    if not hasattr(self.embeddings, 'find_similar'):
                        raise RuntimeError("Embeddings handler not properly initialized")
                    
                    similar_regulations = self.embeddings.find_similar(chunk["text"])
                    
                    if not similar_regulations:
                        raise RuntimeError(f"No similar regulations found for chunk {chunk_position}")
                    
                    chunk_result = self.llm.analyze_compliance(chunk, similar_regulations)
                    
                    # Validate result
                    if not isinstance(chunk_result, dict):
                        raise RuntimeError(f"Invalid result type from LLM: {type(chunk_result)}")
                    
                    chunk_result.update({
                        "chunk_index": i,
                        "position": chunk_position,
                        "text": chunk["text"],
                        "should_analyze": True
                    })
                    
                    results.append(chunk_result)
                    
                    if self.debug:
                        issues_count = len(chunk_result.get("issues", []))
                        print(f"Analyzed {chunk_position}: {issues_count} issues found")
                    
                else:
                    # Create skip result
                    skip_result = {
                        "chunk_index": i,
                        "position": chunk_position,
                        "text": chunk["text"],
                        "issues": [],
                        "should_analyze": False
                    }
                    results.append(skip_result)
                    
                    if self.debug:
                        print(f"Skipped {chunk_position}")
                
            except Exception as e:
                # Don't fall back to empty results - propagate errors
                error_msg = f"Error processing chunk {chunk_position} (analyze={should_analyze}): {e}"
                if self.debug:
                    print(error_msg)
                raise RuntimeError(error_msg)
        
        return results