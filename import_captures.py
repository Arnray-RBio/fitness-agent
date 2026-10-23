import json
import sqlite3
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
CAPTURE_DIR = PROJECT_DIR / "data" / "captures"
DATABASE_PATH = PROJECT_DIR / "data" / "fitness_agent.db"


def main():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    imported = 0
    skipped = 0
    invalid = 0

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS captures (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL UNIQUE,
                source_url TEXT NOT NULL,
                checked_at_utc TEXT NOT NULL,
                brand_name TEXT,
                review_status TEXT NOT NULL,
                extraction_json TEXT NOT NULL,
                webpage_text TEXT NOT NULL
            )
        """)

        for json_path in sorted(CAPTURE_DIR.glob("*.json")):
            text_path = json_path.with_suffix(".txt")

            try:
                capture = json.loads(
                    json_path.read_text(encoding="utf-8")
                )
                webpage_text = text_path.read_text(encoding="utf-8")

                source_url = capture["source_url"]
                checked_at = capture["checked_at_utc"]
                venue = capture["venue"]

                if not isinstance(venue, dict):
                    raise ValueError("venue must be an object")

                if not isinstance(source_url, str) or not source_url:
                    raise ValueError("Missing source URL")

                if not isinstance(checked_at, str) or not checked_at:
                    raise ValueError("Missing retrieval timestamp")

                # All imported extractions remain unreviewed.
                cursor = connection.execute("""
                    INSERT INTO captures (
                        filename,
                        source_url,
                        checked_at_utc,
                        brand_name,
                        review_status,
                        extraction_json,
                        webpage_text
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(filename) DO NOTHING
                """, (
                    json_path.name,
                    source_url,
                    checked_at,
                    venue.get("name"),
                    "needs_manual_review",
                    json.dumps(capture, ensure_ascii=False),
                    webpage_text,
                ))

                if cursor.rowcount == 1:
                    imported += 1
                else:
                    skipped += 1

            except (
                OSError,
                ValueError,
                KeyError,
                TypeError,
                sqlite3.Error,
            ) as error:
                invalid += 1
                print(f"Could not import {json_path.name}: {error}")

        total = connection.execute(
            "SELECT COUNT(*) FROM captures"
        ).fetchone()[0]

    print(f"New captures imported: {imported}")
    print(f"Already imported: {skipped}")
    print(f"Files needing attention: {invalid}")
    print(f"Total stored captures: {total}")
    print(f"Database: {DATABASE_PATH}")


if __name__ == "__main__":
    main()