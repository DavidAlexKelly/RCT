"""
Document Processing Module

Handles document loading, text extraction, and intelligent chunking for compliance analysis.
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from config import DocumentConfig

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Processes documents into analyzable chunks using various strategies.
    
    Supports multiple chunking methods:
    - smart: Detects document structure, falls back to paragraphs
    - paragraph: Groups content by paragraphs  
    - sentence: Groups content by sentences
    - simple: Character-based splitting with word boundaries
    """
    
    def __init__(self, chunk_size: Optional[int] = None, 
                 chunk_overlap: Optional[int] = None, 
                 chunking_method: str = "smart") -> None:
        """
        Initialize document processor.
        
        Args:
            chunk_size: Target size of chunks in characters
            chunk_overlap: Overlap between adjacent chunks in characters
            chunking_method: Strategy for chunking ("smart", "paragraph", "sentence", "simple")
        """
        self.chunk_size = chunk_size or DocumentConfig.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or DocumentConfig.DEFAULT_CHUNK_OVERLAP
        self.chunking_method = chunking_method
        
        # Chunking constraints
        self.min_chunk_size = 200
        self.max_chunk_size = self.chunk_size * 2
        
        logger.info(f"DocumentProcessor initialized: {chunking_method} chunking, "
                   f"size={self.chunk_size}, overlap={self.chunk_overlap}")
    
    def process_document(self, file_path: str, 
                        optimize_chunks: Optional[bool] = None) -> Dict[str, Any]:
        """
        Process document into chunks and metadata.
        
        Args:
            file_path: Path to the document file
            optimize_chunks: Whether to adjust chunk size based on document size
            
        Returns:
            Dictionary with 'metadata' and 'chunks' keys
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format not supported
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Use config default if not specified
        if optimize_chunks is None:
            optimize_chunks = DocumentConfig.OPTIMIZE_CHUNK_SIZE
            
        # Adjust chunking parameters if optimization requested
        original_params = None
        if optimize_chunks:
            original_params = (self.chunk_size, self.chunk_overlap)
            self._adjust_chunk_parameters(file_path)
            
        try:
            # Extract text from file
            document_text = self._extract_text(file_path)
            
            # Extract document-level metadata
            document_metadata = self.extract_document_metadata(document_text)
            
            # Create chunks using selected strategy
            chunks = self._create_chunks_improved(document_text)
            
            # Apply document limits
            if len(chunks) > DocumentConfig.MAX_CHUNKS_PER_DOCUMENT:
                logger.warning(f"Document has {len(chunks)} chunks, "
                             f"limiting to {DocumentConfig.MAX_CHUNKS_PER_DOCUMENT}")
                chunks = chunks[:DocumentConfig.MAX_CHUNKS_PER_DOCUMENT]
            
            # Add document metadata to chunks
            for chunk in chunks:
                chunk["document_type"] = document_metadata["document_type"]
            
            logger.info(f"Processed document into {len(chunks)} chunks")
            
            return {
                "metadata": document_metadata,
                "chunks": chunks
            }
            
        finally:
            # Restore original chunking parameters if they were changed
            if original_params:
                self.chunk_size, self.chunk_overlap = original_params
    
    def extract_document_metadata(self, text: str) -> Dict[str, Any]:
        """
        Extract basic metadata about the document.
        
        Args:
            text: Document text content
            
        Returns:
            Dictionary with document type and data indicators
        """
        metadata = {
            "document_type": "unknown",
            "potential_data_mentions": [],
            "compliance_indicators": []
        }
        
        # Identify document type
        doc_type_patterns = {
            r'privacy policy': 'privacy_policy',
            r'terms (of use|of service)': 'terms_of_service',
            r'agreement': 'agreement',
            r'proposal': 'proposal',
            r'contract': 'contract',
            r'report': 'report',
            r'policy': 'policy'
        }
        
        text_lower = text.lower()
        for pattern, doc_type in doc_type_patterns.items():
            if re.search(pattern, text_lower):
                metadata["document_type"] = doc_type
                break
        
        # Find potential data mentions
        data_mentions = re.findall(
            r'\b(personal data|information|data|email|address|name|phone|user|'
            r'customer|profile|account|location|tracking)\b', 
            text_lower
        )
        metadata["potential_data_mentions"] = list(set(data_mentions))
        
        # Find compliance indicators
        compliance_indicators = re.findall(
            r'\b(consent|opt-in|opt-out|privacy|compliance|regulation|rights|'
            r'retain|delete|access|security|cookie)\b',
            text_lower
        )
        metadata["compliance_indicators"] = list(set(compliance_indicators))
        
        return metadata
    
    def _create_chunks_improved(self, text: str) -> List[Dict[str, Any]]:
        """Create chunks using the selected chunking strategy."""
        strategy_map = {
            "smart": self._smart_chunking,
            "paragraph": self._paragraph_chunking,
            "sentence": self._sentence_chunking,
            "simple": self._simple_chunking
        }
        
        chunking_func = strategy_map.get(self.chunking_method, self._smart_chunking)
        return chunking_func(text)
    
    def _smart_chunking(self, text: str) -> List[Dict[str, Any]]:
        """
        Smart chunking that detects document structure.
        Falls back to paragraph chunking if no clear structure found.
        """
        # Try to detect document sections
        sections = self._detect_major_sections(text)
        
        # Use section-aware chunking if we found meaningful sections
        if len(sections) > 1 and self._sections_look_reasonable(sections):
            logger.debug(f"Smart chunking: detected {len(sections)} sections")
            return self._section_aware_chunking(sections)
        else:
            logger.debug("Smart chunking: no clear structure, using paragraph mode")
            return self._paragraph_chunking(text)
    
    def _detect_major_sections(self, text: str) -> List[Dict[str, str]]:
        """Detect major document sections using pattern matching."""
        sections = []
        lines = text.split('\n')
        current_section = {"title": "Introduction", "text": "", "start_line": 0}
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                current_section["text"] += "\n"
                continue
                
            # Check if this line looks like a section header
            is_section_header = any(
                re.match(pattern, line, re.MULTILINE) 
                for pattern in DocumentConfig.SECTION_PATTERNS
            )
            
            if is_section_header and current_section["text"].strip():
                # Save previous section
                sections.append(current_section)
                # Start new section
                current_section = {
                    "title": line,
                    "text": "",
                    "start_line": i
                }
            else:
                # Add to current section
                current_section["text"] += line + "\n"
        
        # Add final section
        if current_section["text"].strip():
            sections.append(current_section)
        
        return sections
    
    def _sections_look_reasonable(self, sections: List[Dict[str, str]]) -> bool:
        """Check if detected sections seem reasonable."""
        if len(sections) > DocumentConfig.SMART_MAX_SECTIONS:
            return False
            
        # Check section size distribution
        sizes = [len(section["text"]) for section in sections]
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        
        if avg_size < DocumentConfig.SMART_MIN_AVG_SIZE:
            return False
            
        # Check if too many sections are tiny
        small_sections = sum(1 for size in sizes if size < 150)
        if small_sections > len(sections) * 0.6:
            return False
            
        return True
    
    def _section_aware_chunking(self, sections: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Create chunks that respect section boundaries."""
        chunks = []
        
        for section in sections:
            section_text = section["text"].strip()
            section_title = section["title"].strip()
            
            if not section_text:
                continue
            
            # Keep small sections as single chunks
            if len(section_text) <= self.chunk_size:
                chunks.append({
                    "position": section_title,
                    "text": section_text,
                    "size": len(section_text),
                    "type": "section"
                })
            else:
                # Split large sections into sub-chunks
                section_chunks = self._split_text_into_chunks(section_text, section_title)
                chunks.extend(section_chunks)
        
        return chunks
    
    def _paragraph_chunking(self, text: str) -> List[Dict[str, Any]]:
        """Chunk by paragraphs, respecting target size."""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        chunk_number = 1
        
        for paragraph in paragraphs:
            # Check if adding this paragraph would exceed target size
            if len(current_chunk) + len(paragraph) + 2 > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    "position": f"Chunk {chunk_number}",
                    "text": current_chunk.strip(),
                    "size": len(current_chunk),
                    "type": "paragraph_group"
                })
                
                # Start new chunk with overlap
                current_chunk = self._create_overlap(current_chunk) + paragraph
                chunk_number += 1
            else:
                # Add to current chunk
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                "position": f"Chunk {chunk_number}",
                "text": current_chunk.strip(),
                "size": len(current_chunk),
                "type": "paragraph_group"
            })
        
        return chunks
    
    def _sentence_chunking(self, text: str) -> List[Dict[str, Any]]:
        """Chunk by sentences, maintaining target size."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = ""
        chunk_number = 1
        
        for sentence in sentences:
            # Check if adding this sentence would exceed target size
            if len(current_chunk) + len(sentence) + 1 > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    "position": f"Chunk {chunk_number}",
                    "text": current_chunk.strip(),
                    "size": len(current_chunk),
                    "type": "sentence_group"
                })
                
                # Start new chunk with overlap
                overlap = self._create_sentence_overlap(current_chunk)
                current_chunk = overlap + sentence
                chunk_number += 1
            else:
                # Add to current chunk
                if current_chunk:
                    current_chunk += " "
                current_chunk += sentence
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                "position": f"Chunk {chunk_number}",
                "text": current_chunk.strip(),
                "size": len(current_chunk),
                "type": "sentence_group"
            })
        
        return chunks
    
    def _simple_chunking(self, text: str) -> List[Dict[str, Any]]:
        """Simple character-based chunking with word boundaries."""
        chunks = []
        chunk_number = 1
        start = 0
        
        while start < len(text):
            # Find end position
            end = start + self.chunk_size
            
            if end >= len(text):
                # Last chunk
                chunk_text = text[start:].strip()
                if chunk_text:
                    chunks.append({
                        "position": f"Chunk {chunk_number}",
                        "text": chunk_text,
                        "size": len(chunk_text),
                        "type": "simple"
                    })
                break
            
            # Find a good break point (word boundary)
            break_point = self._find_word_boundary(text, end)
            chunk_text = text[start:break_point].strip()
            
            if chunk_text:
                chunks.append({
                    "position": f"Chunk {chunk_number}",
                    "text": chunk_text,
                    "size": len(chunk_text),
                    "type": "simple"
                })
            
            # Move start position with overlap
            start = break_point - self.chunk_overlap
            if start < 0:
                start = break_point
            chunk_number += 1
        
        return chunks
    
    def _split_text_into_chunks(self, text: str, section_title: str) -> List[Dict[str, Any]]:
        """Split a large section into smaller chunks."""
        chunks = []
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        current_chunk = ""
        part_number = 1
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    "position": f"{section_title} (Part {part_number})",
                    "text": current_chunk.strip(),
                    "size": len(current_chunk),
                    "type": "section_part"
                })
                
                # Start new chunk with overlap
                current_chunk = self._create_overlap(current_chunk) + paragraph
                part_number += 1
            else:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                "position": f"{section_title} (Part {part_number})",
                "text": current_chunk.strip(),
                "size": len(current_chunk),
                "type": "section_part"
            })
        
        return chunks
    
    def _create_overlap(self, text: str) -> str:
        """Create overlap text from the end of previous chunk."""
        if self.chunk_overlap <= 0 or len(text) <= self.chunk_overlap:
            return ""
        
        overlap_text = text[-self.chunk_overlap:]
        
        # Try to start overlap at a sentence boundary
        sentence_start = overlap_text.find('. ')
        if sentence_start != -1 and len(overlap_text[sentence_start + 2:]) > 50:
            return overlap_text[sentence_start + 2:] + "\n\n"
        
        # Try to start at a word boundary
        space_pos = overlap_text.find(' ')
        if space_pos != -1:
            return overlap_text[space_pos + 1:] + "\n\n"
        
        return overlap_text + "\n\n"
    
    def _create_sentence_overlap(self, text: str) -> str:
        """Create overlap using complete sentences."""
        if self.chunk_overlap <= 0:
            return ""
        
        # Take last sentence as overlap
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) >= 2:
            return sentences[-1] + " "
        
        return ""
    
    def _find_word_boundary(self, text: str, position: int) -> int:
        """Find the nearest word boundary before the given position."""
        if position >= len(text):
            return len(text)
        
        # Look backwards for a space or punctuation
        for i in range(position, max(position - 100, 0), -1):
            if text[i] in ' \n\t.,;!?':
                return i + 1
        
        return position
    
    def _extract_text(self, file_path: str) -> str:
        """Extract text from a file based on its extension."""
        file_path_lower = file_path.lower()
        
        if file_path_lower.endswith('.pdf'):
            return self._read_pdf(file_path)
        elif file_path_lower.endswith(('.txt', '.md')):
            return self._read_text(file_path)
        else:
            raise ValueError("Unsupported file format. Only PDF, TXT and MD are supported.")
    
    def _read_pdf(self, file_path: str) -> str:
        """Extract text from a PDF file."""
        try:
            import pypdf
        except ImportError:
            raise ImportError("pypdf package is required for PDF processing. "
                            "Install with: pip install pypdf")
        
        text = ""
        with open(file_path, "rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += f"[Page {page_num + 1}] " + page_text + "\n\n"
        
        if not text.strip():
            raise ValueError("No text could be extracted from the PDF. "
                           "The PDF might be image-based or corrupted.")
        
        return text
    
    def _read_text(self, file_path: str) -> str:
        """Extract text from a text file."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                text = file.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, "r", encoding="latin-1") as file:
                text = file.read()
        
        if not text.strip():
            raise ValueError("The text file appears to be empty.")
        
        return text
    
    def _adjust_chunk_parameters(self, file_path: str) -> None:
        """Adjust chunk size and overlap based on file size."""
        file_size = os.path.getsize(file_path)
        
        if file_size < DocumentConfig.SMALL_DOC_THRESHOLD:
            # Small document - use larger chunks
            self.chunk_size = max(int(self.chunk_size * 1.5), file_size // 2)
            self.chunk_overlap = max(50, self.chunk_overlap // 2)
            logger.info(f"Small document ({file_size/1024:.1f}KB) - "
                       f"using larger chunks ({self.chunk_size} chars)")
        elif file_size < DocumentConfig.LARGE_DOC_THRESHOLD:
            # Medium document - slightly larger chunks
            self.chunk_size = int(self.chunk_size * 1.2)
            logger.info(f"Medium document ({file_size/1024:.1f}KB) - "
                       f"using standard chunks ({self.chunk_size} chars)")
        else:
            # Large document - use smaller chunks
            self.chunk_size = int(self.chunk_size * 0.9)
            logger.info(f"Large document ({file_size/1024:.1f}KB) - "
                       f"using smaller chunks ({self.chunk_size} chars)")