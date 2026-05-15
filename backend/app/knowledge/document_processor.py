"""
Document Processor
Process and chunk documents for RAG
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A text chunk from a document"""
    content: str
    metadata: Dict[str, Any]
    chunk_index: int
    start_char: int
    end_char: int


class DocumentProcessor:
    """
    Process documents into chunks for RAG

    Supports:
    - Text files (.txt, .md)
    - PDF files (basic text extraction)
    - HTML files
    - URLs
    """

    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 200

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def process_file(
        self,
        file_path: str,
        source_type: str = "file",
    ) -> List[Chunk]:
        """Process a file into chunks"""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() == ".pdf":
            content = self._extract_pdf(file_path)
        elif path.suffix.lower() in [".txt", ".md", ".rst"]:
            content = path.read_text(encoding="utf-8")
        elif path.suffix.lower() == ".html":
            content = self._extract_html(file_path)
        else:
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = path.read_text(encoding="latin-1")

        return self.chunk_text(
            content,
            metadata={
                "source": str(file_path),
                "source_type": source_type,
                "file_name": path.name,
                "file_size": path.stat().st_size,
            }
        )

    def process_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """Process raw text into chunks"""
        return self.chunk_text(text, metadata or {})

    def process_url(
        self,
        url: str,
        html_content: str,
    ) -> List[Chunk]:
        """Process URL content into chunks"""
        text = self._clean_html(html_content)
        return self.chunk_text(
            text,
            metadata={"source": url, "source_type": "url"}
        )

    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """Split text into chunks with sliding window"""
        text = self._clean_text(text)
        if not text:
            return []

        sentences = self._split_sentences(text)
        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_start = text.find(sentence, current_start)
            if sentence_start == -1:
                continue

            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence + " "
                current_start = sentence_start + len(sentence)
            else:
                if len(current_chunk.strip()) >= self.min_chunk_size:
                    chunks.append(Chunk(
                        content=current_chunk.strip(),
                        metadata={**(metadata or {}), "chunk_index": chunk_index},
                        chunk_index=chunk_index,
                        start_char=current_start - len(current_chunk),
                        end_char=current_start,
                    ))
                    chunk_index += 1

                if self.chunk_overlap > 0 and len(current_chunk) > self.chunk_overlap:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text
                    current_start = sentence_start - len(overlap_text)
                else:
                    current_chunk = ""
                    current_start = sentence_start

                current_chunk += sentence + " "
                current_start = sentence_start + len(sentence)

        if len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append(Chunk(
                content=current_chunk.strip(),
                metadata={**(metadata or {}), "chunk_index": chunk_index},
                chunk_index=chunk_index,
                start_char=current_start - len(current_chunk),
                end_char=current_start,
            ))

        return chunks

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        result = []
        for sent in sentences:
            lines = sent.split("\n")
            result.extend([l.strip() for l in lines if l.strip()])
        return result

    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF"""
        try:
            import PyPDF2
            text = []
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text.append(page_text)
            return "\n\n".join(text)
        except ImportError:
            logger.warning("PyPDF2 not installed, using fallback")
            with open(file_path, "rb") as f:
                content = f.read()
            text = ""
            for byte in content:
                if 32 <= byte <= 126 or byte in [10, 13, 9]:
                    text += chr(byte)
                else:
                    text += " "
            return re.sub(r"\s+", " ", text).strip()

    def _extract_html(self, file_path: str) -> str:
        """Extract text from HTML file"""
        content = Path(file_path).read_text(encoding="utf-8")
        return self._clean_html(content)

    def _clean_html(self, html: str) -> str:
        """Remove HTML tags and extract text"""
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", html)
        try:
            from html import unescape
            text = unescape(text)
        except ImportError:
            pass
        return self._clean_text(text)

    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        return [".txt", ".md", ".rst", ".pdf", ".html", ".htm"]
