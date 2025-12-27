"""
End-to-end document metadata extraction pipeline.

- Uses LangChain with with_structured_output()
- Uses fixed categories
- Uses evolving topics & tags loaded from TXT files
- Separates LLM output from final system-of-record schema
"""

from datetime import date, datetime, timezone
from typing import List, Optional
from pathlib import Path
from uuid import UUID, uuid4
import hashlib
import re

from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate

from dotenv import load_dotenv

load_dotenv(override=True)

# Add backend to path for imports
import sys
BACKEND_DIR = Path(__file__).parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from utils.llm_config import get_chat_llm


# ============================================================
# 1. Utilities
# ============================================================

def load_vocab(path: str) -> List[str]:
    if not Path(path).exists():
        return []
    return [
        line.strip()
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ============================================================
# 2. Paths & Controlled Vocabularies
# ============================================================

# Get project root (parent of examples/)
PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
ASSETS_DIR.mkdir(exist_ok=True)

TOPICS_FILE = ASSETS_DIR / "topics.txt"
TAGS_FILE = ASSETS_DIR / "tags.txt"

KNOWN_TOPICS = load_vocab(str(TOPICS_FILE))
KNOWN_TAGS = load_vocab(str(TAGS_FILE))

CATEGORIES = [
    "Education",
    "Capita Selecta",
    "Research Meeting",
    "World Headlines",
    "Miscellaneous",
]


# ============================================================
# 3. Pydantic Schemas — LLM Extraction
# ============================================================

class GlossaryTerm(BaseModel):
    term: str
    definition: Optional[str]


class QualityFlags(BaseModel):
    possible_duplicate: bool = False
    low_confidence_fields: List[str] = Field(default_factory=list)
    proposed_new_topics: List[str] = Field(default_factory=list)
    proposed_new_tags: List[str] = Field(default_factory=list)


class Author(BaseModel):
    name: str
    orcid: Optional[str] = Field(
        None,
        description="ORCID identifier if explicitly mentioned"
    )


class LLMExtractionSchema(BaseModel):
    suggested_title: Optional[str]
    summary: Optional[str]

    category: str = Field(description="Single best-fit category for this document")
    topics: List[str]
    tags: List[str]

    authors: List[Author]
    creation_date: Optional[date]

    glossary_terms: List[GlossaryTerm]
    quality_flags: QualityFlags


# ============================================================
# 4. Pydantic Schemas — Final System of Record
# ============================================================

class FinalGlossaryTerm(BaseModel):
    term: str
    definition: Optional[str]
    source: str = "llm_extracted"


class FinalFileRecord(BaseModel):
    # Identity
    file_id: UUID
    original_path: str
    file_type: str
    content_hash: str  # SHA-256 hash of file content

    # Naming
    title: str
    suggested_filename: str  # Generated from title and metadata

    # Organization
    category: str

    # Dates
    creation_date: Optional[date]
    last_modified_date: datetime
    analysis_date: datetime

    # People
    authors: List[Author]

    # Semantics
    topics: List[str]
    tags: List[str]
    summary: str

    # Knowledge enrichment
    glossary_terms: List[FinalGlossaryTerm]

    # Quality & governance
    possible_duplicate: bool
    reviewed_by_human: bool = False

    # Traceability
    llm_model: str
    extracted_at: datetime


# ============================================================
# 5. Mapping Function (LLM → Final)
# ============================================================

def sanitize_filename(text: str, max_length: int = 100) -> str:
    """Convert text to a safe filename."""
    # Remove or replace problematic characters
    text = re.sub(r'[<>:"/\\|?*]', '-', text)
    # Replace multiple spaces/hyphens with single hyphen
    text = re.sub(r'[\s\-]+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length].rstrip('-')
    return text or "untitled"


def generate_suggested_filename(
    title: str,
    topics: List[str],
    authors: List[Author],
    creation_date: Optional[date],
    file_type: str,
) -> str:
    """Generate a suggested filename from metadata."""
    parts = []
    
    # Add date prefix if available
    if creation_date:
        parts.append(creation_date.strftime("%Y-%m-%d"))
    
    # Add topics prefix (first topic, sanitized)
    if topics:
        topic_part = sanitize_filename(topics[0], max_length=30)
        parts.append(topic_part)
    
    # Add speaker (first author, sanitised)
    if authors:
        author_part = sanitize_filename(authors[0].name, max_length=30)
        parts.append(author_part)
    
    # Add sanitized title
    title_part = sanitize_filename(title, max_length=50)
    parts.append(title_part)
    
    # Join parts and add extension
    filename = "__".join(parts)
    if not filename:
        filename = "untitled"
    
    return f"{filename}.{file_type}" if file_type else filename


def build_final_record(
    llm_result: LLMExtractionSchema,
    file_path: Path,
    llm_model_name: str,
) -> FinalFileRecord:
    stat = file_path.stat()
    # Read file content once for hash computation
    file_bytes = file_path.read_bytes()
    content_hash = hashlib.sha256(file_bytes).hexdigest()
    
    title = llm_result.suggested_title or file_path.stem
    file_type = file_path.suffix.lstrip(".") or "txt"

    return FinalFileRecord(
        file_id=uuid4(),
        original_path=str(file_path),
        file_type=file_type,
        content_hash=content_hash,

        title=title,
        suggested_filename=generate_suggested_filename(
            title=title,
            topics=llm_result.topics,
            authors=llm_result.authors,
            creation_date=llm_result.creation_date,
            file_type=file_type,
        ),

        category=llm_result.category,

        creation_date=llm_result.creation_date,
        last_modified_date=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        analysis_date=datetime.now(timezone.utc),

        authors=llm_result.authors,

        topics=llm_result.topics,
        tags=llm_result.tags,
        summary=llm_result.summary or "",

        glossary_terms=[
            FinalGlossaryTerm(
                term=g.term,
                definition=g.definition
            )
            for g in llm_result.glossary_terms
        ],

        possible_duplicate=llm_result.quality_flags.possible_duplicate,
        reviewed_by_human=False,

        llm_model=llm_model_name,
        extracted_at=datetime.now(timezone.utc),
    )


# ============================================================
# 6. LLM Setup
# ============================================================

llm = get_chat_llm(temperature=0)

structured_llm = llm.with_structured_output(LLMExtractionSchema)


# ============================================================
# 7. Prompt
# ============================================================

system_prompt = f"""
You are assisting an academic medical department in organizing internal presentations.

STRICT RULES:
- Use ONLY information explicitly present in the document.
- DO NOT guess names, dates, or identifiers.
- If uncertain, return null or empty lists and record this in quality_flags.low_confidence_fields.
- ORCID identifiers must only be included if explicitly written in the text.

CATEGORIES (choose exactly ONE from this list - pick the best fit):
{CATEGORIES}

KNOWN TOPICS (reuse if applicable):
{KNOWN_TOPICS}

KNOWN TAGS (reuse if applicable):
{KNOWN_TAGS}

If you encounter a topic or tag that is clearly relevant but NOT in the known lists:
- Still include it
- ALSO add it to quality_flags.proposed_new_topics or proposed_new_tags

Glossary terms should focus on scientific or technical concepts.
"""

human_prompt = """
DOCUMENT TEXT:
----------------
{text}
----------------

Extract structured metadata for this document.
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", human_prompt),
    ]
)

chain = prompt | structured_llm


# ============================================================
# 8. Example Run
# ============================================================

if __name__ == "__main__":
    example_text = """
    Capita Selecta Lecture – November 14, 2023

    Speaker: Dr. John Smith
    ORCID: 0000-0002-1825-0097

    This lecture introduces survival analysis methods used in clinical research.
    Topics include time-to-event data, Kaplan-Meier curves,
    and Cox proportional hazards models.
    """

    # Create example file
    example_file = ASSETS_DIR / "example_presentation.txt"
    example_file.write_text(example_text, encoding="utf-8")
    print(f"Created example file at: {example_file.absolute()}")

    # Run LLM extraction
    llm_result = chain.invoke({"text": example_text})

    # Build final system record
    final_record = build_final_record(
        llm_result=llm_result,
        file_path=example_file,
        llm_model_name="gpt-4o-mini",
    )

    print("\n=== LLM EXTRACTION (UNTRUSTED) ===")
    print(llm_result.model_dump_json(indent=2))

    print("\n=== FINAL FILE RECORD (SYSTEM OF RECORD) ===")
    print(final_record.model_dump_json(indent=2))
