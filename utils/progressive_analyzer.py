"""
Progressive Analyzer Module

Implements risk-based progressive analysis to optimize LLM usage.
Classifies document sections by compliance risk and only analyzes high-risk sections.
"""

import re
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path

from config import ProgressiveConfig, DocumentConfig

logger = logging.getLogger(__name__)


class ProgressiveAnalyzer:
    """
    Handles progressive depth analysis using configurable risk thresholds.
    
    Classifies document chunks by compliance risk level and only sends
    high-risk chunks to expensive LLM analysis.
    """
    
    def __init__(self, llm_handler: Any, embeddings_handler: Any, 
                 regulation_framework: str, batch_size: int = 1, 
                 debug: bool = False) -> None:
        """
        Initialize progressive analyzer.
        
        Args:
            llm_handler: LLM handler for analysis
            embeddings_handler: Embeddings handler for RAG
            regulation_framework: Regulation framework name
            batch_size: Batch size for processing
            debug: Enable debug logging
        """
        self.llm = llm_handler
        self.embeddings = embeddings_handler
        self.regulation_framework = regulation_framework
        self.batch_size = batch_size
        self.debug = debug
        
        # Load framework-specific terms
        self.data_terms = self._load_framework_terms("data_terms")
        self.regulatory_keywords = self._load_framework_terms("regulatory_keywords")
        self.high_risk_patterns = self._load_framework_terms("high_risk_patterns")
        self.priority_keywords = self._load_framework_terms("priority_keywords")
        
        logger.info(f"ProgressiveAnalyzer initialized for {regulation_framework}")
        if self.debug:
            logger.debug(f"Risk thresholds - High: {ProgressiveConfig.HIGH_RISK_THRESHOLD}, "
                        f"Medium: {ProgressiveConfig.MEDIUM_RISK_THRESHOLD}")
        
    def analyze(self, document_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze document chunks with progressive classification.
        
        Args:
            document_chunks: List of document chunks to analyze
            
        Returns:
            List of analysis results for all chunks
        """
        logger.info(f"Starting progressive analysis of {len(document_chunks)} chunks")
        
        # Check if progressive analysis is enabled
        if not ProgressiveConfig.ENABLED:
            logger.info("Progressive analysis disabled - processing all chunks")
            return self.analyze_batch(document_chunks)
        
        # Step 1: Classify chunks
        analyze_chunks, skip_chunks = self.classify_chunks(document_chunks)
        
        logger.info(f"Classification complete: {len(analyze_chunks)} to analyze, "
                   f"{len(skip_chunks)} to skip")
        
        all_chunk_results = []
        
        # Step 2: Process chunks marked for analysis
        analyze_results = self.process_chunks(analyze_chunks, should_analyze=True)
        all_chunk_results.extend(analyze_results)
        
        # Step 3: Process chunks marked to skip
        skip_results = self.process_chunks(skip_chunks, should_analyze=False)
        all_chunk_results.extend(skip_results)
        
        # Step 4: Sort results by original chunk order
        all_chunk_results.sort(key=lambda x: x.get("chunk_index", 0))
        
        return all_chunk_results
    
    def analyze_batch(self, document_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze all document chunks without progressive filtering.
        
        Args:
            document_chunks: List of document chunks to analyze
            
        Returns:
            List of analysis results
        """
        logger.info(f"Starting batch analysis of {len(document_chunks)} chunks")
        
        all_chunk_results = []
        
        # Apply document limits
        max_chunks = DocumentConfig.MAX_CHUNKS_PER_DOCUMENT
        if len(document_chunks) > max_chunks:
            logger.warning(f"Document has {len(document_chunks)} chunks, "
                          f"limiting to {max_chunks}")
            document_chunks = document_chunks[:max_chunks]
        
        # Process in batches
        for i in range(0, len(document_chunks), self.batch_size):
            batch = document_chunks[i:i + self.batch_size]
            batch_end = min(i + self.batch_size, len(document_chunks))
            
            logger.info(f"Processing batch {i//self.batch_size + 1}/"
                       f"{(len(document_chunks) + self.batch_size - 1)//self.batch_size} "
                       f"(chunks {i+1}-{batch_end})")
            
            batch_results = []
            
            # Process each chunk in the batch
            for chunk_index, chunk in enumerate(batch):
                current_chunk_index = i + chunk_index
                chunk_position = chunk.get('position', f'Chunk {current_chunk_index + 1}')
                
                logger.debug(f"Analyzing chunk {current_chunk_index+1}: {chunk_position}")
                
                # Find relevant regulations
                similar_regulations = self.embeddings.find_similar(chunk["text"])
                
                try:
                    # Analyze compliance
                    chunk_result = self.llm.analyze_compliance(chunk, similar_regulations)
                    
                    # Ensure we have a valid result
                    if chunk_result is None:
                        logger.warning("LLM analysis returned None, creating empty result")
                        chunk_result = {
                            "issues": [],
                            "position": chunk_position,
                            "text": chunk["text"]
                        }
                    
                    # Add chunk info to result
                    chunk_result.update({
                        "chunk_index": current_chunk_index,
                        "position": chunk_position,
                        "text": chunk["text"]
                    })
                    
                    # Report issues found
                    issues = chunk_result.get("issues", [])
                    if issues:
                        logger.debug(f"Found {len(issues)} issues in chunk {current_chunk_index+1}")
                    
                    batch_results.append(chunk_result)
                    
                except Exception as e:
                    logger.error(f"Error analyzing chunk {current_chunk_index+1}: {e}")
                    # Create empty result to avoid breaking the analysis
                    empty_result = {
                        "chunk_index": current_chunk_index,
                        "position": chunk_position,
                        "text": chunk["text"],
                        "issues": [],
                        "error": str(e)
                    }
                    batch_results.append(empty_result)
            
            all_chunk_results.extend(batch_results)
            
        logger.info(f"Batch analysis complete: processed {len(all_chunk_results)} chunks")
        return all_chunk_results
    
    def classify_chunks(self, document_chunks: List[Dict[str, Any]]) -> Tuple[List[Tuple], List[Tuple]]:
        """
        Classify document chunks by compliance risk level.
        
        Args:
            document_chunks: List of chunks to classify
            
        Returns:
            Tuple of (analyze_chunks, skip_chunks)
        """
        analyze_chunks = []
        skip_chunks = []
        
        for i, chunk in enumerate(document_chunks):
            chunk_text = chunk["text"].lower()
            chunk_position = chunk.get("position", "Unknown")
            
            # Check minimum section length
            if len(chunk_text) < ProgressiveConfig.MIN_SECTION_LENGTH:
                logger.debug(f"Chunk {i+1} ({chunk_position}): SKIP (too short: {len(chunk_text)} chars)")
                skip_chunks.append((i, chunk, []))
                continue
            
            # Calculate risk scores
            data_score = self._calculate_data_score(chunk_text)
            regulatory_score = self._calculate_regulatory_score(chunk_text)
            risk_score = self._calculate_risk_score(chunk_text)
            
            total_score = data_score + regulatory_score + risk_score
            
            # Determine if chunk should be analyzed
            should_analyze, reason = self._should_analyze_chunk(
                total_score, data_score, regulatory_score, risk_score, chunk_text
            )
            
            logger.debug(f"Chunk {i+1} ({chunk_position}): "
                        f"{'ANALYZE' if should_analyze else 'SKIP'} - {reason}")
            
            if should_analyze:
                analyze_chunks.append((i, chunk, []))
            else:
                skip_chunks.append((i, chunk, []))
        
        return analyze_chunks, skip_chunks
    
    def process_chunks(self, chunks: List[Tuple], should_analyze: bool) -> List[Dict[str, Any]]:
        """
        Process chunks with specified analysis level.
        
        Args:
            chunks: List of (index, chunk, metadata) tuples
            should_analyze: Whether to perform full LLM analysis
            
        Returns:
            List of processed chunk results
        """
        if not chunks:
            return []
        
        action = "Analyzing" if should_analyze else "Skipping analysis for"
        logger.info(f"{action} {len(chunks)} chunks")
        
        result_chunks = []
        
        for i, chunk, _ in chunks:
            chunk_position = chunk.get("position", "Unknown")
            
            if should_analyze:
                logger.debug(f"Analyzing chunk {i+1}: {chunk_position}")
                
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
                        logger.debug(f"Found {len(issues)} issues in chunk {i+1}")
                        
                except Exception as e:
                    logger.error(f"Error analyzing chunk {i+1}: {e}")
                    # Create empty result
                    result_chunks.append({
                        "chunk_index": i,
                        "position": chunk_position,
                        "text": chunk["text"],
                        "issues": [],
                        "should_analyze": True,
                        "error": str(e)
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
    
    def _load_framework_terms(self, term_type: str) -> List[str]:
        """Load framework-specific terms or use generic defaults."""
        try:
            # Try to load from framework-specific config
            script_dir = Path(__file__).parent.parent
            terms_file = script_dir / "knowledge_base" / self.regulation_framework / f"{term_type}.txt"
            
            if terms_file.exists():
                with open(terms_file, 'r', encoding='utf-8') as f:
                    terms = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    logger.debug(f"Loaded {len(terms)} {term_type} for {self.regulation_framework}")
                    return terms
        except Exception as e:
            logger.debug(f"Could not load {term_type} for {self.regulation_framework}: {e}")
        
        # Framework-agnostic fallback terms
        return self._get_generic_terms(term_type)
    
    def _get_generic_terms(self, term_type: str) -> List[str]:
        """Get generic terms that work across regulation frameworks."""
        term_sets = {
            "data_terms": [
                "information", "record", "file", "database", "document",
                "collect", "store", "maintain", "handle", "manage", 
                "entity", "individual", "organization", "business",
                "system", "process", "procedure"
            ],
            "regulatory_keywords": [
                "compliance", "regulation", "legal", "lawful", "requirement",
                "standard", "rule", "policy", "procedure", "guideline",
                "obligation", "responsibility", "requirement", "mandate",
                "violation", "breach", "non-compliance", "infringement",
                "audit", "inspection", "assessment", "review"
            ],
            "high_risk_patterns": [
                "non-compliant", "violation", "breach", "illegal",
                "unauthorized", "improper", "inadequate", "insufficient",
                "failed", "missing", "absent", "lacking"
            ],
            "priority_keywords": [
                "compliance", "violation", "breach", "requirement", "standard"
            ]
        }
        
        return term_sets.get(term_type, [])
    
    def _calculate_data_score(self, chunk_text: str) -> int:
        """Calculate data-related score for chunk."""
        score = 0
        for term in self.data_terms:
            count = chunk_text.count(term)
            score += count * ProgressiveConfig.DATA_TERM_WEIGHT
        return score
    
    def _calculate_regulatory_score(self, chunk_text: str) -> int:
        """Calculate regulatory-related score for chunk."""
        score = 0
        for keyword in self.regulatory_keywords:
            count = chunk_text.count(keyword)
            # Give priority keywords extra weight
            if keyword in self.priority_keywords:
                score += count * (ProgressiveConfig.REGULATORY_TERM_WEIGHT * 1.5)
            else:
                score += count * ProgressiveConfig.REGULATORY_TERM_WEIGHT
        return score
    
    def _calculate_risk_score(self, chunk_text: str) -> int:
        """Calculate risk-related score for chunk."""
        score = 0
        for pattern in self.high_risk_patterns:
            if re.search(pattern, chunk_text):
                score += ProgressiveConfig.HIGH_RISK_PATTERN_WEIGHT
        return score
    
    def _should_analyze_chunk(self, total_score: int, data_score: int, 
                             regulatory_score: int, risk_score: int, 
                             chunk_text: str) -> Tuple[bool, str]:
        """
        Determine if a chunk should be analyzed based on various criteria.
        
        Returns:
            Tuple of (should_analyze, reason)
        """
        # High-risk patterns always get analyzed
        if risk_score >= ProgressiveConfig.HIGH_RISK_PATTERN_WEIGHT:
            return True, f"high-risk patterns (risk: {risk_score})"
        
        # High total score
        if total_score >= ProgressiveConfig.HIGH_RISK_THRESHOLD:
            return True, f"high score (total: {total_score})"
        
        # Mixed content with reasonable scores
        if data_score >= 4 and regulatory_score >= 2:
            return True, f"mixed content (data: {data_score}, reg: {regulatory_score})"
        
        # Large sections with medium relevance
        if len(chunk_text) > 2000 and total_score >= ProgressiveConfig.MEDIUM_RISK_THRESHOLD:
            return True, f"large section with relevance (size: {len(chunk_text)}, score: {total_score})"
        
        # Technical sections with relevant terms
        tech_terms = ["system", "process", "procedure", "method", "implementation"]
        relevant_terms = self.data_terms[:5]  # Use first 5 data terms
        
        if any(tech_term in chunk_text for tech_term in tech_terms):
            if any(relevant_term in chunk_text for relevant_term in relevant_terms):
                return True, "technical + relevant content"
        
        # Default to skip
        return False, f"low relevance (total: {total_score})"