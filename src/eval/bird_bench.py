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
        if global_database._database is None:
            global_database.setup_database(TABLE_DATA_PATH, SQLITE_DATA_PATH, read_only=True)

        gold_sql = expected_sql.strip()
        try:
            gold_df = global_database.query(gold_sql)
        except Exception as e:
            logger.error(f"Gold SQL failed to execute: {e}")
            return False

        if df_output.empty and gold_df.empty:
            return True

        if len(df_output) != len(gold_df):
            return False

        try:
            df_output = df_output.reindex(sorted(df_output.columns), axis=1)
            gold_df = gold_df.reindex(sorted(gold_df.columns), axis=1)

            gen_sorted = df_output.sort_values(by=list(df_output.columns)).reset_index(drop=True)
            gold_sorted = gold_df.sort_values(by=list(gold_df.columns)).reset_index(drop=True)

            pd.testing.assert_frame_equal(gen_sorted, gold_sorted, check_column_type=False, check_names=False)
            return True
        except Exception:
            return False

    except Exception as e:
        logger.exception(f"Assertion error: {e}")
        return False
