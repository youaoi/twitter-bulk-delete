#!/usr/bin/env python3
"""Load credentials from the X Developer Console and serve a local startup page."""

from __future__ import annotations

import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8787
ENV_PATH = Path(__file__).resolve().parent / ".env"

REQUIRED = (
    ("X_API_KEY", "API Key（Consumer Key）"),
    ("X_API_SECRET", "API Key Secret（Secret Key）"),
    ("X_ACCESS_TOKEN", "Access Token"),
    ("X_ACCESS_TOKEN_SECRET", "Access Token Secret"),
    ("X_CLIENT_ID", "OAuth 2.0 Client ID"),
    ("X_CLIENT_SECRET", "OAuth 2.0 Client Secret"),
)


def load_env(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def missing_keys() -> list[tuple[str, str]]:
    missing = []
    for key, label in REQUIRED:
        if not os.environ.get(key, "").strip():
            missing.append((key, label))
    return missing


def html_page() -> str:
    rows = "\n".join(
        f"<li><code>{key}</code>（{label}）を読み込みました。</li>"
        for key, label in REQUIRED
    )
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>twitter-bulk-delete</title>
  <style>
    body {{ font-family: sans-serif; max-width: 40rem; margin: 3rem auto; line-height: 1.6; }}
    code {{ font-family: ui-monospace, monospace; }}
  </style>
</head>
<body>
  <h1>twitter-bulk-delete が起動しました</h1>
  <p>127.0.0.1:{PORT} で資格情報を読み込んでいます。値そのものはこの画面に出していません。</p>
  <ul>
    {rows}
  </ul>
  <p>コールバック URL は <code>http://127.0.0.1:{PORT}/callback</code> です。</p>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path not in ("/", "/callback"):
            self.send_error(404)
            return
        body = html_page().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main() -> int:
    load_env(ENV_PATH)
    missing = missing_keys()
    if missing:
        print(".env に次の値がありません。README の手順で https://console.x.com/ からコピーしてください。", file=sys.stderr)
        for key, label in missing:
            print(f"  {key}  … {label}", file=sys.stderr)
        return 1

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"http://{HOST}:{PORT}/ で起動しました。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止しました。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
