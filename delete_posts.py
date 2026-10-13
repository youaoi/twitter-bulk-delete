#!/usr/bin/env python3
"""Delete selected X (Twitter) posts via API v2 with OAuth 2.0 PKCE."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests

IDS_FILE = Path("tweetdelete_ids.txt")
TOKEN_FILE = Path("token.json")
DELETED_FILE = Path("deleted.txt")
ERRORS_FILE = Path("errors.log")
AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
DELETE_URL = "https://api.x.com/2/tweets/{id}"
SCOPES = "tweet.read tweet.write users.read offline.access"


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def basic_auth_header(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    code: str | None = None
    error: str | None = None
    event: threading.Event | None = None

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != urllib.parse.urlparse(self.server.redirect_uri).path:  # type: ignore[attr-defined]
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        params = urllib.parse.parse_qs(parsed.query)
        if "error" in params:
            OAuthCallbackHandler.error = params["error"][0]
            body = b"Authorization failed. You can close this window."
        else:
            OAuthCallbackHandler.code = params.get("code", [None])[0]
            body = b"Authorization successful. You can close this window."

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)
        if OAuthCallbackHandler.event:
            OAuthCallbackHandler.event.set()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def exchange_code(
    code: str,
    verifier: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
        "client_id": client_id,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": basic_auth_header(client_id, client_secret),
    }
    resp = requests.post(TOKEN_URL, data=data, headers=headers, timeout=60)
    if not resp.ok:
        raise SystemExit(f"Token exchange failed ({resp.status_code}): {resp.text}")
    token = resp.json()
    token["obtained_at"] = int(time.time())
    return token


def refresh_access_token(token: dict, client_id: str, client_secret: str) -> dict:
    refresh = token.get("refresh_token")
    if not refresh:
        raise SystemExit("No refresh_token available; please re-authorize.")
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh,
        "client_id": client_id,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": basic_auth_header(client_id, client_secret),
    }
    resp = requests.post(TOKEN_URL, data=data, headers=headers, timeout=60)
    if not resp.ok:
        raise SystemExit(f"Token refresh failed ({resp.status_code}): {resp.text}")
    new_token = resp.json()
    if "refresh_token" not in new_token and refresh:
        new_token["refresh_token"] = refresh
    new_token["obtained_at"] = int(time.time())
    return new_token


def save_token(token: dict) -> None:
    TOKEN_FILE.write_text(json.dumps(token, indent=2) + "\n", encoding="utf-8")


def load_token() -> dict | None:
    if not TOKEN_FILE.exists():
        return None
    return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))


def token_expired(token: dict, skew_seconds: int = 60) -> bool:
    obtained = int(token.get("obtained_at", 0))
    expires_in = int(token.get("expires_in", 0))
    if not obtained or not expires_in:
        return True
    return time.time() >= (obtained + expires_in - skew_seconds)


def authorize(client_id: str, client_secret: str, redirect_uri: str) -> dict:
    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(24)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = AUTH_URL + "?" + urllib.parse.urlencode(params)

    parsed = urllib.parse.urlparse(redirect_uri)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80

    OAuthCallbackHandler.code = None
    OAuthCallbackHandler.error = None
    OAuthCallbackHandler.event = threading.Event()

    server = HTTPServer((host, port), OAuthCallbackHandler)
    server.redirect_uri = redirect_uri  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    print("Opening browser for X authorization...")
    print(f"If it does not open, visit:\n{url}\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    if not OAuthCallbackHandler.event.wait(timeout=300):
        server.server_close()
        raise SystemExit("Timed out waiting for OAuth callback.")
    server.server_close()

    if OAuthCallbackHandler.error:
        raise SystemExit(f"OAuth error: {OAuthCallbackHandler.error}")
    if not OAuthCallbackHandler.code:
        raise SystemExit("OAuth callback did not include an authorization code.")

    token = exchange_code(
        OAuthCallbackHandler.code,
        verifier,
        client_id,
        client_secret,
        redirect_uri,
    )
    save_token(token)
    return token


def get_access_token(client_id: str, client_secret: str, redirect_uri: str) -> str:
    token = load_token()
    if token is None:
        token = authorize(client_id, client_secret, redirect_uri)
    elif token_expired(token):
        token = refresh_access_token(token, client_id, client_secret)
        save_token(token)
    access = token.get("access_token")
    if not access:
        raise SystemExit("token.json is missing access_token; please re-authorize.")
    return access


def load_ids(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"ID list not found: {path}")
    ids: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            ids.append(line)
    return ids


def load_deleted(path: Path = DELETED_FILE) -> set[str]:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def append_line(path: Path, value: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(value + "\n")


def log_error(tweet_id: str, status: int, body: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    append_line(ERRORS_FILE, f"{stamp}\t{tweet_id}\t{status}\t{body.replace(chr(10), ' ')}")


def wait_for_rate_limit(resp: requests.Response) -> None:
    reset = resp.headers.get("x-rate-limit-reset")
    now = int(time.time())
    if reset and reset.isdigit():
        sleep_for = max(int(reset) - now, 1) + 1
    else:
        sleep_for = 60
    print(f"Rate limited (429). Waiting {sleep_for}s until reset...")
    time.sleep(sleep_for)


def delete_tweet(tweet_id: str, access_token: str) -> tuple[str, str | None]:
    """Return (outcome, access_token). outcome is 'deleted', 'missing', or 'error'."""
    url = DELETE_URL.format(id=tweet_id)
    headers = {"Authorization": f"Bearer {access_token}"}
    while True:
        resp = requests.delete(url, headers=headers, timeout=60)
        if resp.status_code == 429:
            wait_for_rate_limit(resp)
            continue
        if resp.status_code in (200, 201):
            return "deleted", access_token
        if resp.status_code == 404:
            return "missing", access_token
        log_error(tweet_id, resp.status_code, resp.text)
        return "error", access_token


def confirm_or_exit(count: int) -> None:
    print(f"About to process {count} tweet(s). Type 'yes' to continue:")
    answer = input("> ").strip()
    if answer != "yes":
        raise SystemExit("Aborted.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete tweets listed in tweetdelete_ids.txt via X API v2."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned deletions without calling the API.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only the first N pending IDs.",
    )
    parser.add_argument(
        "--ids-file",
        type=Path,
        default=IDS_FILE,
        help="Path to newline-separated tweet IDs (default: tweetdelete_ids.txt).",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()

    all_ids = load_ids(args.ids_file)
    already = load_deleted()
    pending = [tid for tid in all_ids if tid not in already]

    if args.limit is not None:
        if args.limit < 0:
            raise SystemExit("--limit must be >= 0")
        pending = pending[: args.limit]

    total_pending = len(pending)
    print(f"Total IDs in list: {len(all_ids)}")
    print(f"Already recorded in {DELETED_FILE}: {len(already)}")
    print(f"Pending this run: {total_pending}")

    if args.dry_run:
        print("Dry run — no API calls will be made.")
        print(f"Would delete {total_pending} tweet(s). First 10:")
        for tid in pending[:10]:
            print(f"  {tid}")
        return 0

    if total_pending == 0:
        print("Nothing to delete.")
        return 0

    confirm_or_exit(total_pending)

    client_id = require_env("X_CLIENT_ID")
    client_secret = require_env("X_CLIENT_SECRET")
    redirect_uri = require_env("X_REDIRECT_URI")
    access_token = get_access_token(client_id, client_secret, redirect_uri)

    recorded = len(already)
    total_ids = len(all_ids)
    run_ok = 0
    for tweet_id in pending:
        outcome, access_token = delete_tweet(tweet_id, access_token)
        if outcome in ("deleted", "missing"):
            append_line(DELETED_FILE, tweet_id)
            recorded += 1
            run_ok += 1
            print(f"{recorded}/{total_ids} deleted")
        else:
            print(f"{recorded}/{total_ids} deleted  (error on {tweet_id}, see {ERRORS_FILE})")

        # Refresh token opportunistically if near expiry between calls.
        token = load_token()
        if token and token_expired(token):
            token = refresh_access_token(token, client_id, client_secret)
            save_token(token)
            access_token = token["access_token"]

    print(f"Done. {run_ok}/{total_pending} succeeded this run; {recorded}/{total_ids} in {DELETED_FILE}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
