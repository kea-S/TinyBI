import json
import pandas as pd
from src.eval.bird_bench import check_execution_accuracy

def get_df_from_output(output):
    """
    Helper to extract DataFrame from provider output JSON.
    Expected format: {"metadata": {"data": [...]}}
    """
    try:
        data_dict = json.loads(output)
        df_data = data_dict.get("metadata", {}).get("data")
        if df_data is not None:
            return pd.DataFrame(df_data)
    except Exception:
        pass
    return pd.DataFrame()

def promptfoo_execution_accuracy(output, context, *args, **kwargs):
    """
    Promptfoo Python assertion for Execution Accuracy (EX).
    Called with (output, context) where context["vars"] holds test variables.
    """
    vars_ = context.get("vars", {}) if isinstance(context, dict) else {}
    expected_sql = vars_.get("expected_sql")
    if not expected_sql:
        return {"pass": False, "score": 0, "reason": "No expected_sql provided in vars"}

    # Extract the DataFrame result from the agent output
    df_output = get_df_from_output(output)
    
    # Use existing logic to compare
    is_correct = check_execution_accuracy(df_output, expected_sql)
    
    return {
        "pass": is_correct,
        "score": 1.0 if is_correct else 0.0,
        "reason": "Execution results match Gold SQL" if is_correct else "Execution results do not match Gold SQL"
    }
