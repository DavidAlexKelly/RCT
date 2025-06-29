# utils/progressive_analyzer.py - SIMPLIFIED

import re
from typing import List, Dict, Any, Tuple
from config import ProgressiveConfig, DocumentConfig

class ProgressiveAnalyzer:
    """Progressive analysis using handler classification terms."""
    
    def __init__(self, llm_handler, embeddings_handler, regulation_framework, batch_size=1, debug=False):
        self.llm = llm_handler
        self.embeddings = embeddings_handler
        self.regulation_framework = regulation_framework
        self.batch_size = batch_size
        self.debug = debug
        
        # Get terms from regulation handler (required)
        handler = self.llm.prompt_manager.regulation_handler
        self.data_terms = handler.get_classification_terms("data_terms")
        self.regulatory_keywords = handler.get_classification_terms("regulatory_keywords")
        self.high_risk_patterns = handler.get_classification_terms("high_risk_patterns")
        self.priority_keywords = handler.get_classification_terms("priority_keywords")
        
        if self.debug:
            print(f"Loaded {len(self.data_terms)} data terms, {len(self.regulatory_keywords)} regulatory keywords")
    
    def analyze(self, document_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze with progressive classification."""
        if not ProgressiveConfig.ENABLED:
            return self.analyze_batch(document_chunks)
        
        analyze_chunks, skip_chunks = self.classify_chunks(document_chunks)
        
        all_results = []
        all_results.extend(self.process_chunks(analyze_chunks, should_analyze=True))
        all_results.extend(self.process_chunks(skip_chunks, should_analyze=False))
        all_results.sort(key=lambda x: x.get("chunk_index", 0))
        
        return all_results
    
    def analyze_batch(self, document_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze all chunks without classification."""
        all_results = []
        
        max_chunks = DocumentConfig.MAX_CHUNKS_PER_DOCUMENT
        if len(document_chunks) > max_chunks:
            document_chunks = document_chunks[:max_chunks]
        
        for i, chunk in enumerate(document_chunks):
            print(f"\nCHUNK {i+1}/{len(document_chunks)}: {chunk.get('position', 'Unknown')}")
            
            similar_regulations = self.embeddings.find_similar(chunk["text"])
            
            try:
                chunk_result = self.llm.analyze_compliance(chunk, similar_regulations)
                chunk_result.update({
                    "chunk_index": i,
                    "position": chunk.get("position", "Unknown"),
                    "text": chunk["text"]
                })
                all_results.append(chunk_result)
                
                issues = chunk_result.get("issues", [])
                print(f"Issues found: {len(issues)}")
                
            except Exception as e:
                print(f"Error analyzing chunk: {e}")
                all_results.append({
                    "chunk_index": i,
                    "position": chunk.get("position", "Unknown"),
                    "text": chunk["text"],
                    "issues": []
                })
        
        return all_results
    
    def classify_chunks(self, document_chunks: List[Dict[str, Any]]) -> Tuple[List[Tuple], List[Tuple]]:
        """Classify chunks by risk level."""
        analyze_chunks = []
        skip_chunks = []
        
        for i, chunk in enumerate(document_chunks):
            chunk_text = chunk["text"].lower()
            
            if len(chunk_text) < ProgressiveConfig.MIN_SECTION_LENGTH:
                skip_chunks.append((i, chunk, []))
                continue
            
            # Score using loaded terms
            data_score = sum(chunk_text.count(term) for term in self.data_terms)
            regulatory_score = sum(chunk_text.count(term) for term in self.regulatory_keywords)
            risk_score = sum(5 for pattern in self.high_risk_patterns if pattern in chunk_text)
            
            total_score = data_score + regulatory_score + risk_score
            
            if total_score >= ProgressiveConfig.HIGH_RISK_THRESHOLD:
                analyze_chunks.append((i, chunk, []))
            else:
                skip_chunks.append((i, chunk, []))
        
        return analyze_chunks, skip_chunks
    
    def process_chunks(self, chunks: List[Tuple], should_analyze: bool) -> List[Dict[str, Any]]:
        """Process chunks with specified analysis level."""
        results = []
        
        for i, chunk, _ in chunks:
            if should_analyze:
                similar_regulations = self.embeddings.find_similar(chunk["text"])
                
                try:
                    chunk_result = self.llm.analyze_compliance(chunk, similar_regulations)
                    chunk_result.update({
                        "chunk_index": i,
                        "position": chunk.get("position", "Unknown"),
                        "text": chunk["text"],
                        "should_analyze": True
                    })
                    results.append(chunk_result)
                    
                except Exception as e:
                    results.append({
                        "chunk_index": i,
                        "position": chunk.get("position", "Unknown"),
                        "text": chunk["text"],
                        "issues": [],
                        "should_analyze": True
                    })
            else:
                results.append({
                    "chunk_index": i,
                    "position": chunk.get("position", "Unknown"),
                    "text": chunk["text"],
                    "issues": [],
                    "should_analyze": False
                })
        
        return results