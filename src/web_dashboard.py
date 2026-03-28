import argparse
import asyncio
import html
import json
from pathlib import Path
import traceback
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pandas as pd
from dotenv import load_dotenv

from src.llms.main_pipeline import run_pipeline_with_details
from src.utils.etl import OUTPUT_PATH
from src.utils.models import LOCAL_LLAMA3, REMOTE_GPT_4o, REMOTE_GPT_5, REMOTE_GPT_OSS_SMALL


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_MODEL = REMOTE_GPT_5


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Supermarket Query Dashboard</title>
  <style>
    :root {
      --bg: #f5f1e8;
      --panel: #fffaf2;
      --ink: #1c1a17;
      --muted: #6f675d;
      --line: #d8c8ad;
      --accent: #b44f2a;
      --accent-dark: #8e3a1b;
      --shadow: rgba(60, 36, 20, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(180, 79, 42, 0.12), transparent 30%),
        linear-gradient(180deg, #f7f2e8 0%, #efe6d6 100%);
    }
    .shell {
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }
    .hero {
      margin-bottom: 20px;
    }
    .hero h1 {
      margin: 0;
      font-size: clamp(2rem, 4vw, 3.5rem);
      line-height: 0.95;
      letter-spacing: -0.03em;
    }
    .hero p {
      margin: 10px 0 0;
      color: var(--muted);
      max-width: 700px;
      font-size: 1rem;
    }
    .grid {
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: 18px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 12px 30px var(--shadow);
    }
    .sidebar {
      padding: 18px;
      position: sticky;
      top: 20px;
      height: fit-content;
    }
    .sidebar h2, .chat h2 {
      margin: 0 0 12px;
      font-size: 1rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }
    .stat {
      margin-bottom: 16px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--line);
    }
    .stat:last-child {
      border-bottom: 0;
      margin-bottom: 0;
      padding-bottom: 0;
    }
    .label {
      display: block;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 6px;
    }
    .value {
      font-size: 1.3rem;
      font-weight: 700;
    }
    .examples {
      margin-top: 18px;
      padding-top: 18px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.95rem;
    }
    .examples button {
      width: 100%;
      text-align: left;
      margin-top: 8px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      cursor: pointer;
      font: inherit;
      color: var(--ink);
    }
    .chat {
      padding: 18px;
    }
    .toolbar {
      display: grid;
      grid-template-columns: 1fr 180px 160px 120px;
      gap: 10px;
      margin-bottom: 12px;
    }
    textarea, select, button {
      font: inherit;
    }
    textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      background: #fffdfa;
      color: var(--ink);
    }
    textarea {
      min-height: 110px;
      resize: vertical;
      grid-column: 1 / -1;
    }
    button.primary {
      border: 0;
      border-radius: 14px;
      background: var(--accent);
      color: white;
      cursor: pointer;
      padding: 0 16px;
      font-weight: 700;
    }
    button.primary:hover {
      background: var(--accent-dark);
    }
    .status {
      color: var(--muted);
      min-height: 1.2rem;
      margin-bottom: 12px;
    }
    .result-block {
      margin-top: 14px;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: #fff;
    }
    .result-block h3 {
      margin: 0 0 10px;
      font-size: 0.95rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.9rem;
      line-height: 1.5;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th, td {
      padding: 10px 12px;
      border-bottom: 1px solid #eee2cf;
      text-align: left;
      vertical-align: top;
    }
    th {
      font-size: 0.8rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
      background: #fcf7ee;
    }
    .error {
      color: #8b1e1e;
    }
    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
      .sidebar { position: static; }
      .toolbar { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="hero">
      <h1>Supermarket Query Dashboard</h1>
      <p>Ask natural-language supermarket pricing questions against the current local dataset. The current extraction scope is noodles so the underlying CSV contains noodle products for now.</p>
    </div>
    <div class="grid">
      <aside class="panel sidebar">
        <h2>Dataset</h2>
        <div class="stat">
          <span class="label">Rows</span>
          <div class="value">__ROW_COUNT__</div>
        </div>
        <div class="stat">
          <span class="label">Supermarkets</span>
          <div>__SUPERMARKETS__</div>
        </div>
        <div class="examples">
          <div>Examples</div>
          <button type="button" onclick="setQuestion('Give me the cheapest instant noodles globally')">Cheapest globally</button>
          <button type="button" onclick="setQuestion('Give me the cheapest instant noodles in Sheng Siong')">Cheapest in Sheng Siong</button>
          <button type="button" onclick="setQuestion('Give me the cheapest instant noodles that are not on sale in Sheng Siong')">Cheapest not on sale in Sheng Siong</button>
          <button type="button" onclick="setQuestion('Give me the cheapest instant noodles that are not on sale in Sheng Siong with a weight above 1 kilogram')">Not on sale, above 1 kilogram</button>
        </div>
      </aside>
      <main class="panel chat">
        <h2>Ask</h2>
        <div class="toolbar">
          <select id="model">
            <option value="__DEFAULT_MODEL__">GPT-5</option>
            <option value="__GPT4O__">GPT-4o</option>
            <option value="__GPTOSS__">GPT OSS 20B</option>
            <option value="__LOCALLLAMA__">Llama 3.1 Local</option>
          </select>
          <select id="local">
            <option value="false">Remote model</option>
            <option value="true">Local model</option>
          </select>
          <button class="primary" id="send" type="button">Send</button>
          <button id="clear" type="button">Clear</button>
          <textarea id="question" placeholder="Ask a supermarket pricing question..."></textarea>
        </div>
        <div id="status" class="status"></div>
        <div id="response"></div>
      </main>
    </div>
  </div>
  <script>
    const questionInput = document.getElementById('question');
    const modelInput = document.getElementById('model');
    const localInput = document.getElementById('local');
    const sendButton = document.getElementById('send');
    const clearButton = document.getElementById('clear');
    const statusNode = document.getElementById('status');
    const responseNode = document.getElementById('response');

    function setQuestion(text) {
      questionInput.value = text;
      questionInput.focus();
    }

    function renderResult(data) {
      const blocks = [];
      blocks.push(`
        <div class="result-block">
          <h3>Question</h3>
          <pre>${data.question}</pre>
        </div>
      `);
      if (data.explanation) {
        blocks.push(`
          <div class="result-block">
            <h3>Answer</h3>
            <pre>${data.explanation}</pre>
          </div>
        `);
      }
      if (data.sql) {
        blocks.push(`
          <div class="result-block">
            <h3>Executed SQL</h3>
            <pre>${data.sql}</pre>
          </div>
        `);
      }
      if (data.table_html) {
        blocks.push(`
          <div class="result-block">
            <h3>Results</h3>
            ${data.table_html}
          </div>
        `);
      }
      if (data.error) {
        blocks.push(`
          <div class="result-block error">
            <h3>Error</h3>
            <pre>${data.error}</pre>
          </div>
        `);
      }
      responseNode.innerHTML = blocks.join('');
    }

    async function submitQuestion() {
      const question = questionInput.value.trim();
      if (!question) {
        return;
      }

      sendButton.disabled = true;
      statusNode.textContent = 'Running pipeline...';

      try {
        const response = await fetch('/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question,
            model: modelInput.value,
            local: localInput.value === 'true',
          }),
        });

        const payload = await response.json();
        renderResult(payload);
        statusNode.textContent = response.ok ? 'Done.' : 'Request failed.';
      } catch (error) {
        renderResult({ error: String(error) });
        statusNode.textContent = 'Request failed.';
      } finally {
        sendButton.disabled = false;
      }
    }

    sendButton.addEventListener('click', submitQuestion);
    clearButton.addEventListener('click', () => {
      responseNode.innerHTML = '';
      statusNode.textContent = '';
      questionInput.value = '';
      questionInput.focus();
    });
    questionInput.addEventListener('keydown', (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        submitQuestion();
      }
    });
  </script>
