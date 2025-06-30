import re
from typing import List, Dict, Any, Tuple
from collections import Counter
from config import config

class ProgressiveAnalyzer:
    """Enhanced progressive analysis using regulation handler classification terms."""
    
    def __init__(self, llm_handler, embeddings_handler, regulation_framework, batch_size=1, debug=False):
        """Initialize progressive analyzer with enhanced framework-specific scoring."""
        
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
            # Basic classification terms (existing)
            self.data_terms = handler.get_classification_terms("data_terms")
            self.regulatory_keywords = handler.get_classification_terms("regulatory_keywords")
            self.high_risk_patterns = handler.get_classification_terms("high_risk_patterns")
            self.priority_keywords = handler.get_classification_terms("priority_keywords")
            
            # Enhanced classification terms (new)
            self.scoring_weights = self._load_scoring_weights(handler)
            self.high_value_phrases = self._load_high_value_phrases(handler)
            self.context_patterns = self._load_context_patterns(handler)
            
        except Exception as e:
            raise RuntimeError(f"Failed to load classification terms: {e}")
        
        assert all([self.data_terms, self.regulatory_keywords, self.high_risk_patterns]), \
               "Missing classification terms"
        
        if self.debug:
            self._debug_loaded_terms()
    
    def _load_scoring_weights(self, handler) -> Dict[str, float]:
        """Load framework-specific scoring weights."""
        default_weights = {
            "data_terms": 1.0,
            "regulatory_keywords": 1.5,
            "high_risk_patterns": 5.0,
            "priority_keywords": 2.0,
            "phrase_match_bonus": 2.0,
            "context_bonus": 1.5,
            "negation_penalty": -2.0
        }
        
        # Try to get framework-specific weights
        try:
            if hasattr(handler, 'get_scoring_weights'):
                framework_weights = handler.get_scoring_weights()
                if framework_weights:
                    default_weights.update(framework_weights)
        except Exception as e:
            if self.debug:
                print(f"Warning: Could not load scoring weights: {e}")
        
        return default_weights
    
    def _load_high_value_phrases(self, handler) -> List[str]:
        """Load framework-specific high-value phrases."""
        try:
            if hasattr(handler, 'get_high_value_phrases'):
                phrases = handler.get_high_value_phrases()
                if phrases:
                    return phrases
        except Exception as e:
            if self.debug:
                print(f"Warning: Could not load high value phrases: {e}")
        
        # Fallback to framework-specific defaults
        return self._get_default_phrases()
    
    def _load_context_patterns(self, handler) -> List[Dict[str, Any]]:
        """Load framework-specific context patterns."""
        try:
            if hasattr(handler, 'get_context_patterns'):
                patterns = handler.get_context_patterns()
                if patterns:
                    return patterns
        except Exception as e:
            if self.debug:
                print(f"Warning: Could not load context patterns: {e}")
        
        return []
    
    def _get_default_phrases(self) -> List[str]:
        """Get default framework-specific phrases."""
        if self.regulation_framework == "gdpr":
            return [
                "without consent", "automatic opt-in", "bundled consent",
                "indefinite retention", "third party sharing", "data monetization",
                "no deletion rights", "forced consent", "pre-selected checkboxes",
                "without explicit consent", "automatic data processing"
            ]
        elif self.regulation_framework == "hipaa":
            return [
                "without authorization", "no business associate agreement",
                "unencrypted phi", "basic security measures", "no breach notification",
                "unlimited phi access", "vendor access without baa", "plain text phi",
                "shared without consent", "disposed in trash"
            ]
        else:
            return [
                "without permission", "automatic processing", "no user control",
                "indefinite storage", "third party access", "minimal security"
            ]
    
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
                "should_analyze": True,
                "risk_score": 0,
                "score_breakdown": {}
            })
            
            results.append(chunk_result)
        
        return results
    
    def classify_chunks(self, document_chunks: List[Dict[str, Any]]) -> Tuple[List[Tuple], List[Tuple]]:
        """Enhanced chunk classification with sophisticated scoring."""
        
        analyze_chunks = []
        skip_chunks = []
        
        for i, chunk in enumerate(document_chunks):
            chunk_text = chunk.get("text", "")
            
            # Skip very short chunks
            if len(chunk_text) < 150:
                skip_chunks.append((i, chunk, {"reason": "too_short", "total_score": 0}))
                continue
            
            # Calculate enhanced score
            score_details = self._calculate_enhanced_score(chunk_text)
            total_score = score_details["total_score"]
            
            if self.debug:
                pos = chunk.get("position", f"Chunk {i+1}")
                print(f"Score {pos}: {total_score:.2f} - {score_details}")
            
            # Classify based on threshold
            if total_score >= config.high_risk_threshold:
                analyze_chunks.append((i, chunk, score_details))
            else:
                skip_chunks.append((i, chunk, score_details))
        
        return analyze_chunks, skip_chunks
    
    def _calculate_enhanced_score(self, text: str) -> Dict[str, Any]:
        """Calculate enhanced framework-specific risk score."""
        text_lower = text.lower()
        text_sentences = self._split_into_sentences(text)
        
        score_breakdown = {
            "data_score": 0.0,
            "regulatory_score": 0.0, 
            "risk_pattern_score": 0.0,
            "priority_score": 0.0,
            "phrase_bonus": 0.0,
            "context_bonus": 0.0,
            "negation_penalty": 0.0,
            "total_score": 0.0
        }
        
        # 1. Basic term counting (enhanced with weights)
        score_breakdown["data_score"] = self._count_terms_weighted(
            text_lower, self.data_terms
        ) * self.scoring_weights["data_terms"]
        
        score_breakdown["regulatory_score"] = self._count_terms_weighted(
            text_lower, self.regulatory_keywords
        ) * self.scoring_weights["regulatory_keywords"]
        
        score_breakdown["risk_pattern_score"] = self._count_terms_weighted(
            text_lower, self.high_risk_patterns
        ) * self.scoring_weights["high_risk_patterns"]
        
        score_breakdown["priority_score"] = self._count_terms_weighted(
            text_lower, self.priority_keywords
        ) * self.scoring_weights["priority_keywords"]
        
        # 2. Enhanced phrase matching
        score_breakdown["phrase_bonus"] = self._calculate_phrase_matches(
            text_lower
        ) * self.scoring_weights["phrase_match_bonus"]
        
        # 3. Context-aware scoring
        score_breakdown["context_bonus"] = self._calculate_context_score(
            text_sentences
        ) * self.scoring_weights["context_bonus"]
        
        # 4. Negation detection (reduces false positives)
        score_breakdown["negation_penalty"] = self._detect_negations(
            text_sentences
        ) * self.scoring_weights["negation_penalty"]
        
        # Calculate total
        score_breakdown["total_score"] = sum([
            score_breakdown["data_score"],
            score_breakdown["regulatory_score"], 
            score_breakdown["risk_pattern_score"],
            score_breakdown["priority_score"],
            score_breakdown["phrase_bonus"],
            score_breakdown["context_bonus"],
            score_breakdown["negation_penalty"]
        ])
        
        return score_breakdown
    
    def _count_terms_weighted(self, text: str, terms: List[str]) -> float:
        """Count terms with enhanced weighting."""
        if not terms:
            return 0.0
        
        total_score = 0.0
        
        for term in terms:
            term_lower = term.lower()
            
            # Exact phrase match gets higher weight
            if term_lower in text:
                phrase_count = text.count(term_lower)
                # Longer phrases get higher weight
                weight = len(term_lower.split()) * phrase_count
                total_score += weight
        
        return total_score
    
    def _calculate_phrase_matches(self, text: str) -> float:
        """Calculate bonus for multi-word phrase matches."""
        bonus = 0.0
        
        for phrase in self.high_value_phrases:
            if phrase.lower() in text:
                # Longer phrases get exponentially higher bonus
                phrase_length = len(phrase.split())
                bonus += phrase_length ** 1.5
        
        return bonus
    
    def _calculate_context_score(self, sentences: List[str]) -> float:
        """Calculate context-aware scoring bonus."""
        context_bonus = 0.0
        
        # Look for sentences that combine data terms + risk patterns
        data_terms_lower = [term.lower() for term in self.data_terms]
        risk_patterns_lower = [pattern.lower() for pattern in self.high_risk_patterns]
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            has_data_term = any(term in sentence_lower for term in data_terms_lower)
            has_risk_pattern = any(pattern in sentence_lower for pattern in risk_patterns_lower)
            
            if has_data_term and has_risk_pattern:
                # This sentence combines data handling with risky practices
                context_bonus += 3.0
            elif has_data_term or has_risk_pattern:
                context_bonus += 1.0
        
        # Apply context patterns if available
        for pattern in self.context_patterns:
            data_indicators = pattern.get("data_indicators", [])
            risk_indicators = pattern.get("risk_indicators", [])
            weight_multiplier = pattern.get("weight_multiplier", 1.0)
            
            for sentence in sentences:
                sentence_lower = sentence.lower()
                has_data = any(indicator.lower() in sentence_lower for indicator in data_indicators)
                has_risk = any(indicator.lower() in sentence_lower for indicator in risk_indicators)
                
                if has_data and has_risk:
                    context_bonus += weight_multiplier
        
        return context_bonus
    
    def _detect_negations(self, sentences: List[str]) -> float:
        """Detect negations that might indicate compliance (reduce false positives)."""
        negation_words = ["not", "never", "no", "won't", "don't", "can't", "cannot", "will not"]
        compliance_words = ["violate", "breach", "unauthorized", "illegal", "improper", "share", "sell"]
        
        penalty = 0.0
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            words = sentence_lower.split()
            
            for i, word in enumerate(words):
                if word in negation_words:
                    # Look for compliance words near negations
                    window = words[max(0, i-3):min(len(words), i+4)]
                    if any(comp_word in ' '.join(window) for comp_word in compliance_words):
                        penalty += 1.0  # This is likely a compliance statement
        
        return penalty
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for context analysis."""
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
    
    def process_chunks(self, chunks: List[Tuple], should_analyze: bool) -> List[Dict[str, Any]]:
        """Process chunks with specified analysis level and enhanced metadata."""
        
        results = []
        
        for chunk_tuple in chunks:
            i, chunk = chunk_tuple[0], chunk_tuple[1]
            score_details = chunk_tuple[2] if len(chunk_tuple) > 2 else {}
            chunk_position = chunk.get("position", f"Section {i+1}")
            
            if should_analyze:
                # Full LLM analysis
                similar_regulations = self.embeddings.find_similar(chunk["text"])
                chunk_result = self.llm.analyze_compliance(chunk, similar_regulations)
                
                chunk_result.update({
                    "chunk_index": i,
                    "position": chunk_position,
                    "text": chunk["text"],
                    "should_analyze": True,
                    "risk_score": score_details.get('total_score', 0),
                    "score_breakdown": score_details
                })
                
                results.append(chunk_result)
                
                if self.debug:
                    issues = len(chunk_result.get("issues", []))
                    score = score_details.get('total_score', 0)
                    print(f"Analyzed {chunk_position}: {issues} issues (score: {score:.2f})")
            
            else:
                # Skip analysis
                skip_result = {
                    "chunk_index": i,
                    "position": chunk_position,
                    "text": chunk["text"],
                    "issues": [],
                    "should_analyze": False,
                    "risk_score": score_details.get('total_score', 0),
                    "score_breakdown": score_details
                }
                results.append(skip_result)
                
                if self.debug:
                    score = score_details.get('total_score', 0)
                    print(f"Skipped {chunk_position} (score: {score:.2f})")
        
        return results
    
    def _debug_loaded_terms(self):
        """Debug output for loaded terms."""
        print(f"\n=== Enhanced Progressive Analysis for {self.regulation_framework.upper()} ===")
        
        term_categories = {
            "Data Terms": self.data_terms,
            "Regulatory Keywords": self.regulatory_keywords,
            "High Risk Patterns": self.high_risk_patterns,
            "Priority Keywords": self.priority_keywords,
            "High Value Phrases": self.high_value_phrases
        }
        
        for category, terms in term_categories.items():
            print(f"{category}: {len(terms)} terms")
            if terms and len(terms) <= 3:
                print(f"  Sample: {terms}")
            elif terms:
                print(f"  Sample: {terms[:3]}... (+{len(terms)-3} more)")
        
        print(f"\nScoring Weights:")
        for weight_name, weight_value in self.scoring_weights.items():
            print(f"  {weight_name}: {weight_value}")
        
        print(f"Context Patterns: {len(self.context_patterns)}")
        print("=" * 70)
    
    def get_scoring_explanation(self, chunk_text: str) -> str:
        """Get human-readable explanation of scoring."""
        score_details = self._calculate_enhanced_score(chunk_text)
        
        explanation = f"Framework: {self.regulation_framework.upper()}\n"
        explanation += f"Total Score: {score_details['total_score']:.2f}\n"
        explanation += f"Threshold: {config.high_risk_threshold}\n"
        explanation += f"Decision: {'ANALYZE' if score_details['total_score'] >= config.high_risk_threshold else 'SKIP'}\n\n"
        
        explanation += "Score Breakdown:\n"
        for component, score in score_details.items():
            if component != "total_score" and score != 0:
                explanation += f"  {component}: {score:.2f}\n"
        
        return explanation