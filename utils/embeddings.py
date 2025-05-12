import os
import numpy as np
import re
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import faiss

class EmbeddingsHandler:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.texts = []
        self.metadata = []
        
    def create_embeddings(self, texts: list) -> np.ndarray:
        """Create embeddings for a list of texts."""
        return self.model.encode(texts)
    
    def build_knowledge_base(self, file_path: str) -> None:
        """Build enhanced knowledge base from a text file with metadata extraction."""
        with open(file_path, 'r') as file:
            content = file.read()
            
        # Process the knowledge base with enhanced structure
        knowledge_base = []
        current_article = {"text": "", "id": "", "title": "", "related_concepts": []}
        
        for line in content.split('\n'):
            if line.startswith('Article') or line.startswith('Section'):
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
            
        # Create embeddings and store both texts and metadata
        self.texts = [article["text"] for article in knowledge_base]
        self.metadata = knowledge_base
        embeddings = self.create_embeddings(self.texts)
        self.build_faiss_index(embeddings)
    
    def build_faiss_index(self, embeddings: np.ndarray) -> None:
        """Build a FAISS index from embeddings."""
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)
    
    def _extract_concepts(self, text):
        """Extract key regulatory concepts without hardcoded knowledge."""
        # Use general patterns to identify concepts
        concepts = []
        concept_patterns = [
            r'consent', r'data subject', r'personal data', r'processing',
            r'controller', r'processor', r'legitimate interest', r'transparency',
            r'retention', r'erasure', r'right to', r'information', r'purpose',
            r'privacy', r'security', r'breach', r'notice', r'collection',
            r'disclosure', r'sharing', r'opt-in', r'opt-out', r'confidential'
        ]
        
        for pattern in concept_patterns:
            if re.search(pattern, text.lower()):
                concepts.append(pattern)
                
        return list(set(concepts))
        
    def find_similar(self, query: str, k: int = 3) -> list:
        """Find k most similar texts to query with enhanced metadata."""
        query_embedding = self.model.encode([query])
        distances, indices = self.index.search(query_embedding, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.texts):
                article_metadata = self.metadata[idx] if idx < len(self.metadata) else {}
                
                results.append({
                    "text": self.texts[idx],
                    "distance": float(distances[0][i]),
                    "id": article_metadata.get("id", ""),
                    "title": article_metadata.get("title", ""),
                    "related_concepts": article_metadata.get("related_concepts", [])
                })
                
        return results
    
    def get_document_wide_concepts(self, document_text: str) -> list:
        """Extract concepts from the whole document for better context."""
        # Use the same concept extraction for consistency
        return self._extract_concepts(document_text)