</body>
</html>
"""


def _extract_text(obj):
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    for attr in ("content", "text", "output_text"):
        if hasattr(obj, attr):
            value = getattr(obj, attr, None)
            if value is not None:
                return str(value)
    if isinstance(obj, dict):
        for key in ("explanation", "content", "text", "output_text"):
            value = obj.get(key)
            if value is not None:
                return str(value)
    return str(obj)


def _dataset_summary() -> dict[str, str]:
    if not OUTPUT_PATH.exists():
        return {
            "row_count": "0",
            "supermarkets": "No data yet",
        }

    df = pd.read_csv(OUTPUT_PATH)
    supermarkets = ", ".join(sorted(df["supermarket"].dropna().astype(str).unique())) if "supermarket" in df else "Unknown"
    return {
        "row_count": str(len(df)),
        "supermarkets": supermarkets or "No data yet",
    }


def _render_homepage() -> bytes:
    summary = _dataset_summary()
    page = HTML_PAGE
    replacements = {
        "__ROW_COUNT__": html.escape(summary["row_count"]),
        "__SUPERMARKETS__": html.escape(summary["supermarkets"]),
        "__DEFAULT_MODEL__": html.escape(DEFAULT_MODEL),
        "__GPT4O__": html.escape(REMOTE_GPT_4o),
        "__GPTOSS__": html.escape(REMOTE_GPT_OSS_SMALL),
        "__LOCALLLAMA__": html.escape(LOCAL_LLAMA3),
    }
    for token, value in replacements.items():
        page = page.replace(token, value)
    return page.encode("utf-8")


def _json_response(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _run_question(question: str, model: str, local: bool) -> dict:
    if not Path(OUTPUT_PATH).exists():
        raise FileNotFoundError(
            f"Dataset not found at {OUTPUT_PATH}. Run `python -m src.utils.etl` first."
        )

    if local:
        model = LOCAL_LLAMA3
    elif model == LOCAL_LLAMA3:
        model = DEFAULT_MODEL

    result = asyncio.run(run_pipeline_with_details(question, model, local))
    df = result["dataframe"]
    explanation = _extract_text(result["explanation"])
    table_html = ""
    if hasattr(df, "empty"):
        if df.empty:
            table_html = "<p>No rows returned.</p>"
        else:
            table_html = df.to_html(index=False, border=0, classes="result-table")

    return {
        "question": html.escape(question),
        "explanation": html.escape(explanation),
        "sql": html.escape(result["sql"]),
        "table_html": table_html,
        "error": "",
    }


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = _render_homepage()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/health":
            body = _json_response({"status": "ok"})
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self):
        if self.path != "/ask":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
            question = str(payload.get("question", "")).strip()
            model = str(payload.get("model", DEFAULT_MODEL)).strip() or DEFAULT_MODEL
            local = bool(payload.get("local", False))

            if not question:
                raise ValueError("Question is required.")

            response = _run_question(question, model, local)
            body = _json_response(response)
            self.send_response(HTTPStatus.OK)
        except Exception as exc:
            body = _json_response(
                {
                    "question": "",
                    "explanation": "",
                    "sql": "",
                    "table_html": "",
                    "error": html.escape(f"{exc}\n\n{traceback.format_exc()}"),
                }
            )
            self.send_response(HTTPStatus.BAD_REQUEST)

        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def main():
    parser = argparse.ArgumentParser(description="Launch the supermarket query dashboard.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open a browser tab.")
    args = parser.parse_args()

    load_dotenv()
    if OUTPUT_PATH.exists():
        print(f"Using existing dataset at {OUTPUT_PATH}")
    else:
        print(f"No dataset found at {OUTPUT_PATH}")
        print("Launch will continue, but queries will fail until you run `python -m src.utils.etl`.")

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    dashboard_url = f"http://{args.host}:{args.port}"
    print(f"Dashboard ready at {dashboard_url}")

    if not args.no_browser:
        webbrowser.open(dashboard_url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
