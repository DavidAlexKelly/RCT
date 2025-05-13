# utils/document_processor.py

import os
import re
from typing import List, Dict, Any, Optional, Tuple

class DocumentProcessor:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        """
        Initialize document processor with configurable chunking.
        
        Args:
            chunk_size: Target size of chunks in characters
            chunk_overlap: Overlap between adjacent chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_document(self, file_path: str, optimize_chunks: bool = True) -> Dict[str, Any]:
        """
        Process document with optimized chunking based on document size.
        
        Args:
            file_path: Path to the document file
            optimize_chunks: Whether to adjust chunk size based on document size
            
        Returns:
            Dictionary with metadata and chunks
        """
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Adjust chunking parameters if optimization requested
        original_params = None
        if optimize_chunks:
            original_params = (self.chunk_size, self.chunk_overlap)
            self._adjust_chunk_parameters(file_path)
            
        # Extract text from file
        document_text = self._extract_text(file_path)
        
        # Extract document-level metadata
        document_metadata = self.extract_document_metadata(document_text)
        
        # Extract sections and create chunks
        sections = self._extract_sections(document_text)
        chunks = self._create_chunks(sections)
        
        # Add document metadata to chunks
        for chunk in chunks:
            chunk["document_type"] = document_metadata["document_type"]
        
        # Restore original chunking parameters if they were changed
        if original_params:
            self.chunk_size, self.chunk_overlap = original_params
        
        return {
            "metadata": document_metadata,
            "chunks": chunks
        }
    
    def _extract_text(self, file_path: str) -> str:
        """Extract text from a file based on its extension."""
        if file_path.lower().endswith('.pdf'):
            return self._read_pdf(file_path)
        elif file_path.lower().endswith(('.txt', '.md')):
            return self._read_text(file_path)
        else:
            raise ValueError("Unsupported file format. Only PDF, TXT and MD are supported.")
    
    def _read_pdf(self, file_path: str) -> str:
        """Extract text from a PDF file."""
        import pypdf
        
        text = ""
        with open(file_path, "rb") as file:
            pdf_reader = pypdf.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += f"[Page {page_num + 1}] " + page_text + "\n\n"
        return text
    
    def _read_text(self, file_path: str) -> str:
        """Extract text from a text file."""
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()
        return text
    
    def _adjust_chunk_parameters(self, file_path: str) -> None:
        """Adjust chunk size and overlap based on file size."""
        file_size = os.path.getsize(file_path)
        
        # Adjust chunk size based on file size
        if file_size < 10000:  # Very small document (<10KB)
            self.chunk_size = 10000
            self.chunk_overlap = 0
            print(f"Very small document ({file_size/1024:.1f}KB) - using a single chunk")
        elif file_size < 50000:  # Small document (<50KB)
            self.chunk_size = 5000
            self.chunk_overlap = 500
            print(f"Small document ({file_size/1024:.1f}KB) - using larger chunks")
        elif file_size < 200000:  # Medium document (<200KB)
            self.chunk_size = 2500
            self.chunk_overlap = 250
            print(f"Medium document ({file_size/1024:.1f}KB) - using moderate chunks")
    
    def extract_document_metadata(self, text: str) -> Dict[str, Any]:
        """Extract basic metadata about the document."""
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
        
        for pattern, doc_type in doc_type_patterns.items():
            if re.search(pattern, text, re.I):
                metadata["document_type"] = doc_type
                break
        
        # Find potential data mentions with a single regex
        data_mentions = re.findall(r'\b(personal data|information|data|email|address|name|phone|user|customer|profile|account|location|tracking)\b', 
                                 text.lower())
        metadata["potential_data_mentions"] = list(set(data_mentions))
        
        # Find compliance indicators with a single regex
        compliance_indicators = re.findall(r'\b(consent|opt-in|opt-out|privacy|compliance|regulation|rights|retain|delete|access|security|cookie)\b',
                                       text.lower())
        metadata["compliance_indicators"] = list(set(compliance_indicators))
        
        return metadata
    
    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """Extract sections using a simplified approach that focuses on headers and paragraphs."""
        sections = []
        
        # Use a simplified pattern that works for most documents
        # Look for numbered sections, headers in ALL CAPS, or title case headers with colon
        section_pattern = re.compile(r'(?:^|\n)(?:(\d+(?:\.\d+)*\.\s+[^\n]+)|([A-Z][A-Z\s]{2,}[A-Z])|([A-Z][a-zA-Z\s]+:))(?:\n|$)')
        
        matches = list(section_pattern.finditer(text))
        
        if not matches:
            # If no section headers found, treat the whole document as one section
            sections.append({
                "title": "Document",
                "text": text,
                "level": 0
            })
            return sections
        
        # Process each section
        for i, match in enumerate(matches):
            title = match.group(0).strip()
            start_pos = match.start()
            
            # Determine the end position (start of next section or end of text)
            if i < len(matches) - 1:
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            # Extract section text
            section_text = text[start_pos:end_pos].strip()
            
            # Determine section level (simplified)
            level = 0
            if match.group(1):  # Numbered section
                # Count dots to determine level
                level = match.group(1).count('.')
            
            sections.append({
                "title": title,
                "text": section_text,
                "level": level
            })
        
        # Handle content before first section if any
        if matches and matches[0].start() > 0:
            intro_text = text[:matches[0].start()].strip()
            if intro_text:
                sections.insert(0, {
                    "title": "Introduction/Header",
                    "text": intro_text,
                    "level": 0
                })
        
        return sections
    
    def _create_chunks(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create chunks from sections, respecting paragraph boundaries where possible."""
        chunks = []
        
        for section in sections:
            section_text = section["text"]
            section_title = section["title"]
            
            # If section is small enough, keep it as a single chunk
            if len(section_text) <= self.chunk_size:
                chunks.append({
                    "position": section_title,
                    "text": section_text,
                    "level": section["level"]
                })
                continue
            
            # Split by paragraphs first
            paragraphs = re.split(r'\n\s*\n', section_text)
            
            current_chunk = ""
            chunk_count = 1
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                # If adding this paragraph would exceed the chunk size
                if len(current_chunk) + len(para) + 2 > self.chunk_size and current_chunk:
                    # Save current chunk
                    chunks.append({
                        "position": f"{section_title} (Part {chunk_count})",
                        "text": current_chunk,
                        "level": section["level"]
                    })
                    chunk_count += 1
                    
                    # Start new chunk with overlap if needed
                    if self.chunk_overlap > 0 and len(current_chunk) > self.chunk_overlap:
                        # Find a good break point for overlap
                        overlap_text = current_chunk[-self.chunk_overlap:]
                        # Try to break at a sentence boundary
                        sentence_break = re.search(r'(?<=[.!?])\s+', overlap_text)
                        if sentence_break:
                            overlap_text = overlap_text[sentence_break.end():]
                        current_chunk = overlap_text + "\n\n" + para
                    else:
                        current_chunk = para
                else:
                    # Add to current chunk
                    if current_chunk:
                        current_chunk += "\n\n"
                    current_chunk += para
            
            # Add the last chunk if there's anything left
            if current_chunk:
                chunks.append({
                    "position": f"{section_title} (Part {chunk_count})",
                    "text": current_chunk,
                    "level": section["level"]
                })
        
        return chunks