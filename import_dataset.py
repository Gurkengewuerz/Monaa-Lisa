#!/usr/bin/env python3
"""
Import MonaaLisa_dataset_full.jsonl into the Postgres database.

Usage:
    python import_dataset.py [--file MonaaLisa_dataset_full.jsonl] [--batch-size 5000]

Requirements:
    pip install psycopg2-binary  (already in requirements.txt)

Strategy:
    1. Read JSONL line-by-line (memory-safe for 5 GB+)
    2. Batch-insert papers via COPY (fastest Postgres bulk method)
    3. Collect citation/reference links and batch-insert them via COPY
    4. Skip duplicates gracefully using a temp table + INSERT ... ON CONFLICT

12-February-2026 – Basti
"""

import argparse
import io
import json
import os
import sys
import time
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_dt(value: str | None) -> str | None:
    """Return an ISO timestamp string or None."""
    if not value:
        return None
    try:
        # Dataset uses format like "2007-03-31T22:45:05"
        dt = datetime.fromisoformat(value)
        return dt.isoformat()
    except Exception:
        return None


def make_hash(entry_id: str, title: str) -> str:
    """No longer needed — kept as stub."""
    return ""


def escape_copy(value) -> str:
    """Escape a value for Postgres COPY TSV format."""
    if value is None:
        return "\\N"
    s = str(value)
    # Escape backslashes, tabs, newlines for COPY TEXT format
    s = s.replace("\\", "\\\\")
    s = s.replace("\t", "\\t")
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    return s


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_connection():
    """Create a psycopg2 connection from DATABASE_URL or individual env vars."""
    url = os.environ.get("DATABASE_URL")
    if url:
        # The SQLAlchemy-style URL uses postgresql+psycopg2:// but psycopg2
        # expects postgresql://  – strip the driver part.
        url = url.replace("postgresql+psycopg2://", "postgresql://")
        return psycopg2.connect(url)

    # Fallback: compose from env vars used in docker-compose
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ.get("POSTGRES_USER", "monaa"),
        password=os.environ.get("POSTGRES_PASSWORD", "monaa"),
        dbname=os.environ.get("POSTGRES_DB", "monaa"),
    )


def ensure_schema(conn):
    """Drop FK constraints on link tables so bulk import works."""
    with conn.cursor() as cur:
        for constraint in [
            ("paper_citation", "paper_citation_belonging_paper_entry_id_fkey"),
            ("paper_citation", "paper_citation_cited_paper_entry_id_fkey"),
            ("paper_reference", "paper_reference_belonging_paper_entry_id_fkey"),
            ("paper_reference", "paper_reference_referenced_paper_entry_id_fkey"),
        ]:
            cur.execute(f"ALTER TABLE {constraint[0]} DROP CONSTRAINT IF EXISTS {constraint[1]};")
    conn.commit()
    print("[schema] FK constraints on link tables dropped.")


# ---------------------------------------------------------------------------
# COPY-based bulk insert
# ---------------------------------------------------------------------------

PAPER_COLS = [
    "entry_id", "title", "authors", "abstract", "categories",
    "published", "updated", "doi", "journal_ref", "license",
    "url", "s2_id", "non_arxiv_citation_count", "non_arxiv_reference_count",
]

PAPER_CITATION_COLS = ["belonging_paper_entry_id", "cited_paper_entry_id"]
PAPER_REFERENCE_COLS = ["belonging_paper_entry_id", "referenced_paper_entry_id"]


def flush_papers(conn, rows: list[tuple]):
    """Bulk-insert papers via a temp table + ON CONFLICT.

    Uses a two-stage approach:
    1. Try fast bulk INSERT via COPY + temp table.
    2. If that fails (e.g. duplicate hash/s2_id across different entry_ids),
       fall back to row-by-row upsert so only the conflicting row is skipped.
    """
    if not rows:
        return
    cols = ", ".join(PAPER_COLS)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TEMP TABLE _tmp_paper (LIKE paper INCLUDING DEFAULTS)
                ON COMMIT DROP;
            """)
            cur.execute("ALTER TABLE _tmp_paper DROP COLUMN id;")

            buf = io.StringIO()
            for row in rows:
                buf.write("\t".join(escape_copy(v) for v in row) + "\n")
            buf.seek(0)

            cur.copy_from(buf, "_tmp_paper", columns=PAPER_COLS)

            cur.execute(f"""
                INSERT INTO paper ({cols})
                SELECT {cols} FROM _tmp_paper
                ON CONFLICT (entry_id) DO UPDATE SET
                    title     = EXCLUDED.title,
                    authors   = EXCLUDED.authors,
                    abstract  = EXCLUDED.abstract,
                    categories = EXCLUDED.categories,
                    published = EXCLUDED.published,
                    updated   = EXCLUDED.updated,
                    doi       = EXCLUDED.doi,
                    journal_ref = EXCLUDED.journal_ref,
                    license   = EXCLUDED.license,
                    url       = EXCLUDED.url,
                    s2_id     = EXCLUDED.s2_id,
                    non_arxiv_citation_count  = EXCLUDED.non_arxiv_citation_count,
                    non_arxiv_reference_count = EXCLUDED.non_arxiv_reference_count;
            """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[warn] Bulk insert failed ({e}), falling back to row-by-row upsert...")
        _flush_papers_rowwise(conn, cols, rows)


def _flush_papers_rowwise(conn, cols: str, rows: list[tuple]):
    """Fallback: insert papers one by one, skipping rows that violate constraints."""
    placeholders = ", ".join(["%s"] * len(PAPER_COLS))
    skipped = 0
    for row in rows:
        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO paper ({cols}) VALUES ({placeholders})
                    ON CONFLICT (entry_id) DO UPDATE SET
                        title     = EXCLUDED.title,
                        authors   = EXCLUDED.authors,
                        abstract  = EXCLUDED.abstract,
                        categories = EXCLUDED.categories,
                        published = EXCLUDED.published,
                        updated   = EXCLUDED.updated,
                        doi       = EXCLUDED.doi,
                        journal_ref = EXCLUDED.journal_ref,
                        license   = EXCLUDED.license,
                        url       = EXCLUDED.url,
                        s2_id     = EXCLUDED.s2_id,
                        non_arxiv_citation_count  = EXCLUDED.non_arxiv_citation_count,
                        non_arxiv_reference_count = EXCLUDED.non_arxiv_reference_count;
                """, row)
            conn.commit()
        except Exception:
            conn.rollback()
            skipped += 1
    if skipped:
        print(f"[warn] Skipped {skipped} papers due to constraint violations.")


