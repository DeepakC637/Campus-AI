"""
ai_engine/parsing.py

Core text extraction and skill identification engine for PlacementHub resumes.
Supports PDF (via pdfplumber) and DOCX (via python-docx) formats, and leverages
spaCy PhraseMatcher for token-aware, case-insensitive skill identification.
"""

import logging
import os
from pathlib import Path
from typing import Any, Iterable, List

import docx
import pdfplumber
import spacy
from spacy.matcher import PhraseMatcher

logger = logging.getLogger(__name__)

# Initialize lightweight English tokenizer once at module level.
# No heavy deep-learning model download required; blank('en') provides
# fast, robust tokenization and rule-based vocabulary.
_nlp = spacy.blank("en")


def extract_text(file_path: Any, file_extension: str) -> str:
    """
    Extract raw text from a resume file on disk or file-like path.

    Supports:
        - PDF files (using pdfplumber)
        - DOCX files (using python-docx)

    Corrupt, malformed, empty, or unreadable files log a warning and safely
    return an empty string without crashing.
    """
    if not file_path:
        return ""

    ext = (file_extension or "").lower().lstrip(".")
    if not ext and isinstance(file_path, (str, Path)):
        ext = os.path.splitext(str(file_path))[1].lower().lstrip(".")

    try:
        if ext == "pdf":
            text_chunks: List[str] = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_chunks.append(page_text)
            return "\n".join(text_chunks).strip()

        elif ext == "docx":
            doc = docx.Document(file_path)
            para_texts = [p.text for p in doc.paragraphs if p.text]
            return "\n".join(para_texts).strip()

        else:
            logger.warning("Unsupported file extension '%s' for resume text extraction at %s", ext, file_path)
            return ""

    except Exception as exc:
        logger.warning(
            "Failed to extract text from %s (extension '%s'): %s",
            file_path,
            ext,
            exc,
            exc_info=True,
        )
        return ""


def extract_skills(text: str, skill_queryset: Iterable[Any]) -> List[str]:
    """
    Match text against all known skill names and return deduplicated matches.

    Why spaCy PhraseMatcher:
    ------------------------
    1. Token-aware boundary matching:
       Naive substring searches produce notorious false positives in tech resumes
       (e.g., 'Java' falsely matching inside 'JavaScript', or single letters like 'C'
       matching inside 'React', 'CSS', or 'Cloud'). PhraseMatcher aligns with discrete
       token boundaries.
    2. Multi-word phrase support:
       Handles multi-word skills (e.g., 'Machine Learning', 'Data Structures',
       'REST APIs', 'Spring Boot') as multi-token sequences seamlessly.
    3. Performance:
       Builds an in-memory Aho-Corasick prefix tree (trie) in C/Cython, enabling
       O(N) scanning of document text regardless of dictionary size, avoiding
       costly repeated regex iterations.
    4. Case-insensitivity with canonical casing:
       Matches tokens with attr="LOWER" against case variations in user resumes,
       while resolving each match back to its authoritative canonical Skill.name.
    """
    if not text or not skill_queryset:
        return []

    # Normalize skill items from queryset or iterable of strings/models
    canonical_skills: List[str] = []
    for item in skill_queryset:
        name = getattr(item, "name", None)
        if name is None:
            name = str(item)
        cleaned_name = name.strip()
        if cleaned_name and cleaned_name not in canonical_skills:
            canonical_skills.append(cleaned_name)

    if not canonical_skills:
        return []

    matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
    # Register patterns for each canonical skill
    for skill_name in canonical_skills:
        pattern_doc = _nlp.make_doc(skill_name)
        matcher.add(skill_name, [pattern_doc])

    doc = _nlp(text)
    matches = matcher(doc)

    matched_names: List[str] = []
    for match_id, _start, _end in matches:
        canonical_name = _nlp.vocab.strings[match_id]
        matched_names.append(canonical_name)

    # Return deduplicated skill names preserving order of first match
    return list(dict.fromkeys(matched_names))
