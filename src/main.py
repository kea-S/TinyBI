import asyncio
import os

from src.llms.main_pipeline import run_pipeline
from src.utils.models import REMOTE_GPT_4o


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DEFAULT_MODEL = os.getenv("TINYBI_MODEL", REMOTE_GPT_4o)
DEFAULT_LOCAL = _env_flag("TINYBI_LOCAL", default=False)


def main():
    print("Chatbot ready. Type a question and press Enter. Type 'exit', 'quit', or Ctrl+D to quit.")
    try:
        while True:
            try:
                question = input("\nYou: ").strip()
            except EOFError:
                print("\nEOF received. Exiting.")
                break

            if not question:
                continue

            if question.lower() in {"exit", "quit", "q"}:
                print("Goodbye.")
                break

            try:
                resulting_df, explanation = asyncio.run(
                    run_pipeline(question, DEFAULT_MODEL, DEFAULT_LOCAL)
                )
                print(resulting_df)
                print(explanation)
            except Exception as e:
                # Keep the loop alive on errors so the user can continue asking questions.
                print(f"Error running pipeline: {e}")

    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")


if __name__ == "__main__":
    main()
