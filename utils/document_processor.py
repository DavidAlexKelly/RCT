# utils/document_processor.py - Simplified (637 → 180 lines)

import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from config import config

class DocumentProcessor:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None, chunking_method: str = "smart"):
        self.chunk_size = chunk_size or config.chunk_size
        self.chunk_overlap = chunk_overlap or config.chunk_overlap
        self.chunking_method = chunking_method
        
        assert 200 <= self.chunk_size <= 5000, f"Invalid chunk_size: {self.chunk_size}"
        assert 0 <= self.chunk_overlap < self.chunk_size, f"Invalid chunk_overlap: {self.chunk_overlap}"
        assert chunking_method in ["smart", "paragraph", "sentence", "simple"], f"Invalid method: {chunking_method}"
    
    def process_document(self, file_path: str, optimize_chunks: bool = True) -> Dict[str, Any]:
        """Process document and return metadata and chunks."""
        file_path = Path(file_path)
        assert file_path.exists() and file_path.is_file(), f"Invalid file: {file_path}"
        
        # Optimize chunk size based on file size
        if optimize_chunks:
            self._optimize_chunk_size(file_path)
        
        # Extract text
        text = self._extract_text(file_path)
        assert text and text.strip(), f"No text extracted from: {file_path}"
        
        # Create chunks
        chunks = self._create_chunks(text)
        assert chunks, "No chunks created"
        
        # Extract metadata
        metadata = self._extract_metadata(text)
        
        return {"metadata": metadata, "chunks": chunks}
    
    def _extract_text(self, file_path: Path) -> str:
        """Extract text from file based on extension."""
        ext = file_path.suffix.lower()
        
        if ext == '.pdf':
            return self._read_pdf(file_path)
        elif ext in ['.txt', '.md']:
            return self._read_text(file_path)
        else:
            raise ValueError(f"Unsupported format: {ext}")
    
    def _read_pdf(self, file_path: Path) -> str:
        """Extract text from PDF."""
        try:
            import pypdf
        except ImportError:
            raise RuntimeError("PDF support requires: pip install pypdf")
        
        text_parts = []
        with open(file_path, "rb") as file:
            reader = pypdf.PdfReader(file)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():
                    text_parts.append(f"[Page {i + 1}] {text}")
        
        assert text_parts, "No text found in PDF"
        return "\n\n".join(text_parts)
    
    def _read_text(self, file_path: Path) -> str:
        """Extract text from text file."""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as file:
                    text = file.read()
                    assert text.strip(), "Empty text file"
                    return text
            except UnicodeDecodeError:
                continue
        
        raise ValueError(f"Could not decode file with encodings: {encodings}")
    
    def _create_chunks(self, text: str) -> List[Dict[str, Any]]:
        """Create chunks using specified method."""
        methods = {
            "smart": self._smart_chunking,
            "paragraph": self._paragraph_chunking,
            "sentence": self._sentence_chunking,
            "simple": self._simple_chunking
        }
        return methods[self.chunking_method](text)
    
    def _smart_chunking(self, text: str) -> List[Dict[str, Any]]:
        """Smart chunking with section detection."""
        sections = self._detect_sections(text)
        
        if len(sections) > 1 and self._valid_sections(sections):
            return self._section_chunking(sections)
        else:
            return self._paragraph_chunking(text)
    
    def _detect_sections(self, text: str) -> List[Dict[str, str]]:
        """Detect document sections."""
        patterns = [
            r'^(\d+\.\s+[A-Z][^\n]{10,80})$',  # "1. Section Title"
            r'^([A-Z][A-Z\s]{5,50}[A-Z])$',   # "SECTION TITLE"
            r'^(#{1,3}\s+[^\n]+)$',           # "# Headers"
            r'^([A-Z][a-zA-Z\s&]{5,60}:)$'   # "Section:"
        ]
        
        sections = []
        lines = text.split('\n')
        current_section = {"title": "Introduction", "text": ""}
        
        for line in lines:
            line = line.strip()
            if not line:
                current_section["text"] += "\n"
                continue
            
            # Check for section header
            if any(re.match(p, line, re.MULTILINE) for p in patterns) and current_section["text"].strip():
                sections.append(current_section)
                current_section = {"title": line, "text": ""}
            else:
                current_section["text"] += line + "\n"
        
        if current_section["text"].strip():
            sections.append(current_section)
        
        return sections
    
    def _valid_sections(self, sections: List[Dict]) -> bool:
        """Check if sections are reasonable."""
        if len(sections) > 20:
            return False
        
        sizes = [len(s["text"]) for s in sections]
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        small_sections = sum(1 for s in sizes if s < 150)
        
        return avg_size >= 300 and small_sections <= len(sections) * 0.6
    
    def _section_chunking(self, sections: List[Dict]) -> List[Dict[str, Any]]:
        """Create chunks respecting section boundaries."""
        chunks = []
        
        for section in sections:
            text = section["text"].strip()
            title = section["title"].strip()
            
            if not text:
                continue
            
            if len(text) <= self.chunk_size:
                chunks.append({
                    "position": title,
                    "text": text,
                    "size": len(text),
                    "type": "section"
                })
            else:
                # Split large section
                sub_chunks = self._split_text(text, title)
                chunks.extend(sub_chunks)
        
        return chunks
    
    def _paragraph_chunking(self, text: str) -> List[Dict[str, Any]]:
        """Chunk by paragraphs."""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        chunk_num = 1
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 > self.chunk_size and current_chunk:
                chunks.append({
                    "position": f"Chunk {chunk_num}",
                    "text": current_chunk.strip(),
                    "size": len(current_chunk),
                    "type": "paragraph_group"
                })
                current_chunk = self._create_overlap(current_chunk) + para
                chunk_num += 1
            else:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += para
        
        if current_chunk.strip():
            chunks.append({
                "position": f"Chunk {chunk_num}",
                "text": current_chunk.strip(),
                "size": len(current_chunk),
                "type": "paragraph_group"
            })
        
        return chunks
    
    def _sentence_chunking(self, text: str) -> List[Dict[str, Any]]:
        """Chunk by sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = ""
        chunk_num = 1
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 > self.chunk_size and current_chunk:
                chunks.append({
                    "position": f"Chunk {chunk_num}",
                    "text": current_chunk.strip(),
                    "size": len(current_chunk),
                    "type": "sentence_group"
                })
                current_chunk = sentence
                chunk_num += 1
            else:
                if current_chunk:
                    current_chunk += " "
                current_chunk += sentence
        
        if current_chunk.strip():
            chunks.append({
                "position": f"Chunk {chunk_num}",
                "text": current_chunk.strip(),
                "size": len(current_chunk),
                "type": "sentence_group"
            })
        
        return chunks
    
    def _simple_chunking(self, text: str) -> List[Dict[str, Any]]:
        """Simple character-based chunking."""
        chunks = []
        chunk_num = 1
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            if end >= len(text):
                chunk_text = text[start:].strip()
                if chunk_text:
                    chunks.append({
                        "position": f"Chunk {chunk_num}",
                        "text": chunk_text,
                        "size": len(chunk_text),
                        "type": "simple"
                    })
                break
            
            # Find word boundary
            while end > start and text[end] not in ' \n\t.,;!?':
                end -= 1
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "position": f"Chunk {chunk_num}",
                    "text": chunk_text,
                    "size": len(chunk_text),
                    "type": "simple"
                })
            
            start = end - self.chunk_overlap
            chunk_num += 1
        
        return chunks
    
    def _split_text(self, text: str, section_title: str) -> List[Dict[str, Any]]:
        """Split large section into chunks."""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        part_num = 1
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 > self.chunk_size and current_chunk:
                chunks.append({
                    "position": f"{section_title} (Part {part_num})",
                    "text": current_chunk.strip(),
                    "size": len(current_chunk),
                    "type": "section_part"
                })
                current_chunk = self._create_overlap(current_chunk) + para
                part_num += 1
            else:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += para
        
        if current_chunk.strip():
            chunks.append({
                "position": f"{section_title} (Part {part_num})",
                "text": current_chunk.strip(),
                "size": len(current_chunk),
                "type": "section_part"
            })
        
        return chunks
    
    def _create_overlap(self, text: str) -> str:
        """Create overlap text."""
        if self.chunk_overlap <= 0 or len(text) <= self.chunk_overlap:
            return ""
        
        overlap = text[-self.chunk_overlap:]
        
        # Try to start at sentence boundary
        sentence_start = overlap.find('. ')
        if sentence_start != -1 and len(overlap[sentence_start + 2:]) > 50:
            return overlap[sentence_start + 2:] + "\n\n"
        
        # Try word boundary
        space_pos = overlap.find(' ')
        if space_pos != -1:
            return overlap[space_pos + 1:] + "\n\n"
        
        return overlap + "\n\n"
    
    def _optimize_chunk_size(self, file_path: Path):
        """Adjust chunk size based on file size."""
        file_size = file_path.stat().st_size
        
        if file_size < 10000:  # Small file
            self.chunk_size = min(int(self.chunk_size * 1.5), file_size // 2)
        elif file_size > 200000:  # Large file
            self.chunk_size = int(self.chunk_size * 0.9)
    
    def _extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extract document metadata."""
        text_lower = text.lower()
        
        # Determine document type
        doc_types = {
            r'privacy policy': 'privacy_policy',
            r'terms (of use|of service)': 'terms_of_service',
            r'agreement': 'agreement',
            r'contract': 'contract',
            r'proposal': 'proposal'
        }
        
        doc_type = "unknown"
        for pattern, dtype in doc_types.items():
            if re.search(pattern, text_lower):
                doc_type = dtype
                break
        
        # Find data mentions and compliance indicators
        data_mentions = list(set(re.findall(
            r'\b(personal data|information|email|address|phone|user|customer)\b', text_lower
        )))
        
        compliance_indicators = list(set(re.findall(
            r'\b(consent|privacy|compliance|rights|security|cookie)\b', text_lower
        )))
        
        return {
            "document_type": doc_type,
            "potential_data_mentions": data_mentions,
            "compliance_indicators": compliance_indicators
        }