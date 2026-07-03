import argparse
import datetime as dt
import json
import re
import unicodedata
from pathlib import Path


HTML_ESCAPE_TABLE = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
}


def html_escape(text):
    return "".join(HTML_ESCAPE_TABLE.get(char, char) for char in str(text))


def slugify(value):
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "publication"


def infer_category(record):
    venue = str(record.get("venue", "")).lower()
    title = str(record.get("title", "")).lower()
    searchable = f"{venue} {title}"

    book_keywords = [
        "studies in computational intelligence",
        "edited volume",
        "book chapter",
        "chapter",
    ]
    conference_keywords = [
        "proceedings",
        "conference",
        "workshop",
        "symposium",
        "recsys",
        "clei",
        "summarization workshop",
        "coling",
        "emnlp",
        "brazilian symposium",
    ]
    manuscript_keywords = [
        "journal",
        "transactions",
        "frontiers",
        "arxiv",
        "preprint",
        "physica",
        "expert systems",
        "world patent information",
        "universit",
        "thesis",
    ]

    if any(keyword in searchable for keyword in book_keywords):
        return "books"
    if any(keyword in searchable for keyword in conference_keywords):
        return "conferences"
    if any(keyword in searchable for keyword in manuscript_keywords):
        return "manuscripts"
    return "manuscripts"


def format_authors(authors):
    authors = [author.strip() for author in authors if str(author).strip()]
    if not authors:
        return "Unknown author"
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} and {authors[1]}"
    return ", ".join(authors[:-1]) + f", and {authors[-1]}"


def build_citation(record):
    authors = format_authors(record.get("authors", []))
    year = record.get("year", "n.d.")
    title = html_escape(record.get("title", "Untitled"))
    venue = html_escape(record.get("venue", "Venue unavailable"))
    return f"{html_escape(authors)}. ({year}). &quot;{title}.&quot; <i>{venue}</i>."


def build_body(record, citation):
    sections = []
    abstract = str(record.get("abstract") or "").strip()
    if abstract:
        sections.append(html_escape(abstract))

    key_phrases = [phrase.strip() for phrase in record.get("key_phrases", []) if str(phrase).strip()]
    if key_phrases:
        sections.append("Keywords: " + ", ".join(html_escape(phrase) for phrase in key_phrases))

    notes = str(record.get("notes") or "").strip()
    if notes:
        sections.append("Note: " + html_escape(notes))

    sections.append("Recommended citation: " + citation)
    return "\n\n".join(sections) + "\n"


def publication_date(year, year_index):
    base_date = dt.date(int(year), 12, 31)
    return base_date - dt.timedelta(days=year_index)


def excerpt_text(record):
    return str(record.get("abstract") or record.get("notes") or "").strip()


def markdown_for_record(record, publication_date_value):
    title = html_escape(record.get("title", "Untitled"))
    slug = slugify(record.get("title", "publication"))
    date_text = publication_date_value.isoformat()
    category = infer_category(record)
    citation = build_citation(record)
    excerpt = excerpt_text(record)
    paper_url = str(record.get("paperurl") or record.get("paper_url") or "").strip()
    slides_url = str(record.get("slidesurl") or record.get("slides_url") or "").strip()

    lines = [
        "---",
        f'title: "{title}"',
        "collection: publications",
        f"category: {category}",
        f"permalink: /publication/{date_text}-{slug}",
    ]

    if excerpt:
        lines.append(f"excerpt: '{html_escape(excerpt)}'")

    lines.extend([
        f"date: {date_text}",
        f"venue: '{html_escape(record.get('venue', 'Venue unavailable'))}'",
    ])

    if paper_url:
        lines.append(f"paperurl: '{paper_url}'")
    if slides_url:
        lines.append(f"slidesurl: '{slides_url}'")

    lines.append(f"citation: '{citation}'")
    lines.append("---")

    if paper_url:
        lines.append(f"\n<a href='{paper_url}'>Download paper here</a>")

    lines.append("\n" + build_body(record, citation).rstrip())
    return "\n".join(lines) + "\n"


def load_records(input_path):
    with input_path.open("r", encoding="utf-8") as handle:
        records = json.load(handle)

    if not isinstance(records, list):
        raise ValueError("Expected a JSON array of publication records")
    return records


def write_publications(records, output_dir, clean=False):
    output_dir.mkdir(parents=True, exist_ok=True)

    if clean:
        for existing_file in output_dir.glob("*.md"):
            existing_file.unlink()

    year_offsets = {}

    for record in records:
        year = int(record["year"])
        offset = year_offsets.get(year, 0)
        year_offsets[year] = offset + 1

        date_value = publication_date(year, offset)
        slug = slugify(record.get("title", "publication"))
        filename = f"{date_value.isoformat()}-{slug}.md"
        content = markdown_for_record(record, date_value)
        (output_dir / filename).write_text(content, encoding="utf-8")


def parse_args():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    parser = argparse.ArgumentParser(description="Generate Academic Pages publication markdown from JSON")
    parser.add_argument(
        "--input",
        type=Path,
        default=repo_root / ".researcher_infos" / "publications.json",
        help="Path to the publications JSON file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root / "_publications",
        help="Directory where markdown files should be written",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing publication markdown files before writing new ones",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    records = load_records(args.input)
    write_publications(records, args.output_dir, clean=args.clean)


if __name__ == "__main__":
    main()


