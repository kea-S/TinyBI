from src.llms.main_pipeline import run_pipeline


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
                _, resulting_df, explainer_results = run_pipeline(question)
                print(resulting_df)
                print(explainer_results)
            except Exception as e:
                # Keep the loop alive on errors so the user can continue asking questions
                print(f"Error running pipeline: {e}")

    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")


if __name__ == "__main__":
    main()
