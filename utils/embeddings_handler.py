# utils/embeddings_handler.py

import numpy as np
import re
import yaml
from typing import List, Dict, Any, Optional, Set
from sentence_transformers import SentenceTransformer
import faiss
from pathlib import Path

class EmbeddingsHandler:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embeddings handler with proper error handling."""
        if not model_name or not model_name.strip():
            raise ValueError("model_name cannot be empty")
        
        self.model_name = model_name
        self.model = None
        self.index = None
        self.texts = []
        self.metadata = []
        
        # Initialize the model with proper error handling
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as e:
            # Check if it's a network/download issue
            if "ConnectTimeout" in str(e) or "ReadTimeout" in str(e):
                raise RuntimeError(
                    f"Failed to download embedding model '{model_name}': Network timeout\n"
                    f"Solutions:\n"
                    f"1. Check internet connection\n"
                    f"2. Download model manually: python -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('{model_name}')\"\n"
                    f"3. Use a different model name"
                )
            elif "ValueError" in str(e) and "not a valid model" in str(e):
                raise ValueError(
                    f"Invalid embedding model name: '{model_name}'\n"
                    f"Try a valid SentenceTransformer model like:\n"
                    f"- all-MiniLM-L6-v2 (default, fast)\n"
                    f"- all-mpnet-base-v2 (better quality)\n"
                    f"- multi-qa-MiniLM-L6-cos-v1 (question-answering optimized)"
                )
            else:
                raise RuntimeError(f"Failed to load embedding model '{model_name}': {e}")
        
    def create_embeddings(self, texts: list) -> np.ndarray:
        """Create embeddings for a list of texts with validation."""
        if not texts:
            raise ValueError("texts list cannot be empty")
        
        if not isinstance(texts, list):
            raise ValueError("texts must be a list")
        
        # Filter out empty texts
        non_empty_texts = [text for text in texts if text and str(text).strip()]
        if not non_empty_texts:
            raise ValueError("All texts are empty after filtering")
        
        if len(non_empty_texts) != len(texts):
            print(f"Warning: Filtered out {len(texts) - len(non_empty_texts)} empty texts")
        
        try:
            embeddings = self.model.encode(non_empty_texts)
            if embeddings.size == 0:
                raise RuntimeError("Model returned empty embeddings")
            return embeddings
        except Exception as e:
            raise RuntimeError(f"Failed to create embeddings: {e}")
    
    def build_knowledge_base(self, file_path: str) -> None:
        """Build knowledge base from a text file with validation and metadata extraction."""
        if not file_path:
            raise ValueError("file_path cannot be empty")
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Knowledge base file not found: {file_path}")
        
        if file_path.stat().st_size == 0:
            raise ValueError(f"Knowledge base file is empty: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except UnicodeDecodeError as e:
            raise ValueError(f"Knowledge base file encoding error: {e}. File must be UTF-8 encoded.")
        except Exception as e:
            raise RuntimeError(f"Failed to read knowledge base file: {e}")
        
        if not content.strip():
            raise ValueError(f"Knowledge base file contains no content: {file_path}")
        
        # Process the knowledge base with enhanced structure
        knowledge_base = []
        current_article = {"text": "", "id": "", "title": "", "related_concepts": []}
        
        lines = content.split('\n')
        if not lines:
            raise ValueError("Knowledge base file contains no lines")
        
        for line_num, line in enumerate(lines, 1):
            try:
                if self._is_new_article(line):
                    # Save previous article if exists
                    if current_article["text"].strip():
                        knowledge_base.append(current_article)
                        
                    # Parse article ID and title
                    parts = line.split(' - ', 1)
                    article_id = parts[0].strip()
                    title = parts[1].strip() if len(parts) > 1 else ""
                    
                    # Initialize new article
                    current_article = {
                        "text": line + "\n",
                        "id": article_id,
                        "title": title,
                        "related_concepts": self._extract_concepts(title)
                    }
                else:
                    current_article["text"] += line + "\n"
                    # Incrementally update related concepts
                    current_article["related_concepts"].extend(
                        self._extract_concepts(line)
                    )
            except Exception as e:
                print(f"Warning: Error processing line {line_num}: {e}")
                continue
                
        # Add final article
        if current_article["text"].strip():
            knowledge_base.append(current_article)
        
        if not knowledge_base:
            raise ValueError(f"No articles found in knowledge base file: {file_path}")
        
        # Create embeddings and store both texts and metadata
        self.texts = [article["text"] for article in knowledge_base]
        self.metadata = knowledge_base
        
        if not self.texts:
            raise ValueError("No text content extracted from articles")
        
        try:
            embeddings = self.create_embeddings(self.texts)
            self.build_faiss_index(embeddings)
        except Exception as e:
            raise RuntimeError(f"Failed to build embeddings from knowledge base: {e}")
        
        print(f"Built knowledge base with {len(knowledge_base)} articles from {file_path}")
    
    def _is_new_article(self, line: str) -> bool:
        """Determine if a line starts a new article or section."""
        if not line or not line.strip():
            return False
        
        # Check for common article/section patterns across regulations - made framework-agnostic
        patterns = [
            r'^(Article|Section|Rule|Standard|Requirement|Principle|Regulation|Part|Chapter)\s+\S+',
            r'^\d+\.\s*[A-Z]',  # Numbered sections like "1. Data Protection"
            r'^[A-Z][A-Z\s]+[A-Z]$',  # ALL CAPS headers
            r'^\d+\.\d+\s+',  # Subsections like "1.1 Overview"
        ]
        
        line_stripped = line.strip()
        for pattern in patterns:
            if re.match(pattern, line_stripped):
                return True
        return False
    
    def build_faiss_index(self, embeddings: np.ndarray) -> None:
        """Build a FAISS index from embeddings with validation."""
        if embeddings is None:
            raise ValueError("embeddings cannot be None")
        
        if not isinstance(embeddings, np.ndarray):
            raise ValueError("embeddings must be a numpy array")
        
        if embeddings.size == 0:
            raise ValueError("embeddings array is empty")
        
        if len(embeddings.shape) != 2:
            raise ValueError(f"embeddings must be 2D array, got shape: {embeddings.shape}")
        
        dimension = embeddings.shape[1]
        if dimension <= 0:
            raise ValueError(f"Invalid embedding dimension: {dimension}")
        
        try:
            self.index = faiss.IndexFlatL2(dimension)
            self.index.add(embeddings)
        except Exception as e:
            raise RuntimeError(f"Failed to build FAISS index: {e}")
        
        print(f"Built FAISS index with {embeddings.shape[0]} vectors of dimension {dimension}")
    
    def _extract_concepts(self, text: str) -> List[str]:
        """Extract key regulatory concepts without framework-specific knowledge."""
        if not text:
            return []
        
        concepts = []
        
        # Generic regulatory concepts that apply across frameworks
        concept_patterns = [
            # Data and information concepts
            r'data', r'information', r'record', r'database', r'file',
            # Rights and responsibilities  
            r'right', r'obligation', r'responsibility', r'duty', r'requirement',
            # Process concepts
            r'process', r'collect', r'store', r'transfer', r'share', r'disclose',
            # Access and control
            r'access', r'control', r'manage', r'restrict', r'limit',
            # Security and protection
            r'security', r'protect', r'safeguard', r'secure', r'confidential',
            # Compliance and legal
            r'compliance', r'legal', r'lawful', r'authorize', r'permit',
            # Notice and transparency
            r'notice', r'notification', r'inform', r'disclose', r'transparency',
            # Individual/entity concepts
            r'individual', r'person', r'entity', r'organization', r'controller',
            # Time-related concepts
            r'period', r'duration', r'retention', r'storage', r'delete',
            # Consent and agreement
            r'consent', r'agree', r'approve', r'authorize', r'permit'
        ]
        
        text_lower = text.lower()
        for pattern in concept_patterns:
            if re.search(r'\b' + pattern + r'\b', text_lower):
                concepts.append(pattern)
                
        return list(set(concepts))
        
    def find_similar(self, query: str, k: int = 3) -> list:
        """Find k most similar texts to query with proper error handling."""
        if not query:
            raise ValueError("Query cannot be empty")
        
        if not query.strip():
            raise ValueError("Query cannot be just whitespace")
        
        if not isinstance(k, int) or k <= 0:
            raise ValueError("k must be a positive integer")
        
        if not self.index:
            raise RuntimeError(
                "Embeddings index not built. Call build_knowledge_base() first.\n"
                "Make sure the knowledge base file exists and contains valid articles."
            )
        
        if not self.texts:
            raise RuntimeError("No texts available. Knowledge base may not be loaded properly.")
        
        if k > len(self.texts):
            print(f"Warning: Requested k={k} but only {len(self.texts)} texts available. Using k={len(self.texts)}")
            k = len(self.texts)
        
        try:
            query_embedding = self.model.encode([query])
            if query_embedding.size == 0:
                raise RuntimeError("Failed to create query embedding")
        except Exception as e:
            raise RuntimeError(f"Failed to encode query: {e}")
        
        try:
            distances, indices = self.index.search(query_embedding, k)
        except Exception as e:
            raise RuntimeError(f"FAISS search failed: {e}")
        
        if len(distances) == 0 or len(indices) == 0:
            raise RuntimeError("FAISS search returned no results")
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(self.texts):
                print(f"Warning: Invalid index {idx} returned by FAISS search")
                continue
                
            article_metadata = self.metadata[idx] if idx < len(self.metadata) else {}
            
            result = {
                "text": self.texts[idx],
                "distance": float(distances[0][i]),
                "id": article_metadata.get("id", f"Article_{idx}"),
                "title": article_metadata.get("title", ""),
                "related_concepts": article_metadata.get("related_concepts", [])
            }
            
            results.append(result)
        
        if not results:
            raise RuntimeError("No valid results found after filtering")
                
        return results