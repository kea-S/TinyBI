import sqlite3
import os

def prune_db(db_path: str, keep: int = 2) -> None:
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Delete eval_results not belonging to the latest `keep` evals
    cursor.execute("""
        DELETE FROM eval_results WHERE eval_id NOT IN (
            SELECT id FROM evals ORDER BY created_at DESC LIMIT ?
        )
    """, (keep,))
    
    # Delete evals not in the latest `keep` evals
    cursor.execute("""
        DELETE FROM evals WHERE id NOT IN (
            SELECT id FROM evals ORDER BY created_at DESC LIMIT ?
        )
    """, (keep,))
    
    # Clean up orphaned metadata/links if present
    for table in ["evals_to_datasets", "evals_to_prompts", "evals_to_tags"]:
        try:
            cursor.execute(f"""
                DELETE FROM {table} WHERE eval_id NOT IN (
                    SELECT id FROM evals
                )
            """)
        except sqlite3.OperationalError:
            pass

    conn.commit()
    cursor.execute("VACUUM")
    conn.close()

if __name__ == "__main__":
    db_file = "data/promptfoo_store/promptfoo.db"
    print(f"Pruning {db_file} to keep last 2 evals...")
    prune_db(db_file, keep=2)
    print("Done!")
