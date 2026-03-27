import argparse
import csv
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = PROJECT_ROOT / "rag_dataset" / "raw"
PROCESSED_ROOT = PROJECT_ROOT / "rag_dataset" / "processed"
MANIFEST_PATH = PROCESSED_ROOT / "manifest.csv"
CHUNKS_PATH = PROCESSED_ROOT / "chunks.jsonl"
SUPPORTED_EXTENSIONS = {".md", ".txt"}
DEFAULT_MIN_WORDS = 90
DEFAULT_MAX_WORDS = 180


def parse_args():
    parser = argparse.ArgumentParser(description="Build AutoMentor RAG dataset from raw notes.")
    parser.add_argument("--raw-root", type=Path, default=RAW_ROOT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--chunks", type=Path, default=CHUNKS_PATH)
    parser.add_argument("--min-words", type=int, default=DEFAULT_MIN_WORDS)
    parser.add_argument("--max-words", type=int, default=DEFAULT_MAX_WORDS)
    return parser.parse_args()


def parse_note_file(path: Path) -> tuple[dict, str]:
    raw_text = path.read_text(encoding="utf-8")
    lines = raw_text.splitlines()

    metadata: dict[str, str] = {}
    body_start = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            body_start = index + 1
            break
        if ":" not in stripped:
            raise ValueError(f"{path} has invalid metadata line: {line}")
        key, value = stripped.split(":", 1)
        metadata[key.strip()] = value.strip()

    body = "\n".join(lines[body_start:]).strip()
    if not body:
        raise ValueError(f"{path} does not contain note body text")

    metadata.setdefault("subject", path.parent.name.title())
    metadata.setdefault("unit", "")
    metadata.setdefault("topic", path.stem.replace("_", " ").title())
    metadata.setdefault("source_type", "lecture_notes")
    metadata.setdefault("source_name", path.name)
    metadata.setdefault("difficulty", "medium")
    metadata.setdefault("question_type", "concept")
    return metadata, body


def split_into_paragraphs(text: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    return paragraphs or [text.strip()]


def make_chunks(text: str, min_words: int, max_words: int) -> list[str]:
    paragraphs = split_into_paragraphs(text)
    chunks: list[str] = []
    buffer: list[str] = []
    word_count = 0

    for paragraph in paragraphs:
        words = paragraph.split()
        paragraph_words = len(words)
        if buffer and word_count + paragraph_words > max_words:
            chunks.append("\n\n".join(buffer).strip())
            buffer = []
            word_count = 0

        buffer.append(paragraph)
        word_count += paragraph_words

        if word_count >= min_words:
            chunks.append("\n\n".join(buffer).strip())
            buffer = []
            word_count = 0

    if buffer:
        chunks.append("\n\n".join(buffer).strip())

    return [chunk for chunk in chunks if chunk]


def slugify(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9]+", "_", lowered)
    return lowered.strip("_")


def iter_note_files(raw_root: Path):
    for path in sorted(raw_root.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def build_dataset(raw_root: Path, min_words: int, max_words: int) -> tuple[list[dict], list[dict]]:
    manifest_rows: list[dict] = []
    chunk_rows: list[dict] = []

    for path in iter_note_files(raw_root):
        metadata, body = parse_note_file(path)
        manifest_rows.append(
            {
                "subject": metadata["subject"],
                "unit": metadata["unit"],
                "topic": metadata["topic"],
                "source_type": metadata["source_type"],
                "source_name": metadata["source_name"],
                "difficulty": metadata["difficulty"],
                "question_type": metadata["question_type"],
            }
        )

        for index, chunk_text in enumerate(make_chunks(body, min_words, max_words), start=1):
            chunk_rows.append(
                {
                    "chunk_id": f"{slugify(metadata['subject'])}_{slugify(metadata['topic'])}_{index:02d}",
                    "subject": metadata["subject"],
                    "unit": metadata["unit"],
                    "topic": metadata["topic"],
                    "source_type": metadata["source_type"],
                    "source_name": metadata["source_name"],
                    "difficulty": metadata["difficulty"],
                    "question_type": metadata["question_type"],
                    "text": " ".join(chunk_text.split()),
                }
            )

    return manifest_rows, chunk_rows


def write_manifest(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "subject",
        "unit",
        "topic",
        "source_type",
        "source_name",
        "difficulty",
        "question_type",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_chunks(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def main():
    args = parse_args()
    manifest_rows, chunk_rows = build_dataset(args.raw_root, args.min_words, args.max_words)
    write_manifest(args.manifest, manifest_rows)
    write_chunks(args.chunks, chunk_rows)
    print(f"Built manifest: {args.manifest}")
    print(f"Built chunks:   {args.chunks}")
    print(f"Source files:   {len(manifest_rows)}")
    print(f"Chunks:         {len(chunk_rows)}")


if __name__ == "__main__":
    main()
