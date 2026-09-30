import os
import sqlite3

def migrate():
    db_paths = [
        "services/api/krishinet_dev.db",
        "krishinet_dev.db",
    ]
    cols = [
        ("advisories", "prompt_version", "VARCHAR(32) DEFAULT 'v1.0.0' NOT NULL"),
        ("advisories", "engine_mode", "VARCHAR(32) DEFAULT 'hybrid' NOT NULL"),
        ("advisories", "language", "VARCHAR(10) DEFAULT 'en' NOT NULL"),
        ("advisories", "execution_trace", "JSON DEFAULT '{}' NOT NULL"),
        ("advisories", "full_advisory_json", "JSON DEFAULT '{}' NOT NULL"),
        ("knowledge_documents", "language", "VARCHAR(10) DEFAULT 'en' NOT NULL"),
        ("knowledge_documents", "crop_tags", "JSON DEFAULT '[]' NOT NULL"),
        ("knowledge_documents", "region_tags", "JSON DEFAULT '[]' NOT NULL"),
        ("knowledge_documents", "published_year", "INTEGER"),
        ("knowledge_chunks", "tsv_content", "TEXT"),
    ]

    for db_path in db_paths:
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            for tbl, col, typedef in cols:
                try:
                    cur.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typedef}")
                    print(f"Added {col} to {tbl} in {db_path}")
                except Exception as e:
                    print(f"Column {col} already exists or error: {e}")
            conn.commit()
            conn.close()
    print("Migration finished successfully!")

if __name__ == "__main__":
    migrate()
