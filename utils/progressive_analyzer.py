from typing import List, Dict, Any, Tuple
from config import config

class ProgressiveAnalyzer:
    """Progressive analysis using regulation handler classification terms."""
    
    def __init__(self, llm_handler, embeddings_handler, regulation_framework, batch_size=1, debug=False):
        """Initialize progressive analyzer."""
        
        assert llm_handler and embeddings_handler, "Missing required handlers"
        assert regulation_framework, "Missing framework"
        
        self.llm = llm_handler
        self.embeddings = embeddings_handler
        self.regulation_framework = regulation_framework
        self.batch_size = max(1, batch_size)
        self.debug = debug
        
        # Get classification terms from handler
        handler = self.llm.prompt_manager.regulation_handler
        assert handler, "Missing regulation handler"
        
        try:
            self.data_terms = handler.get_classification_terms("data_terms")
            self.regulatory_keywords = handler.get_classification_terms("regulatory_keywords")
            self.high_risk_patterns = handler.get_classification_terms("high_risk_patterns")
            self.priority_keywords = handler.get_classification_terms("priority_keywords")
        except Exception as e:
            raise RuntimeError(f"Failed to load classification terms: {e}")
        
        assert all([self.data_terms, self.regulatory_keywords, self.high_risk_patterns]), \
               "Missing classification terms"
        
        if self.debug:
            print(f"Loaded terms: {len(self.data_terms)} data, {len(self.regulatory_keywords)} regulatory")
    
    def analyze(self, document_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze with progressive classification."""
        
        assert document_chunks, "No chunks to analyze"
        
        if not config.progressive_enabled:
            return self.analyze_batch(document_chunks)
        
        analyze_chunks, skip_chunks = self.classify_chunks(document_chunks)
        
        if self.debug:
            print(f"Progressive: {len(analyze_chunks)} analyze, {len(skip_chunks)} skip")
        
        results = []
        results.extend(self.process_chunks(analyze_chunks, should_analyze=True))
        results.extend(self.process_chunks(skip_chunks, should_analyze=False))
        
        # Sort by original index
        results.sort(key=lambda x: x.get("chunk_index", 0))
        return results
    
    def analyze_batch(self, document_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze all chunks without progressive filtering."""
        
        results = []
        
        for i, chunk in enumerate(document_chunks):
            chunk_position = chunk.get("position", f"Section {i+1}")
            
            if self.debug:
                print(f"Batch analyzing: {chunk_position}")
            
            similar_regulations = self.embeddings.find_similar(chunk["text"])
            chunk_result = self.llm.analyze_compliance(chunk, similar_regulations)
            
            chunk_result.update({
                "chunk_index": i,
                "position": chunk_position,
                "text": chunk["text"],
                "should_analyze": True
            })
            
            results.append(chunk_result)
        
        return results
    
    def classify_chunks(self, document_chunks: List[Dict[str, Any]]) -> Tuple[List[Tuple], List[Tuple]]:
        """Classify chunks by risk level."""
        
        analyze_chunks = []
        skip_chunks = []
        
        for i, chunk in enumerate(document_chunks):
            chunk_text = chunk.get("text", "")
            
            # Skip very short chunks
            if len(chunk_text) < 150:
                skip_chunks.append((i, chunk, []))
                continue
            
            # Score chunk using classification terms
            chunk_lower = chunk_text.lower()
            
            data_score = sum(chunk_lower.count(term.lower()) for term in self.data_terms)
            regulatory_score = sum(chunk_lower.count(term.lower()) for term in self.regulatory_keywords)
            risk_score = sum(5 for pattern in self.high_risk_patterns if pattern.lower() in chunk_lower)
            
            total_score = data_score + regulatory_score + risk_score
            
            if self.debug:
                pos = chunk.get("position", f"Chunk {i+1}")
                print(f"Score {pos}: data={data_score}, reg={regulatory_score}, risk={risk_score}, total={total_score}")
            
            # Classify based on threshold
            if total_score >= config.high_risk_threshold:
                analyze_chunks.append((i, chunk, []))
            else:
                skip_chunks.append((i, chunk, []))
        
        return analyze_chunks, skip_chunks
    
    def process_chunks(self, chunks: List[Tuple], should_analyze: bool) -> List[Dict[str, Any]]:
        """Process chunks with specified analysis level."""
        
        results = []
        
        for chunk_tuple in chunks:
            i, chunk = chunk_tuple[0], chunk_tuple[1]
            chunk_position = chunk.get("position", f"Section {i+1}")
            
            if should_analyze:
                # Full LLM analysis
                similar_regulations = self.embeddings.find_similar(chunk["text"])
                chunk_result = self.llm.analyze_compliance(chunk, similar_regulations)
                
                chunk_result.update({
                    "chunk_index": i,
                    "position": chunk_position,
                    "text": chunk["text"],
                    "should_analyze": True
                })
                
                results.append(chunk_result)
                
                if self.debug:
                    issues = len(chunk_result.get("issues", []))
                    print(f"Analyzed {chunk_position}: {issues} issues")
            
            else:
                # Skip analysis
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
        
        return results