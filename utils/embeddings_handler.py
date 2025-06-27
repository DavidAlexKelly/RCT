"""
Embeddings Handler Module

Handles vector embeddings and RAG (Retrieval-Augmented Generation) for regulation lookup.
Uses sentence transformers for embedding generation and FAISS for similarity search.
"""

import numpy as np
import re
import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class EmbeddingsHandler:
    """
    Handles vector embeddings for regulation retrieval.
    
    Creates embeddings for regulation text and provides similarity search
    to find relevant regulations for document chunks.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """
        Initialize the embeddings handler.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        try:
            from sentence_transformers import SentenceTransformer
            import faiss
        except ImportError:
            raise ImportError("Required packages missing. Install with: "
                            "pip install sentence-transformers faiss-cpu")
        
        self.model = SentenceTransformer(model_name)
        self.index: Optional[Any] = None
        self.texts: List[str] = []
        self.metadata: List[Dict[str, Any]] = []
        
        logger.info(f"EmbeddingsHandler initialized with model: {model_name}")
        
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Create embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            NumPy array of embeddings
        """
        if not texts:
            logger.warning("Empty text list provided for embedding creation")
            return np.array([])
        
        logger.debug(f"Creating embeddings for {len(texts)} texts")
        return self.model.encode(texts)
    
    def build_knowledge_base(self, file_path: str) -> None:
        """
        Build knowledge base from a regulation text file.
        
        Args:
            file_path: Path to the regulation file (articles.txt)
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If no valid articles are found
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Knowledge base file not found: {file_path}")
        
        logger.info(f"Building knowledge base from: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Process the knowledge base with enhanced structure
        knowledge_base = []
        current_article = {"text": "", "id": "", "title": "", "related_concepts": []}
        
        for line in content.split('\n'):
            if self._is_new_article(line):
                # Save previous article if exists
                if current_article["text"]:
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
                
        # Add final article
        if current_article["text"]:
            knowledge_base.append(current_article)
            
        if not knowledge_base:
            raise ValueError(f"No valid articles found in {file_path}")
        
        # Create embeddings and store both texts and metadata
        self.texts = [article["text"] for article in knowledge_base]
        self.metadata = knowledge_base
        
        logger.info(f"Processed {len(knowledge_base)} articles")
        
        embeddings = self.create_embeddings(self.texts)
        self.build_faiss_index(embeddings)
        
        logger.info("Knowledge base built successfully")
    
    def build_faiss_index(self, embeddings: np.ndarray) -> None:
        """
        Build a FAISS index from embeddings.
        
        Args:
            embeddings: NumPy array of embeddings
        """
        try:
            import faiss
        except ImportError:
            raise ImportError("faiss-cpu package required. Install with: pip install faiss-cpu")
        
        if embeddings.size == 0:
            logger.warning("Empty embeddings array provided")
            return
            
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)
        
        logger.debug(f"Built FAISS index with {embeddings.shape[0]} embeddings, dimension {dimension}")
    
    def find_similar(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Find k most similar texts to query.
        
        Args:
            query: Query text to find similar regulations for
            k: Number of similar results to return
            
        Returns:
            List of dictionaries with similar regulation text and metadata
        """
        if not self.index:
            logger.warning("No FAISS index available for similarity search")
            return []
        
        if not query.strip():
            logger.warning("Empty query provided for similarity search")
            return []
            
        try:
            query_embedding = self.model.encode([query])
            distances, indices = self.index.search(query_embedding, k)
            
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.texts) and idx >= 0:
                    article_metadata = self.metadata[idx] if idx < len(self.metadata) else {}
                    
                    results.append({
                        "text": self.texts[idx],
                        "distance": float(distances[0][i]),
                        "id": article_metadata.get("id", ""),
                        "title": article_metadata.get("title", ""),
                        "related_concepts": article_metadata.get("related_concepts", [])
                    })
            
            logger.debug(f"Found {len(results)} similar regulations for query")
            return results
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []
        
    def _is_new_article(self, line: str) -> bool:
        """
        Determine if a line starts a new article or section.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line starts a new article
        """
        # Framework-agnostic patterns for detecting articles/sections
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
    
    def _extract_concepts(self, text: str) -> List[str]:
        """
        Extract key regulatory concepts from text.
        
        Args:
            text: Text to extract concepts from
            
        Returns:
            List of relevant regulatory concepts
        """
        if not text:
            return []
            
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
        concepts = []
        
        for pattern in concept_patterns:
            if re.search(r'\b' + pattern + r'\b', text_lower):
                concepts.append(pattern)
                
        return list(set(concepts))