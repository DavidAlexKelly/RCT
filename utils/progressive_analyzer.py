# utils/progressive_analyzer.py

import re
from typing import List, Dict, Any, Tuple
import os
from pathlib import Path

class ProgressiveAnalyzer:
    """Handles progressive depth analysis of documents."""
    
    def __init__(self, llm_handler, embeddings_handler, regulation_framework, batch_size=1, debug=False):
        """Initialize progressive analyzer."""
        self.llm = llm_handler
        self.embeddings = embeddings_handler
        self.regulation_framework = regulation_framework
        self.batch_size = batch_size
        self.debug = debug
        
        # Load framework-specific terms if available, otherwise use generic terms
        self.data_terms = self._load_framework_terms("data_terms")
        self.regulatory_keywords = self._load_framework_terms("regulatory_keywords")
        
    def _load_framework_terms(self, term_type):
        """Load framework-specific terms or use generic defaults."""
        try:
            # Try to load from framework-specific config
            import os
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            terms_file = os.path.join(script_dir, "knowledge_base", self.regulation_framework, f"{term_type}.txt")
            
            if os.path.exists(terms_file):
                with open(terms_file, 'r', encoding='utf-8') as f:
                    terms = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    if self.debug:
                        print(f"Loaded {len(terms)} {term_type} for {self.regulation_framework}")
                    return terms
        except Exception as e:
            if self.debug:
                print(f"Could not load {term_type} for {self.regulation_framework}: {e}")
        
        # Fallback to generic terms
        if term_type == "data_terms":
            return [
                "data", "information", "record", "file", "database",
                "collect", "store", "process", "retain", "share", 
                "user", "customer", "individual", "person", "entity",
                "tracking", "monitoring", "surveillance"
            ]
        elif term_type == "regulatory_keywords":
            return [
                "compliance", "regulation", "legal", "lawful", "authorize",
                "rights", "responsibilities", "obligations", "requirements",
                "security", "protection", "safeguard", "confidential",
                "notice", "notification", "transparency", "disclosure",
                "access", "control", "restrict", "limit", "prohibit",
                "consent", "approval", "authorization", "permit"
            ]
        else:
            return []
        
    def analyze(self, document_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze document chunks with simplified binary classification.
        This is the main entry point for progressive analysis.
        """
        if self.debug:
            print(f"Starting simplified progressive analysis of {len(document_chunks)} chunks...")
        
        # Step 1: Classify chunks as analyze vs skip
        analyze_chunks, skip_chunks = self.classify_chunks(document_chunks)
        
        if self.debug:
            print(f"\nClassification complete:")
            print(f"  - Analyze: {len(analyze_chunks)} chunks")
            print(f"  - Skip: {len(skip_chunks)} chunks")
        
        all_chunk_results = []
        
        # Step 2: Process chunks marked for analysis
        analyze_results = self.process_chunks(analyze_chunks, should_analyze=True)
        all_chunk_results.extend(analyze_results)
        
        # Step 3: Process chunks marked to skip (minimal processing)
        skip_results = self.process_chunks(skip_chunks, should_analyze=False)
        all_chunk_results.extend(skip_results)
        
        # Step 4: Sort results by original chunk order
        all_chunk_results.sort(key=lambda x: x.get("chunk_index", 0))
        
        return all_chunk_results
    
    def analyze_batch(self, document_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze document chunks using traditional batch processing.
        This is used when progressive analysis is disabled.
        """
        if self.debug:
            print(f"Starting batch analysis of {len(document_chunks)} chunks...")
        
        all_chunk_results = []
        
        # Process in batches for better efficiency
        for i in range(0, len(document_chunks), self.batch_size):
            batch = document_chunks[i:i + self.batch_size]
            batch_end = min(i + self.batch_size, len(document_chunks))
            print(f"Processing batch {i//self.batch_size + 1}/{(len(document_chunks) + self.batch_size - 1)//self.batch_size} (chunks {i+1}-{batch_end} of {len(document_chunks)})...")
            
            batch_results = []
            # Process each chunk in the batch
            for chunk_index, chunk in enumerate(batch):
                current_chunk_index = i + chunk_index
                print(f"\nCHUNK {current_chunk_index+1}/{len(document_chunks)}: {chunk.get('position', 'Unknown')}")
                print("-" * 40)
                # Display first 100 chars of the chunk text
                chunk_preview = chunk["text"][:100] + "..." if len(chunk["text"]) > 100 else chunk["text"]
                print(f"Content preview: {chunk_preview}")
                
                # Find relevant regulations
                similar_regulations = self.embeddings.find_similar(chunk["text"])
                
                try:
                    # Analyze compliance
                    chunk_result = self.llm.analyze_compliance(chunk, similar_regulations)
                    
                    # Make sure we have a valid result
                    if chunk_result is None:
                        if self.debug:
                            print("Warning: LLM analysis returned None. Creating empty result.")
                        chunk_result = {
                            "issues": [],
                            "compliance_points": [],
                            "position": chunk.get("position", "Unknown"),
                            "text": chunk["text"]
                        }
                    
                    # Add chunk info to result
                    chunk_result.update({
                        "chunk_index": current_chunk_index,
                        "position": chunk.get("position", "Unknown"),
                        "text": chunk["text"]
                    })
                    
                    # Report issues found for this chunk
                    issues = chunk_result.get("issues", [])
                    if issues:
                        print(f"Issues found: {len(issues)}")
                        for idx, issue in enumerate(issues):
                            print(f"  Issue {idx+1}: {issue.get('issue', 'Unknown issue')} ({issue.get('confidence', 'Medium')} confidence)")
                    else:
                        print("No issues found in this chunk.")
                    
                    # Report compliance points found for this chunk
                    compliance_points = chunk_result.get("compliance_points", [])
                    if compliance_points:
                        print(f"Compliance points found: {len(compliance_points)}")
                        for idx, point in enumerate(compliance_points):
                            print(f"  Point {idx+1}: {point.get('point', 'Unknown point')} ({point.get('confidence', 'Medium')} confidence)")
                    else:
                        print("No compliance points found in this chunk.")
                        
                    batch_results.append(chunk_result)
                except Exception as e:
                    print(f"Error analyzing chunk: {e}")
                    if self.debug:
                        import traceback
                        traceback.print_exc()
                    # Create empty result for this chunk to avoid breaking the entire analysis
                    empty_result = {
                        "chunk_index": current_chunk_index,
                        "position": chunk.get("position", "Unknown"),
                        "text": chunk["text"],
                        "issues": [],
                        "compliance_points": []
                    }
                    batch_results.append(empty_result)
                    print("Created empty result for this chunk due to error.")
            
            # Add batch results to all results
            all_chunk_results.extend(batch_results)
            print(f"\nProcessed {len(batch_results)} chunks in this batch")
            
        return all_chunk_results
    
    def classify_chunks(self, document_chunks: List[Dict[str, Any]]) -> Tuple[List[Tuple], List[Tuple]]:
        """Classify document chunks as analyze vs skip based on data relevance."""
        analyze_chunks = []
        skip_chunks = []
        
        for i, chunk in enumerate(document_chunks):
            chunk_text = chunk["text"].lower()
            
            # Simple scoring based on data-related terms
            data_score = 0
            for term in self.data_terms:
                if term in chunk_text:
                    data_score += 1
            
            # Check for regulatory keywords - use loaded terms
            regulatory_score = 0
            for keyword in self.regulatory_keywords:
                if keyword in chunk_text:
                    regulatory_score += 1
            
            # Simple binary classification - made more selective
            total_score = data_score + regulatory_score
            
            # Don't analyze very short sections even if they have keywords (likely just headers)
            if len(chunk_text) < 100:
                if self.debug:
                    print(f"Chunk {i+1}: SKIP (too short: {len(chunk_text)} chars)")
                skip_chunks.append((i, chunk, []))
            elif total_score >= 3 or len(chunk_text) > 1500:  # Raised threshold from 2 to 3
                if self.debug:
                    print(f"Chunk {i+1}: ANALYZE (score: {total_score})")
                analyze_chunks.append((i, chunk, []))
            else:
                if self.debug:
                    print(f"Chunk {i+1}: SKIP (score: {total_score})")
                skip_chunks.append((i, chunk, []))
        
        return analyze_chunks, skip_chunks
    
    def process_chunks(self, chunks: List[Tuple], should_analyze: bool) -> List[Dict[str, Any]]:
        """Process chunks with specified analysis level."""
        result_chunks = []
        
        if not chunks:
            return result_chunks
        
        action = "Analyzing" if should_analyze else "Skipping analysis for"
        print(f"\n{action} {len(chunks)} chunks...")
        
        for i, chunk, _ in chunks:
            chunk_position = chunk.get("position", "Unknown")
            
            if should_analyze:
                print(f"\nAnalyzing chunk {i+1}: {chunk_position}")
                
                # Find relevant regulations
                similar_regulations = self.embeddings.find_similar(chunk["text"], k=5)
                
                try:
                    # Prepare chunk with metadata
                    chunk_with_metadata = chunk.copy()
                    chunk_with_metadata["should_analyze"] = True
                    
                    # Analyze with LLM
                    chunk_result = self.llm.analyze_compliance(chunk_with_metadata, similar_regulations)
                    
                    # Add metadata to result
                    chunk_result.update({
                        "chunk_index": i,
                        "position": chunk_position,
                        "text": chunk["text"],
                        "should_analyze": True
                    })
                    
                    result_chunks.append(chunk_result)
                    
                    # Report issues found
                    issues = chunk_result.get("issues", [])
                    if issues:
                        print(f"Issues found: {len(issues)}")
                        for idx, issue in enumerate(issues[:3]):  # Show top 3
                            print(f"  Issue {idx+1}: {issue.get('issue', 'Unknown')} ({issue.get('confidence', 'Medium')})")
                    else:
                        print("No issues found in this chunk.")
                        
                except Exception as e:
                    print(f"Error analyzing chunk: {e}")
                    if self.debug:
                        import traceback
                        traceback.print_exc()
                    # Create empty result
                    result_chunks.append({
                        "chunk_index": i,
                        "position": chunk_position,
                        "text": chunk["text"],
                        "issues": [],
                        "compliance_points": [],
                        "should_analyze": True
                    })
            else:
                # Skip analysis - just create minimal result
                result_chunks.append({
                    "chunk_index": i,
                    "position": chunk_position,
                    "text": chunk["text"],
                    "issues": [],
                    "compliance_points": [],
                    "should_analyze": False
                })
        
        return result_chunks