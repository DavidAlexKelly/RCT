import numpy as np
import re
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import faiss
from pathlib import Path

class EmbeddingsHandler:
    """Simplified embeddings handler for regulatory compliance analysis."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embeddings handler."""
        if not model_name or not model_name.strip():
            raise ValueError("model_name cannot be empty")
        
        self.model_name = model_name
        self.model = None
        self.index = None
        self.texts = []
        self.metadata = []
        
        # Initialize the model
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as e:
            if "ConnectTimeout" in str(e) or "ReadTimeout" in str(e):
                raise RuntimeError(
                    f"Failed to download embedding model '{model_name}': Network timeout\n"
                    f"Solutions:\n"
                    f"1. Check internet connection\n"
                    f"2. Try: python -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('{model_name}')\"\n"
                    f"3. Use a different model name"
                )
            else:
                raise RuntimeError(f"Failed to load embedding model '{model_name}': {e}")
        
        print(f"Embeddings: Loaded {model_name}")
    
    def create_embeddings(self, texts: list) -> np.ndarray:
        """Create embeddings for a list of texts."""
        if not texts:
            raise ValueError("texts list cannot be empty")
        
        # Filter out empty texts
        non_empty_texts = [text for text in texts if text and str(text).strip()]
        if not non_empty_texts:
            raise ValueError("All texts are empty after filtering")
        
        try:
            embeddings = self.model.encode(non_empty_texts)
            if embeddings.size == 0:
                raise RuntimeError("Model returned empty embeddings")
            return embeddings
        except Exception as e:
            raise RuntimeError(f"Failed to create embeddings: {e}")
    
    def build_knowledge_base(self, file_path: str) -> None:
        """Build knowledge base from a text file."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Knowledge base file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read knowledge base file: {e}")
        
        if not content.strip():
            raise ValueError(f"Knowledge base file contains no content: {file_path}")
        
        # Process the knowledge base
        knowledge_base = []
        current_article = {"text": "", "id": "", "title": ""}
        
        lines = content.split('\n')
        for line in lines:
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
                    "title": title
                }
            else:
                current_article["text"] += line + "\n"
                
        # Add final article
        if current_article["text"].strip():
            knowledge_base.append(current_article)
        
        if not knowledge_base:
            raise ValueError(f"No articles found in knowledge base file: {file_path}")
        
        # Create embeddings and store metadata
        self.texts = [article["text"] for article in knowledge_base]
        self.metadata = knowledge_base
        
        embeddings = self.create_embeddings(self.texts)
        self.build_faiss_index(embeddings)
        
        print(f"Knowledge base: {len(knowledge_base)} articles indexed")
    
    def _is_new_article(self, line: str) -> bool:
        """Determine if a line starts a new article or section."""
        if not line or not line.strip():
            return False
        
        # Check for common article/section patterns
        patterns = [
            r'^(Article|Section|Rule|Standard|Requirement|Principle|Regulation|Part|Chapter)\s+\S+',
            r'^\d+\.\s*[A-Z]',  # Numbered sections
            r'^[A-Z][A-Z\s]+[A-Z]$',  # ALL CAPS headers
            r'^\d+\.\d+\s+',  # Subsections
            r'^§\s*\d+'  # Section symbols
        ]
        
        line_stripped = line.strip()
        for pattern in patterns:
            if re.match(pattern, line_stripped):
                return True
        return False
    
    def build_faiss_index(self, embeddings: np.ndarray) -> None:
        """Build a FAISS index from embeddings."""
        if embeddings is None or embeddings.size == 0:
            raise ValueError("Invalid embeddings")
        
        dimension = embeddings.shape[1]
        try:
            self.index = faiss.IndexFlatL2(dimension)
            self.index.add(embeddings)
        except Exception as e:
            raise RuntimeError(f"Failed to build FAISS index: {e}")
        
        print(f"FAISS index: {embeddings.shape[0]} vectors indexed")
    
    def find_similar(self, query: str, k: int = 3) -> list:
        """Find k most similar texts to query."""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if not self.index or not self.texts:
            raise RuntimeError("Knowledge base not loaded. Call build_knowledge_base() first.")
        
        if k > len(self.texts):
            k = len(self.texts)
        
        try:
            query_embedding = self.model.encode([query])
            distances, indices = self.index.search(query_embedding, k)
        except Exception as e:
            raise RuntimeError(f"Search failed: {e}")
        
        results = []
        for i, idx in enumerate(indices[0]):
            if 0 <= idx < len(self.texts):
                article_metadata = self.metadata[idx] if idx < len(self.metadata) else {}
                
                result = {
                    "text": self.texts[idx],
                    "distance": float(distances[0][i]),
                    "id": article_metadata.get("id", f"Article_{idx}"),
                    "title": article_metadata.get("title", "")
                }
                results.append(result)
        
        return results