def flush_links(conn, table: str, cols: list[str], rows: list[tuple]):
    """Bulk-insert citation/reference links via temp table + ON CONFLICT."""
    if not rows:
        return
    with conn.cursor() as cur:
        tmp = f"_tmp_{table}"
        cur.execute(f"""
            CREATE TEMP TABLE {tmp} (
                {cols[0]} TEXT NOT NULL,
                {cols[1]} TEXT NOT NULL
            ) ON COMMIT DROP;
        """)

        buf = io.StringIO()
        for row in rows:
            buf.write(f"{escape_copy(row[0])}\t{escape_copy(row[1])}\n")
        buf.seek(0)

        cur.copy_from(buf, tmp, columns=cols)

        col_list = ", ".join(cols)
        cur.execute(f"""
            INSERT INTO {table} ({col_list})
            SELECT {col_list} FROM {tmp}
            ON CONFLICT DO NOTHING;
        """)
    conn.commit()


# ---------------------------------------------------------------------------
# Main import loop
# ---------------------------------------------------------------------------

def import_dataset(filepath: str, batch_size: int = 5000):
    conn = get_connection()
    print(f"[db] Connected to {conn.dsn}")
    ensure_schema(conn)

    paper_batch: list[tuple] = []
    citation_batch: list[tuple] = []
    reference_batch: list[tuple] = []

    total_papers = 0
    total_citations = 0
    total_references = 0
    t0 = time.time()

    with open(filepath, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[warn] Skipping line {line_no}: {e}")
                continue

            entry_id = rec.get("id", "").strip()
            if not entry_id:
                continue

            title = rec.get("title", "").strip()
            authors = rec.get("authors", None)
            abstract = rec.get("abstract", None)
            published = parse_dt(rec.get("published"))
            updated = parse_dt(rec.get("updated"))
            categories = rec.get("categories", None)
            doi = rec.get("doi", None)
            journal_ref = rec.get("journal_ref", None)
            license_val = rec.get("license", None)
            url = rec.get("url", None)
            s2_id = rec.get("s2_id", None)
            non_arxiv_cit = rec.get("non_arxiv_citation_count", None)
            non_arxiv_ref = rec.get("non_arxiv_reference_count", None)
            paper_row = (
                entry_id, title, authors, abstract, categories,
                published, updated, doi, journal_ref,
                license_val, url, s2_id, non_arxiv_cit, non_arxiv_ref,
            )
            paper_batch.append(paper_row)
            total_papers += 1

            # Citations (arXiv IDs this paper is cited by)
            for cit_id in (rec.get("citations") or []):
                cit_id = cit_id.strip()
                if cit_id:
                    citation_batch.append((entry_id, cit_id))
                    total_citations += 1

            # References (arXiv IDs this paper references)
            for ref_id in (rec.get("references") or []):
                ref_id = ref_id.strip()
                if ref_id:
                    reference_batch.append((entry_id, ref_id))
                    total_references += 1

            # Flush papers when batch is full
            if len(paper_batch) >= batch_size:
                flush_papers(conn, paper_batch)
                paper_batch.clear()

            # Flush links when they accumulate (links can be much larger)
            if len(citation_batch) >= batch_size * 5:
                flush_links(conn, "paper_citation", PAPER_CITATION_COLS, citation_batch)
                citation_batch.clear()

            if len(reference_batch) >= batch_size * 5:
                flush_links(conn, "paper_reference", PAPER_REFERENCE_COLS, reference_batch)
                reference_batch.clear()

            if line_no % 50000 == 0:
                elapsed = time.time() - t0
                rate = total_papers / elapsed if elapsed > 0 else 0
                print(
                    f"[progress] {total_papers:>10,} papers | "
                    f"{total_citations:>10,} citations | "
                    f"{total_references:>10,} references | "
                    f"{rate:,.0f} papers/s"
                )

    # Flush remaining
    flush_papers(conn, paper_batch)
    flush_links(conn, "paper_citation", PAPER_CITATION_COLS, citation_batch)
    flush_links(conn, "paper_reference", PAPER_REFERENCE_COLS, reference_batch)

    elapsed = time.time() - t0
    print(
        f"\n[done] Imported {total_papers:,} papers, "
        f"{total_citations:,} citations, {total_references:,} references "
        f"in {elapsed:.1f}s"
    )

    conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import MonaaLisa JSONL dataset into Postgres")
    parser.add_argument(
        "--file", "-f",
        default="MonaaLisa_dataset_full.jsonl",
        help="Path to the JSONL file (default: MonaaLisa_dataset_full.jsonl)",
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=5000,
        help="Number of papers per batch INSERT (default: 5000)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"[error] File not found: {args.file}")
        sys.exit(1)

    import_dataset(args.file, args.batch_size)
