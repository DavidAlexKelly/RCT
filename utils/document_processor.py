# utils/document_processor.py - Proper error handling without fallbacks

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# Import centralized performance configuration
from config import DocumentConfig

class DocumentProcessor:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None, chunking_method: str = "smart"):
        """
        Initialize document processor with validation.
        
        Args:
            chunk_size: Target size of chunks in characters (uses config default if None)
            chunk_overlap: Overlap between adjacent chunks in characters (uses config default if None)
            chunking_method: "smart", "paragraph", "sentence", or "simple"
        """
        # Validate and set chunk size
        if chunk_size is None:
            self.chunk_size = DocumentConfig.DEFAULT_CHUNK_SIZE
        else:
            if not isinstance(chunk_size, int) or chunk_size < DocumentConfig.MIN_CHUNK_SIZE or chunk_size > DocumentConfig.MAX_CHUNK_SIZE:
                raise ValueError(f"chunk_size must be between {DocumentConfig.MIN_CHUNK_SIZE} and {DocumentConfig.MAX_CHUNK_SIZE}, got {chunk_size}")
            self.chunk_size = chunk_size
        
        # Validate and set chunk overlap
        if chunk_overlap is None:
            self.chunk_overlap = DocumentConfig.DEFAULT_CHUNK_OVERLAP
        else:
            if not isinstance(chunk_overlap, int) or chunk_overlap < DocumentConfig.MIN_OVERLAP or chunk_overlap > DocumentConfig.MAX_OVERLAP:
                raise ValueError(f"chunk_overlap must be between {DocumentConfig.MIN_OVERLAP} and {DocumentConfig.MAX_OVERLAP}, got {chunk_overlap}")
            if chunk_overlap >= self.chunk_size:
                raise ValueError(f"chunk_overlap ({chunk_overlap}) must be less than chunk_size ({self.chunk_size})")
            self.chunk_overlap = chunk_overlap
        
        # Validate chunking method
        valid_methods = ["smart", "paragraph", "sentence", "simple"]
        if chunking_method not in valid_methods:
            raise ValueError(f"chunking_method must be one of {valid_methods}, got '{chunking_method}'")
        self.chunking_method = chunking_method
        
        # Chunking parameters
        self.min_chunk_size = 200  # Minimum viable chunk size
        self.max_chunk_size = self.chunk_size * 2  # Maximum before forced split
    
    def process_document(self, file_path: str, optimize_chunks: bool = None) -> Dict[str, Any]:
        """
        Process document with proper error handling and validation.
        
        Args:
            file_path: Path to the document file
            optimize_chunks: Whether to adjust chunk size based on document size (uses config default if None)
            
        Returns:
            Dictionary with metadata and chunks
        """
        # Validate file path
        if not file_path:
            raise ValueError("file_path cannot be empty")
        
        if not isinstance(file_path, (str, Path)):
            raise ValueError("file_path must be a string or Path object")
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        if file_path.stat().st_size == 0:
            raise ValueError(f"File is empty: {file_path}")
        
        # Use configuration default for optimize_chunks if not specified
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
            
            # Validate extracted text
            if not document_text:
                raise ValueError(f"No text content extracted from file: {file_path}")
            
            if not document_text.strip():
                raise ValueError(f"Extracted text contains only whitespace: {file_path}")
            
            # Extract document-level metadata
            document_metadata = self.extract_document_metadata(document_text)
            
            # Create chunks using improved strategy
            chunks = self._create_chunks_improved(document_text)
            
            if not chunks:
                raise RuntimeError(f"Failed to create chunks from document: {file_path}")
            
            # Apply document limits from configuration
            if len(chunks) > DocumentConfig.MAX_CHUNKS_PER_DOCUMENT:
                print(f"Warning: Document has {len(chunks)} chunks, limiting to {DocumentConfig.MAX_CHUNKS_PER_DOCUMENT}")
                chunks = chunks[:DocumentConfig.MAX_CHUNKS_PER_DOCUMENT]
            
            # Validate chunks
            valid_chunks = []
            for i, chunk in enumerate(chunks):
                if not chunk.get("text", "").strip():
                    print(f"Warning: Skipping empty chunk {i+1}")
                    continue
                
                # Add document metadata to chunks
                chunk["document_type"] = document_metadata["document_type"]
                valid_chunks.append(chunk)
            
            if not valid_chunks:
                raise RuntimeError(f"No valid chunks created from document: {file_path}")
            
            return {
                "metadata": document_metadata,
                "chunks": valid_chunks
            }
            
        except Exception as e:
            # Re-raise with additional context but don't hide the original error
            if "No text content" in str(e) or "empty" in str(e).lower():
                raise ValueError(f"Document processing failed - {e}")
            elif "Failed to create chunks" in str(e):
                raise RuntimeError(f"Chunking failed - {e}")
            else:
                raise RuntimeError(f"Document processing failed for {file_path}: {e}")
        
        finally:
            # Restore original chunking parameters if they were changed
            if original_params:
                self.chunk_size, self.chunk_overlap = original_params
    
    def _extract_text(self, file_path: Path) -> str:
        """Extract text from a file based on its extension with proper error handling."""
        file_extension = file_path.suffix.lower()
        
        supported_extensions = {'.pdf': 'PDF', '.txt': 'Plain text', '.md': 'Markdown'}
        
        if file_extension not in supported_extensions:
            supported_list = ", ".join(supported_extensions.keys())
            raise ValueError(
                f"Unsupported file format '{file_extension}'. "
                f"Supported formats: {supported_list}"
            )
        
        try:
            if file_extension == '.pdf':
                return self._read_pdf(file_path)
            elif file_extension in ['.txt', '.md']:
                return self._read_text(file_path)
        except Exception as e:
            file_type = supported_extensions[file_extension]
            raise RuntimeError(f"Failed to extract text from {file_type} file: {e}")
    
    def _read_pdf(self, file_path: Path) -> str:
        """Extract text from a PDF file with proper error handling."""
        try:
            import pypdf
        except ImportError:
            raise RuntimeError(
                "PDF processing requires pypdf. Install with: pip install pypdf"
            )
        
        text_parts = []
        
        try:
            with open(file_path, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)
                
                if len(pdf_reader.pages) == 0:
                    raise ValueError("PDF file contains no pages")
                
                for page_num in range(len(pdf_reader.pages)):
                    try:
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text()
                        
                        if page_text and page_text.strip():
                            text_parts.append(f"[Page {page_num + 1}] {page_text}")
                        
                    except Exception as e:
                        print(f"Warning: Failed to extract text from page {page_num + 1}: {e}")
                        continue
        
        except Exception as e:
            if "encrypted" in str(e).lower():
                raise ValueError("PDF file is encrypted or password-protected")
            elif "corrupted" in str(e).lower() or "invalid" in str(e).lower():
                raise ValueError("PDF file appears to be corrupted or invalid")
            else:
                raise RuntimeError(f"PDF reading failed: {e}")
        
        if not text_parts:
            raise ValueError("No readable text found in PDF file. File may be image-based or corrupted.")
        
        full_text = "\n\n".join(text_parts)
        
        if len(full_text.strip()) < 10:
            raise ValueError("Extracted PDF text is too short (less than 10 characters)")
        
        return full_text
    
    def _read_text(self, file_path: Path) -> str:
        """Extract text from a text file with proper error handling."""
        encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings_to_try:
            try:
                with open(file_path, "r", encoding=encoding) as file:
                    text = file.read()
                    
                if not text:
                    raise ValueError("Text file is empty")
                
                if len(text.strip()) < 5:
                    raise ValueError("Text file contains insufficient content (less than 5 characters)")
                
                return text
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                raise RuntimeError(f"Failed to read text file: {e}")
        
        # If all encodings failed
        raise ValueError(
            f"Could not decode text file with any of these encodings: {encodings_to_try}. "
            f"File may be binary or use an unsupported encoding."
        )
    
    def _create_chunks_improved(self, text: str) -> List[Dict[str, Any]]:
        """
        Improved chunking strategy with proper validation.
        """
        if not text:
            raise ValueError("Input text cannot be empty")
        
        if not text.strip():
            raise ValueError("Input text contains only whitespace")
        
        try:
            if self.chunking_method == "smart":
                return self._smart_chunking(text)
            elif self.chunking_method == "paragraph":
                return self._paragraph_chunking(text)
            elif self.chunking_method == "sentence":
                return self._sentence_chunking(text)
            elif self.chunking_method == "simple":
                return self._simple_chunking(text)
            else:
                raise ValueError(f"Invalid chunking method: {self.chunking_method}")
        except Exception as e:
            raise RuntimeError(f"Chunking failed with method '{self.chunking_method}': {e}")
    
    def _smart_chunking(self, text: str) -> List[Dict[str, Any]]:
        """Smart chunking that detects document structure."""
        # Try to detect if document has clear section structure
        sections = self._detect_major_sections(text)
        
        # If we found meaningful sections, use section-aware chunking
        if len(sections) > 1 and self._sections_look_reasonable(sections):
            return self._section_aware_chunking(sections)
        else:
            # Fall back to paragraph-based chunking for unstructured documents
            return self._paragraph_chunking(text)
    
    def _detect_major_sections(self, text: str) -> List[Dict[str, str]]:
        """Detect major document sections (only clear, obvious ones)."""
        sections = []
        
        # Look for clear section patterns
        section_patterns = [
            r'^(\d+\.\s+[A-Z][^\n]{10,80})$',  # "1. Section Title"
            r'^([A-Z][A-Z\s]{5,50}[A-Z])$',   # "SECTION TITLE" (all caps)
            r'^(#{1,3}\s+[^\n]+)$',           # "# Markdown Headers"
            r'^([A-Z][a-zA-Z\s&]{5,60}:)$'   # "Section Title:"
        ]
        
        lines = text.split('\n')
        current_section = {"title": "Introduction", "text": "", "start_line": 0}
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                current_section["text"] += "\n"
                continue
                
            # Check if this line looks like a section header
            is_section_header = False
            for pattern in section_patterns:
                if re.match(pattern, line, re.MULTILINE):
                    is_section_header = True
                    break
            
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
        if len(sections) > 20:  # Too many sections = probably false positives
            return False
            
        # Check if sections have reasonable size distribution
        sizes = [len(section["text"]) for section in sections]
        if not sizes:
            return False
            
        avg_size = sum(sizes) / len(sizes)
        
        # If average section is too small, probably over-detected
        if avg_size < 300:
            return False
            
        # If most sections are too small, probably not real structure
        small_sections = sum(1 for size in sizes if size < 150)
        if small_sections > len(sections) * 0.6:  # More than 60% are tiny
            return False
            
        return True
    
    def _section_aware_chunking(self, sections: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Create chunks that respect section boundaries but maintain target size."""
        chunks = []
        
        for section in sections:
            section_text = section["text"].strip()
            section_title = section["title"].strip()
            
            if not section_text:
                continue
            
            # If section is small enough, keep it as one chunk
            if len(section_text) <= self.chunk_size:
                chunks.append({
                    "position": section_title,
                    "text": section_text,
                    "size": len(section_text),
                    "type": "section"
                })
            else:
                # Split large section into sub-chunks
                section_chunks = self._split_text_into_chunks(section_text, section_title)
                chunks.extend(section_chunks)
        
        if not chunks:
            raise RuntimeError("Section-aware chunking produced no chunks")
        
        return chunks
    
    def _paragraph_chunking(self, text: str) -> List[Dict[str, Any]]:
        """Chunk by paragraphs, respecting target size."""
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        if not paragraphs:
            raise RuntimeError("No paragraphs found in text")
        
        chunks = []
        current_chunk = ""
        chunk_number = 1
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed target size
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
        
        if not chunks:
            raise RuntimeError("Paragraph chunking produced no chunks")
        
        return chunks
    
    def _sentence_chunking(self, text: str) -> List[Dict[str, Any]]:
        """Chunk by sentences, maintaining target size."""
        # Simple sentence splitting (can be improved with nltk if needed)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            raise RuntimeError("No sentences found in text")
        
        chunks = []
        current_chunk = ""
        chunk_number = 1
        
        for sentence in sentences:
            # If adding this sentence would exceed target size
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
        
        if not chunks:
            raise RuntimeError("Sentence chunking produced no chunks")
        
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
        
        if not chunks:
            raise RuntimeError("Simple chunking produced no chunks")
        
        return chunks
    
    def _split_text_into_chunks(self, text: str, section_title: str) -> List[Dict[str, Any]]:
        """Split a large section into smaller chunks."""
        chunks = []
        
        # Try paragraph splitting first
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
        
        # Take last few sentences as overlap
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) >= 2:
            return sentences[-1] + " "  # Last sentence
        
        return ""
    
    def _find_word_boundary(self, text: str, position: int) -> int:
        """Find the nearest word boundary before the given position."""
        if position >= len(text):
            return len(text)
        
        # Look backwards for a space or punctuation
        for i in range(position, max(position - 100, 0), -1):
            if text[i] in ' \n\t.,;!?':
                return i + 1
        
        # If no good boundary found, use the position
        return position
    
    def _adjust_chunk_parameters(self, file_path: Path) -> None:
        """Adjust chunk size and overlap based on file size using configuration thresholds."""
        file_size = file_path.stat().st_size
        
        if file_size < DocumentConfig.SMALL_DOC_THRESHOLD:  # Very small document
            self.chunk_size = max(int(self.chunk_size * 1.5), file_size // 2)
            self.chunk_overlap = max(50, self.chunk_overlap // 2)
            print(f"Small document ({file_size/1024:.1f}KB) - using larger chunks ({self.chunk_size} chars)")
        elif file_size < DocumentConfig.LARGE_DOC_THRESHOLD:  # Medium document
            self.chunk_size = int(self.chunk_size * 1.2)
            print(f"Medium document ({file_size/1024:.1f}KB) - using standard chunks ({self.chunk_size} chars)")
        else:  # Large document
            self.chunk_size = int(self.chunk_size * 0.9)
            print(f"Large document ({file_size/1024:.1f}KB) - using smaller chunks ({self.chunk_size} chars)")
    
    def extract_document_metadata(self, text: str) -> Dict[str, Any]:
        """Extract basic metadata about the document with validation."""
        if not text:
            raise ValueError("Text cannot be empty for metadata extraction")
        
        metadata = {
            "document_type": "unknown",
            "potential_data_mentions": [],
            "compliance_indicators": []
        }
        
        # Try to identify document type using a simplified approach
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
        
        # Find potential data mentions with validation
        try:
            data_mentions = re.findall(r'\b(personal data|information|data|email|address|name|phone|user|customer|profile|account|location|tracking)\b', 
                                     text_lower)
            metadata["potential_data_mentions"] = list(set(data_mentions))
        except Exception as e:
            print(f"Warning: Failed to extract data mentions: {e}")
            metadata["potential_data_mentions"] = []
        
        # Find compliance indicators with validation
        try:
            compliance_indicators = re.findall(r'\b(consent|opt-in|opt-out|privacy|compliance|regulation|rights|retain|delete|access|security|cookie)\b',
                                           text_lower)
            metadata["compliance_indicators"] = list(set(compliance_indicators))
        except Exception as e:
            print(f"Warning: Failed to extract compliance indicators: {e}")
            metadata["compliance_indicators"] = []
        
        return metadata