import sqlite3
import pytest
from pathlib import Path
from scripts.prune_promptfoo_db import prune_db

def test_prune_db(tmp_path: Path):
    db_path = tmp_path / "promptfoo_test.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE evals (
            id TEXT PRIMARY KEY,
            created_at INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE eval_results (
            id TEXT PRIMARY KEY,
            eval_id TEXT,
            FOREIGN KEY(eval_id) REFERENCES evals(id)
        )
    """)
    
    # Insert 5 evals
    for i in range(1, 6):
        eval_id = f"eval-{i}"
        cursor.execute("INSERT INTO evals (id, created_at) VALUES (?, ?)", (eval_id, i * 1000))
        cursor.execute("INSERT INTO eval_results (id, eval_id) VALUES (?, ?)", (f"res-{i}", eval_id))
    
    conn.commit()
    conn.close()

    # Prune keeping only 2
    prune_db(str(db_path), keep=2)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM evals ORDER BY created_at ASC")
    remaining_evals = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT id FROM eval_results")
    remaining_results = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert remaining_evals == ["eval-4", "eval-5"]
    assert sorted(remaining_results) == ["res-4", "res-5"]
