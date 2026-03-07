import duckdb
from pathlib import Path

# ...existing code...
_conn = None


def get_connection():
    """Return a singleton in-memory DuckDB connection for this kernel."""
    global _conn
    if _conn is None:
        _conn = duckdb.connect(database=":memory:")
    return _conn


def register_csv_as_view(csv_path, view_name=None, conn=None, auto_detect=True, **read_opts):
    """
    Create or replace a view that selects from the CSV via read_csv_auto/read_csv.
    Use view_name to reference the CSV in subsequent SQL queries.
    """
    conn = conn or get_connection()
    csv_path = Path(csv_path).expanduser().resolve()
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    view_name = view_name or csv_path.stem.replace("-", "_")
    read_fn = "read_csv_auto" if auto_detect else "read_csv"

    opts = []
    for k, v in read_opts.items():
        if isinstance(v, bool):
            v_str = "true" if v else "false"
        else:
            v_str = f"'{v}'"
        opts.append(f"{k} => {v_str}")
    opts_sql = ", " + ", ".join(opts) if opts else ""

    conn.execute(
        f"""CREATE OR REPLACE VIEW {view_name} AS
        SELECT * FROM {read_fn}('{csv_path.as_posix()}'{opts_sql})""")

    return view_name


def query(sql, conn=None):
    """Execute SQL on the shared connection and return a pandas DataFrame (requires pandas)."""
    conn = conn or get_connection()

    return conn.execute(sql).fetchdf()


def close_connection():
    """Close the shared connection (optional)."""
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
