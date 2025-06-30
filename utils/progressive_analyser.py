from typing import List, Dict, Any

class ProgressiveAnalyser:
    """Simplified progressive analysis using framework handler keyword scoring."""
    
    def __init__(self, handler, embeddings_handler, debug=False):
        """Initialize with framework handler and embeddings."""
        
        assert handler, "Missing framework handler"
        assert embeddings_handler, "Missing embeddings handler"
        
        self.handler = handler
        self.embeddings = embeddings_handler
        self.debug = debug
        
        if self.debug:
            print(f"Progressive Analyser: Initialized for {handler.name}")
            print(f"Regulated topics: {len(handler.regulated_topics)} categories")
            print(f"Topic threshold: {handler.analysis_threshold}")
    
    def classify_chunks(self, document_chunks: List[Dict[str, Any]]) -> tuple:
        """Classify chunks as high-risk (analyse) or low-risk (skip)."""
        
        analyse_chunks = []
        skip_chunks = []
        
        for i, chunk in enumerate(document_chunks):
            chunk_text = chunk.get("text", "")
            
            # Skip very short chunks
            if len(chunk_text) < 100:
                skip_chunks.append((i, chunk, {"reason": "too_short", "score": 0}))
                continue
            
            # Use handler's topic assessment
            topic_score = self.handler.calculate_risk_score(chunk_text)
            should_analyse = self.handler.should_analyse(chunk_text)
            
            if self.debug:
                pos = chunk.get("position", f"Chunk {i+1}")
                print(f"Chunk {pos}: topics={topic_score:.1f}, analyse={should_analyse}")
            
            if should_analyse:
                analyse_chunks.append((i, chunk, {"score": topic_score, "reason": "multiple_topics"}))
            else:
                skip_chunks.append((i, chunk, {"score": topic_score, "reason": "insufficient_topics"}))
        
        if self.debug:
            total = len(document_chunks)
            analyse_count = len(analyse_chunks)
            skip_count = len(skip_chunks)
            efficiency = (skip_count / total * 100) if total > 0 else 0
            print(f"Progressive Analysis Results:")
            print(f"  Total chunks: {total}")
            print(f"  Multi-topic (analyse): {analyse_count}")
            print(f"  Single/no topic (skip): {skip_count}")
            print(f"  Efficiency gain: {efficiency:.1f}%")
        
        return analyse_chunks, skip_chunks
    
    def analyse(self, document_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Main analysis method - classifies and returns results."""
        
        assert document_chunks, "No chunks to analyse"
        
        # Classify chunks
        analyse_chunks, skip_chunks = self.classify_chunks(document_chunks)
        
        results = []
        
        # Process chunks that need analysis
        for chunk_index, chunk, metadata in analyse_chunks:
            chunk_position = chunk.get("position", f"Section {chunk_index + 1}")
            
            if self.debug:
                print(f"Progressive: Analysing {chunk_position}")
            
            results.append({
                "chunk_index": chunk_index,
                "chunk": chunk,
                "should_analyse": True,
                "risk_score": metadata.get("score", 0),
                "position": chunk_position
            })
        
        # Process chunks that are skipped
        for chunk_index, chunk, metadata in skip_chunks:
            chunk_position = chunk.get("position", f"Section {chunk_index + 1}")
            
            if self.debug:
                print(f"Progressive: Skipping {chunk_position}")
            
            results.append({
                "chunk_index": chunk_index,
                "chunk": chunk,
                "should_analyse": False,
                "risk_score": metadata.get("score", 0),
                "position": chunk_position,
                "skip_reason": metadata.get("reason", "low_risk")
            })
        
        # Sort by original index
        results.sort(key=lambda x: x.get("chunk_index", 0))
        return results