# utils/progressive_analyzer.py

import re
from typing import List, Dict, Any, Tuple
import os
from pathlib import Path

# Import centralized performance configuration
from config import ProgressiveConfig, DocumentConfig

class ProgressiveAnalyzer:
    """Handles progressive depth analysis of documents using configurable thresholds."""
    
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
        self.high_risk_patterns = self._load_framework_terms("high_risk_patterns")
        self.priority_keywords = self._load_framework_terms("priority_keywords")
        
        if self.debug:
            print(f"Progressive Analysis Configuration:")
            print(f"  - High Risk Threshold: {ProgressiveConfig.HIGH_RISK_THRESHOLD}")
            print(f"  - Medium Risk Threshold: {ProgressiveConfig.MEDIUM_RISK_THRESHOLD}")
            print(f"  - Min Section Length: {ProgressiveConfig.MIN_SECTION_LENGTH}")
            print(f"  - Progressive Analysis: {'Enabled' if ProgressiveConfig.ENABLED else 'Disabled'}")
        
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
        
        # Framework-agnostic fallback terms
        return self._get_generic_terms(term_type)
    
    def _get_generic_terms(self, term_type):
        """Get generic terms that work across regulation frameworks."""
        if term_type == "data_terms":
            return [
                "information", "record", "file", "database", "document",
                "collect", "store", "maintain", "handle", "manage", 
                "entity", "individual", "organization", "business",
                "system", "process", "procedure"
            ]
        elif term_type == "regulatory_keywords":
            return [
                "compliance", "regulation", "legal", "lawful", "requirement",
                "standard", "rule", "policy", "procedure", "guideline",
                "obligation", "responsibility", "requirement", "mandate",
                "violation", "breach", "non-compliance", "infringement",
                "audit", "inspection", "assessment", "review"
            ]
        elif term_type == "high_risk_patterns":
            return [
                "non-compliant", "violation", "breach", "illegal",
                "unauthorized", "improper", "inadequate", "insufficient",
                "failed", "missing", "absent", "lacking"
            ]
        elif term_type == "priority_keywords":
            return [
                "compliance", "violation", "breach", "requirement", "standard"
            ]
        else:
            return []
        
    def analyze(self, document_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze document chunks with configurable progressive classification.
        """
        if self.debug:
            print(f"Starting progressive analysis of {len(document_chunks)} chunks...")
        
        # Check if progressive analysis is enabled
        if not ProgressiveConfig.ENABLED:
            if self.debug:
                print("Progressive analysis disabled - processing all chunks")
            return self.analyze_batch(document_chunks)
        
        # Step 1: Classify chunks as analyze vs skip with configurable selectivity
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
        
        # Apply document limits
        max_chunks = DocumentConfig.MAX_CHUNKS_PER_DOCUMENT
        if len(document_chunks) > max_chunks:
            if self.debug:
                print(f"Warning: Document has {len(document_chunks)} chunks, limiting to {max_chunks}")
            document_chunks = document_chunks[:max_chunks]
        
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
                        "issues": []
                    }
                    batch_results.append(empty_result)
                    print("Created empty result for this chunk due to error.")
            
            # Add batch results to all results
            all_chunk_results.extend(batch_results)
            print(f"\nProcessed {len(batch_results)} chunks in this batch")
            
        return all_chunk_results
    
    def classify_chunks(self, document_chunks: List[Dict[str, Any]]) -> Tuple[List[Tuple], List[Tuple]]:
        """Classify document chunks with configurable selectivity - framework agnostic."""
        analyze_chunks = []
        skip_chunks = []
        
        for i, chunk in enumerate(document_chunks):
            chunk_text = chunk["text"].lower()
            chunk_position = chunk.get("position", "Unknown")
            
            # 🔧 Use configurable minimum section length
            if len(chunk_text) < ProgressiveConfig.MIN_SECTION_LENGTH:
                if self.debug:
                    print(f"Chunk {i+1} ({chunk_position}): SKIP (too short: {len(chunk_text)} chars)")
                skip_chunks.append((i, chunk, []))
                continue
            
            # Calculate scores with configurable weights
            data_score = 0
            regulatory_score = 0
            risk_score = 0
            
            # 🔧 Use configurable scoring weights
            for term in self.data_terms:
                count = chunk_text.count(term)
                data_score += count * ProgressiveConfig.DATA_TERM_WEIGHT
            
            for keyword in self.regulatory_keywords:
                count = chunk_text.count(keyword)
                # Use framework-specific priority keywords instead of hardcoded terms
                if keyword in self.priority_keywords:
                    regulatory_score += count * (ProgressiveConfig.REGULATORY_TERM_WEIGHT * 1.5)
                else:
                    regulatory_score += count * ProgressiveConfig.REGULATORY_TERM_WEIGHT
            
            # Use framework-specific high-risk patterns
            for pattern in self.high_risk_patterns:
                if re.search(pattern, chunk_text):
                    risk_score += ProgressiveConfig.HIGH_RISK_PATTERN_WEIGHT
            
            # Special handling for technical sections that mention relevant terms
            tech_terms = ["system", "process", "procedure", "method", "implementation"]
            relevant_terms = self.data_terms[:5]  # Use first 5 data terms as relevance indicators
            
            if any(tech_term in chunk_text for tech_term in tech_terms):
                if any(relevant_term in chunk_text for relevant_term in relevant_terms):
                    risk_score += 2  # Technical + relevant = worth analyzing
            
            # Calculate total score
            total_score = data_score + regulatory_score + risk_score
            
            # 🔧 Use configurable classification thresholds
            should_analyze = False
            
            if risk_score >= ProgressiveConfig.HIGH_RISK_PATTERN_WEIGHT:
                should_analyze = True
                reason = f"high-risk patterns (risk: {risk_score})"
            elif total_score >= ProgressiveConfig.HIGH_RISK_THRESHOLD:
                should_analyze = True
                reason = f"high score (total: {total_score})"
            elif (data_score >= 4 and regulatory_score >= 2):
                should_analyze = True
                reason = f"mixed content (data: {data_score}, reg: {regulatory_score})"
            elif len(chunk_text) > 2000 and total_score >= ProgressiveConfig.MEDIUM_RISK_THRESHOLD:
                should_analyze = True  
                reason = f"large section with relevance (size: {len(chunk_text)}, score: {total_score})"
            else:
                should_analyze = False
                reason = f"low relevance (total: {total_score})"
            
            if self.debug:
                print(f"Chunk {i+1} ({chunk_position}): {'ANALYZE' if should_analyze else 'SKIP'} - {reason}")
                if should_analyze:
                    print(f"  Scores - Data: {data_score}, Regulatory: {regulatory_score}, Risk: {risk_score}")
            
            if should_analyze:
                analyze_chunks.append((i, chunk, []))
            else:
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
                        "should_analyze": True
                    })
            else:
                # Skip analysis - just create minimal result
                result_chunks.append({
                    "chunk_index": i,
                    "position": chunk_position,
                    "text": chunk["text"],
                    "issues": [],
                    "should_analyze": False
                })
        
        return result_chunks