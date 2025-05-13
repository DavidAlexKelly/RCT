# utils/progressive_analyzer.py

import re
from typing import List, Dict, Any, Tuple
import os
from pathlib import Path

class ProgressiveAnalyzer:
    """Handles progressive depth analysis of documents."""
    
    def __init__(self, llm_handler, embeddings_handler, regulation_framework, batch_size=1, 
                high_risk_threshold=5, medium_risk_threshold=2, debug=False):
        """Initialize progressive analyzer."""
        self.llm = llm_handler
        self.embeddings = embeddings_handler
        self.regulation_framework = regulation_framework
        self.batch_size = batch_size
        self.debug = debug
        self.high_risk_threshold = high_risk_threshold
        self.medium_risk_threshold = medium_risk_threshold
        
        # Load risk scoring configuration
        self.risk_score_weights = {
            "high_risk_keyword": 3,
            "pattern_indicator": 2,
            "data_term": 1
        }
        
        # Common data terms across regulation frameworks
        self.data_terms = [
            "personal data", "email", "address", "phone", "location", 
            "user", "profile", "info", "personal", "information", "data"
        ]
        
    def analyze(self, document_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze document chunks with progressive depth.
        This is the main entry point for progressive analysis.
        """
        if self.debug:
            print(f"Starting progressive analysis of {len(document_chunks)} chunks...")
        
        # Step 1: Initial classification of chunks by risk level
        high_risk_chunks, medium_risk_chunks, low_risk_chunks = self.classify_chunks(document_chunks)
        
        if self.debug:
            print(f"\nRisk classification complete:")
            print(f"  - High risk: {len(high_risk_chunks)} chunks")
            print(f"  - Medium risk: {len(medium_risk_chunks)} chunks")
            print(f"  - Low risk: {len(low_risk_chunks)} chunks")
        
        all_chunk_results = []
        
        # Step 2: Process high-risk chunks with detailed analysis
        high_risk_results = self.process_high_risk_chunks(high_risk_chunks)
        all_chunk_results.extend(high_risk_results)
        
        # Step 3: Process medium-risk chunks with standard analysis
        medium_risk_results = self.process_medium_risk_chunks(medium_risk_chunks)
        all_chunk_results.extend(medium_risk_results)
        
        # Step 4: Process low-risk chunks with minimal analysis
        low_risk_results = self.process_low_risk_chunks(low_risk_chunks)
        all_chunk_results.extend(low_risk_results)
        
        # Step 5: Sort results by original chunk order
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
    
    def classify_chunks(self, document_chunks: List[Dict[str, Any]]) -> Tuple[List[Tuple], List[Tuple], List[Tuple]]:
        """Classify document chunks by risk level."""
        high_risk_chunks = []
        medium_risk_chunks = []
        low_risk_chunks = []
        
        # Load high-risk keywords for the specific regulation framework
        high_risk_keywords = self._load_high_risk_keywords()
        
        # Load violation patterns
        violation_patterns = self._load_violation_patterns()
        
        # Classify each chunk
        for i, chunk in enumerate(document_chunks):
            chunk_text = chunk["text"].lower()
            risk_score = 0
            matched_patterns = []
            
            # Check for high-risk keywords
            for keyword in high_risk_keywords:
                if keyword.lower() in chunk_text:
                    risk_score += self.risk_score_weights.get("high_risk_keyword", 3)
                    matched_patterns.append(f"High-risk keyword: '{keyword}'")
            
            # Check for known violation patterns
            for pattern_name, pattern_data in violation_patterns.items():
                for indicator in pattern_data.get("indicators", []):
                    if indicator.lower() in chunk_text:
                        risk_score += self.risk_score_weights.get("pattern_indicator", 2)
                        matched_patterns.append(f"Pattern indicator: '{indicator}' from '{pattern_name}'")
            
            # Check for data-related terms
            for term in self.data_terms:
                if term in chunk_text:
                    risk_score += self.risk_score_weights.get("data_term", 1)
            
            # Classify based on risk score
            if risk_score >= self.high_risk_threshold:
                if self.debug:
                    print(f"Chunk {i+1} identified as HIGH risk (score: {risk_score})")
                    if matched_patterns:
                        print(f"  Matched: {matched_patterns[:3]}")
                high_risk_chunks.append((i, chunk, matched_patterns))
            elif risk_score >= self.medium_risk_threshold:
                if self.debug:
                    print(f"Chunk {i+1} identified as MEDIUM risk (score: {risk_score})")
                medium_risk_chunks.append((i, chunk, matched_patterns))
            else:
                if self.debug:
                    print(f"Chunk {i+1} identified as LOW risk (score: {risk_score})")
                low_risk_chunks.append((i, chunk, []))
        
        return high_risk_chunks, medium_risk_chunks, low_risk_chunks
    
    def _load_high_risk_keywords(self) -> List[str]:
        """Load high-risk keywords for the regulation framework."""
        # Load from framework-specific file if available
        base_dir = self._get_knowledge_base_dir()
        keywords_path = os.path.join(base_dir, self.regulation_framework, "risk_keywords.txt")
        
        keywords = []
        
        # Try to load framework-specific keywords
        if os.path.exists(keywords_path):
            try:
                with open(keywords_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            keywords.append(line)
            except Exception as e:
                if self.debug:
                    print(f"Error loading risk keywords: {e}")
        
        # Load default keywords if no framework-specific ones or as a supplement
        if not keywords:
            # Generic high-risk keywords that apply to most regulatory frameworks
            default_keywords = [
                "indefinitely", "permanent", "all data", "required to accept", 
                "must agree", "no option", "without consent", "automated", 
                "without human", "sensitive", "collect everything", "all available", 
                "unencrypted", "no encryption", "budget constraints", "minimal security"
            ]
            keywords.extend(default_keywords)
        
        return keywords
    
    def _load_violation_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load violation patterns for the regulation framework."""
        violation_patterns = {}
        
        # Get patterns file path
        base_dir = self._get_knowledge_base_dir()
        pattern_file = os.path.join(base_dir, self.regulation_framework, "common_patterns.txt")
        
        if os.path.exists(pattern_file):
            try:
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    pattern_text = f.read()
                    
                # Parse the patterns file
                current_pattern = None
                for line in pattern_text.split('\n'):
                    if line.startswith('Pattern:'):
                        current_pattern = line.replace('Pattern:', '').strip()
                        violation_patterns[current_pattern] = {"indicators": [], "risk": "medium"}
                    elif line.startswith('Indicators:') and current_pattern:
                        indicators = line.replace('Indicators:', '').strip()
                        # Extract quoted phrases or comma-separated items
                        if '"' in indicators:
                            quoted_indicators = re.findall(r'"([^"]*)"', indicators)
                            violation_patterns[current_pattern]["indicators"].extend(quoted_indicators)
                        else:
                            comma_indicators = [i.strip() for i in indicators.split(',')]
                            violation_patterns[current_pattern]["indicators"].extend(comma_indicators)
            except Exception as e:
                if self.debug:
                    print(f"Error loading patterns: {e}")
        
        return violation_patterns
    
    def _get_knowledge_base_dir(self) -> str:
        """Get the path to the knowledge base directory."""
        # Try to find knowledge base directory
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(script_dir, "knowledge_base")
    
    def process_high_risk_chunks(self, high_risk_chunks: List[Tuple]) -> List[Dict[str, Any]]:
        """Process high-risk chunks with thorough analysis."""
        result_chunks = []
        
        if not high_risk_chunks:
            return result_chunks
            
        print(f"\nPerforming detailed analysis on {len(high_risk_chunks)} high-risk chunks...")
        
        for i, chunk, patterns in high_risk_chunks:
            print(f"\nAnalyzing HIGH-RISK chunk {i+1}: {chunk.get('position', 'Unknown')}")
            
            # Find relevant regulations - more for high-risk
            similar_regulations = self.embeddings.find_similar(chunk["text"], k=5)
            
            try:
                # Prepare chunk with metadata
                chunk_with_metadata = chunk.copy()
                chunk_with_metadata["detected_patterns"] = patterns
                chunk_with_metadata["risk_level"] = "high"
                
                # Analyze with LLM
                chunk_result = self.llm.analyze_compliance(chunk_with_metadata, similar_regulations)
                
                # Add metadata to result
                chunk_result.update({
                    "chunk_index": i,
                    "position": chunk.get("position", "Unknown"),
                    "text": chunk["text"],
                    "risk_level": "high"
                })
                
                result_chunks.append(chunk_result)
                
                # Report issues found
                issues = chunk_result.get("issues", [])
                if issues:
                    print(f"Issues found: {len(issues)}")
                    for idx, issue in enumerate(issues[:3]):  # Show top 3
                        print(f"  Issue {idx+1}: {issue.get('issue', 'Unknown')} ({issue.get('confidence', 'Medium')})")
                else:
                    print("No issues found in this high-risk chunk.")
            except Exception as e:
                print(f"Error analyzing high-risk chunk: {e}")
                # Create empty result
                result_chunks.append({
                    "chunk_index": i,
                    "position": chunk.get("position", "Unknown"),
                    "text": chunk["text"],
                    "issues": [],
                    "compliance_points": [],
                    "risk_level": "high"
                })
        
        return result_chunks
    
    def process_medium_risk_chunks(self, medium_risk_chunks: List[Tuple]) -> List[Dict[str, Any]]:
        """Process medium-risk chunks with standard analysis."""
        result_chunks = []
        
        if not medium_risk_chunks:
            return result_chunks
            
        print(f"\nPerforming standard analysis on {len(medium_risk_chunks)} medium-risk chunks...")
        
        # Try to use a faster model for medium-risk chunks if available
        original_model = None
        if hasattr(self.llm, 'switch_to_faster_model'):
            original_model = self.llm.model_key
            self.llm.switch_to_faster_model()
            if self.debug and original_model != self.llm.model_key:
                print(f"Switched to faster model ({self.llm.model_key}) for medium-risk chunks")
        
        for i, chunk, patterns in medium_risk_chunks:
            print(f"\nAnalyzing MEDIUM-RISK chunk {i+1}: {chunk.get('position', 'Unknown')}")
            
            # Find relevant regulations - fewer for medium risk
            similar_regulations = self.embeddings.find_similar(chunk["text"], k=3)
            
            try:
                # Prepare chunk with metadata
                chunk_with_metadata = chunk.copy()
                chunk_with_metadata["detected_patterns"] = patterns
                chunk_with_metadata["risk_level"] = "medium"
                
                # Analyze with LLM
                chunk_result = self.llm.analyze_compliance(chunk_with_metadata, similar_regulations)
                
                # Add metadata to result
                chunk_result.update({
                    "chunk_index": i,
                    "position": chunk.get("position", "Unknown"),
                    "text": chunk["text"],
                    "risk_level": "medium"
                })
                
                result_chunks.append(chunk_result)
                
                # Report issues found
                issues = chunk_result.get("issues", [])
                if issues:
                    print(f"Issues found: {len(issues)}")
                    for idx, issue in enumerate(issues[:2]):  # Show top 2
                        print(f"  Issue {idx+1}: {issue.get('issue', 'Unknown')} ({issue.get('confidence', 'Medium')})")
                else:
                    print("No issues found in this medium-risk chunk.")
            except Exception as e:
                print(f"Error analyzing medium-risk chunk: {e}")
                # Create empty result
                result_chunks.append({
                    "chunk_index": i,
                    "position": chunk.get("position", "Unknown"),
                    "text": chunk["text"],
                    "issues": [],
                    "compliance_points": [],
                    "risk_level": "medium"
                })
        
        # Switch back to original model if needed
        if original_model and hasattr(self.llm, 'restore_original_model'):
            self.llm.restore_original_model()
            if self.debug:
                print(f"Restored original model ({original_model}) after processing medium-risk chunks")
        
        return result_chunks
    
    def process_low_risk_chunks(self, low_risk_chunks: List[Tuple]) -> List[Dict[str, Any]]:
        """Process low-risk chunks with minimal analysis."""
        result_chunks = []
        
        if not low_risk_chunks:
            return result_chunks
            
        print(f"\nSkipping detailed analysis for {len(low_risk_chunks)} low-risk chunks...")
        
        # For low-risk chunks, just create minimal results without LLM analysis
        for i, chunk, _ in low_risk_chunks:
            result_chunks.append({
                "chunk_index": i,
                "position": chunk.get("position", "Unknown"),
                "text": chunk["text"],
                "issues": [],
                "compliance_points": [],
                "risk_level": "low"
            })
        
        return result_chunks