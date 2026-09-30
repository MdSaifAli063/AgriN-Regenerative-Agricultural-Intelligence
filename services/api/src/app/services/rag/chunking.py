"""
KrishiNet-BRICS - Structure-Aware Agronomic Text Chunker.

Splits markdown, text, and PDF documents into semantically coherent chunks:
  - Extracts YAML front-matter tags (crop, region, practice, license, source)
  - Splits primarily along heading boundaries (#, ##, ###)
  - Sub-divides large sections into 400-600 token windows with ~60 token overlap
  - Preserves hierarchical document context (title, section, metadata) on every chunk
"""

import re
from typing import Any, Dict, List, Optional, Tuple


class TextChunk:
    def __init__(
        self,
        index: int,
        content: str,
        section_heading: str,
        metadata: Dict[str, Any],
    ):
        self.index = index
        self.content = content.strip()
        self.section_heading = section_heading
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_index": self.index,
            "content_text": self.content,
            "section_heading": self.section_heading,
            "metadata": self.metadata,
        }


def extract_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Extracts YAML front-matter from markdown if present."""
    metadata = {}
    cleaned_text = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            raw_yaml = parts[1]
            cleaned_text = parts[2].strip()
            for line in raw_yaml.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    key = k.strip()
                    val = v.strip().strip('"').strip("'")
                    metadata[key] = val

    return metadata, cleaned_text


def chunk_document(
    text: str,
    doc_title: str,
    doc_metadata: Optional[Dict[str, Any]] = None,
    max_chars: int = 2000,   # ~500 tokens
    overlap_chars: int = 240, # ~60 tokens
) -> List[TextChunk]:
    """
    Splits text into structure-aware chunks.
    Preserves document title, section headings, and agronomic metadata.
    """
    fm_meta, body = extract_frontmatter(text)
    combined_meta = dict(doc_metadata or {})
    combined_meta.update(fm_meta)
    combined_meta["document_title"] = doc_title

    # 1. Split body into heading-delimited sections
    # Matches markdown headers like # Heading, ## Subheading, ### Sub-subheading
    heading_pattern = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)
    splits = heading_pattern.split(body)

    sections: List[Tuple[str, str]] = []
    current_heading = "Introduction"

    if splits:
        # First element is pre-heading text
        if splits[0].strip():
            sections.append((current_heading, splits[0].strip()))

        i = 1
        while i < len(splits):
            header = splits[i].strip().lstrip("#").strip()
            content = splits[i + 1].strip() if i + 1 < len(splits) else ""
            if content:
                sections.append((header, content))
            i += 2

    if not sections:
        sections = [(doc_title, body.strip())]

    # 2. Window-split sections that exceed max_chars
    chunks: List[TextChunk] = []
    chunk_counter = 0

    for heading, sec_text in sections:
        if len(sec_text) <= max_chars:
            chunk_meta = dict(combined_meta)
            chunk_meta["section_heading"] = heading
            chunks.append(
                TextChunk(
                    index=chunk_counter,
                    content=f"[{doc_title} - {heading}]\n{sec_text}",
                    section_heading=heading,
                    metadata=chunk_meta,
                )
            )
            chunk_counter += 1
        else:
            # Sub-split into overlapping windows
            # Break on paragraph or sentence boundaries
            atoms: List[str] = []
            for p in sec_text.split("\n\n"):
                if len(p) <= max_chars:
                    atoms.append(p)
                else:
                    # Split paragraph on sentences
                    sentences = re.split(r"(?<=[.!?])\s+", p)
                    cur_s = []
                    cur_s_len = 0
                    for s in sentences:
                        if cur_s_len + len(s) > max_chars and cur_s:
                            atoms.append(" ".join(cur_s))
                            cur_s = [s]
                            cur_s_len = len(s)
                        else:
                            cur_s.append(s)
                            cur_s_len += len(s)
                    if cur_s:
                        atoms.append(" ".join(cur_s))

            cur_buffer = []
            cur_len = 0

            for atom in atoms:
                atom_len = len(atom)
                if cur_len + atom_len > max_chars and cur_buffer:
                    sub_text = "\n\n".join(cur_buffer)
                    chunk_meta = dict(combined_meta)
                    chunk_meta["section_heading"] = heading
                    chunks.append(
                        TextChunk(
                            index=chunk_counter,
                            content=f"[{doc_title} - {heading}]\n{sub_text}",
                            section_heading=heading,
                            metadata=chunk_meta,
                        )
                    )
                    chunk_counter += 1

                    # Retain last atom for overlap if within overlap limit
                    if len(cur_buffer[-1]) <= overlap_chars:
                        cur_buffer = [cur_buffer[-1], atom]
                        cur_len = len(cur_buffer[0]) + atom_len
                    else:
                        cur_buffer = [atom]
                        cur_len = atom_len
                else:
                    cur_buffer.append(atom)
                    cur_len += atom_len

            if cur_buffer:
                sub_text = "\n\n".join(cur_buffer)
                chunk_meta = dict(combined_meta)
                chunk_meta["section_heading"] = heading
                chunks.append(
                    TextChunk(
                        index=chunk_counter,
                        content=f"[{doc_title} - {heading}]\n{sub_text}",
                        section_heading=heading,
                        metadata=chunk_meta,
                    )
                )
                chunk_counter += 1

    return chunks

