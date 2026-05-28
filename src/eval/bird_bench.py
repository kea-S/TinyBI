import pandas as pd
import logging
from src.utils.database import global_database
from src.config import TABLE_DATA_PATH, SQLITE_DATA_PATH

logger = logging.getLogger(__name__)


def check_execution_accuracy(df_output: pd.DataFrame,
                             expected_sql: str) -> bool:
    """
    Compares the results of the generated SQL vs the Gold SQL.
    Used by Promptfoo for Execution Accuracy (EX) benchmarking.
    """
    try:
        # 1. Setup Database Connection
        # Ensure we are pointing to the financial DB used in BIRD
        global_database.setup_database(TABLE_DATA_PATH,
                                        SQLITE_DATA_PATH)

        # 3. Execute Gold SQL (the ground truth)
        gold_sql = expected_sql.strip()
        try:
            gold_df = global_database.query(gold_sql)
        except Exception as e:
            logger.error(f"Gold SQL failed to execute: {e}")
            # If gold fails, it's a benchmark data issue, but we still return False
            return False

        # 4. Compare Results
        # We use pandas.testing.assert_frame_equal or a manual comparison
        # that is robust to column ordering/naming.
        if df_output.empty and gold_df.empty:
            return True

        if len(df_output) != len(gold_df):
            return False

        # Basic "Set" comparison: are the rows the same?
        # 1. Normalize column ordering
        # 2. Sort both by all columns to normalize row order
        # 3. Reset index
        # 4. Compare values
        try:
            # Sort columns alphabetically to ensure same column order
            df_output = df_output.reindex(sorted(df_output.columns), axis=1)
            gold_df = gold_df.reindex(sorted(gold_df.columns), axis=1)

            # Sort rows by all columns
            gen_sorted = df_output.sort_values(by=list(df_output.columns)).reset_index(drop=True)
            gold_sorted = gold_df.sort_values(by=list(gold_df.columns)).reset_index(drop=True)

            # We compare the values only, ignoring original index
            pd.testing.assert_frame_equal(gen_sorted, gold_sorted, check_column_type=False, check_names=False)
            return True
        except Exception:
            # If standard comparison fails, try a more relaxed one
            # e.g. checking if all values exist in both
            return False

    except Exception as e:
        logger.exception(f"Assertion error: {e}")
        return False
    finally:
        global_database.close_connection()
