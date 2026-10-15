# twitter-bulk-delete

Delete selected posts from your own [X](https://x.com/) account using the [X API v2](https://developer.x.com/), driven by a plain text list of tweet IDs.

指定したツイート ID だけを、自分のアカウントから X API v2 で一括削除する小さな Python スクリプトです。

## Features

- OAuth 2.0 Authorization Code + PKCE（ユーザーコンテキスト）
- 1 行 1 ID のリスト（`tweetdelete_ids.txt`）を順に削除
- `--dry-run` / `--limit` で安全に試せる
- `deleted.txt` による途中再開
- 404（既に無い投稿）は成功扱い、429 はレート制限解除まで待機
- その他のエラーは `errors.log` に記録して次へ

## Requirements

- Python 3.10+（3.9 でも動作する想定）
- [`requests`](https://pypi.org/project/requests/)
- [X Developer Portal](https://developer.x.com/) のアプリ  
  - OAuth 2.0 有効
  - App type: **Web App / Confidential**
  - App permissions: **Read and write**
  - Callback URI 例: `http://127.0.0.1:8765/callback`

## Installation

```bash
git clone https://github.com/youaoi/twitter-bulk-delete.git
cd twitter-bulk-delete
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install requests
cp .env.example .env
```

`.env` に Portal で発行した値を記入します。

```env
X_CLIENT_ID=your_client_id
X_CLIENT_SECRET=your_client_secret
X_REDIRECT_URI=http://127.0.0.1:8765/callback
```

## X Developer Portal setup

1. [Developer Portal](https://developer.x.com/) で Project / App を作成
2. **User authentication settings** で **OAuth 2.0** を有効化
3. App type を **Web App / Confidential** にする（Client Secret が必要）
4. Callback URI に `.env` の `X_REDIRECT_URI` と同じ URL を登録
5. 権限を **Read and write** にする
6. Client ID / Client Secret を `.env` にコピー

認可時に要求するスコープ: `tweet.read tweet.write users.read offline.access`

## Preparing `tweetdelete_ids.txt`

削除対象はリポジトリルートに自分で作成する `tweetdelete_ids.txt` に **1 行 1 ID** で置きます（`#` 始まりはコメント扱い）。このファイルには個人の投稿 ID が含まれるため、Git では追跡しません。

初めて使う場合は、ひな形をコピーしてから自分の ID を追加してください。

```bash
cp tweetdelete_ids.example.txt tweetdelete_ids.txt
```

`tweetdelete_ids.txt` は `.gitignore` 対象です。実際の ID を含むファイルをコミットしないでください。`--ids-file path` で別ファイルも指定できます。

### Asking Grok to build the ID list

[Grok](https://x.com/i/grok)（X 上の Grok / Grok Bot）に、削除候補の投稿 ID 一覧を作ってもらうときの例文です。出力は「数字の ID だけ・1 行 1 件・余計な説明なし」と明示すると `tweetdelete_ids.txt` にそのまま貼りやすいです。

#### 例 1: 期間で絞る

```text
@自分のユーザー名 の投稿のうち、2020-01-01 より前のものを調べて。
ツイート ID（snowflake）だけを 1 行に 1 件、コードブロックで出力して。
本文・URL・説明は付けないで。
```

#### 例 2: キーワードで絞る

```text
@自分のユーザー名 のタイムラインから、「販促」「当選」を含む投稿を探して。
見つかった投稿の tweet ID だけを 1 行 1 件で列挙して。
最大 200 件。前置きや番号付けは不要。
```

#### 例 3: リプライ / RT を除外

```text
@自分のユーザー名 のオリジナル投稿だけ（リプライ・公式 RT は除外）で、
2022 年以前のものを tweet ID のリストにして。
形式はプレーンテキスト、1 行 1 ID。最後に件数だけ教えて。
```

#### 例 4: 既存リストの整形

```text
次の投稿 URL / ステータス一覧から tweet ID だけ抜き出して、
重複を除き古い順に並べて。出力は 1 行 1 ID のコードブロックだけにして。

（ここに URL や Grok が返した一覧を貼る）
```

#### 例 5: 段階的に（件数が多いとき）

```text
さっき出した ID リストの続きから、次の 100 件分の tweet ID だけを同じ形式で出して。
すでに出した ID は繰り返さないで。
```

Grok の回答をファイルに保存する例:

```bash
# 回答のコードブロック部分だけを保存
pbpaste > tweetdelete_ids.txt          # macOS
# またはエディタで tweetdelete_ids.txt に貼り付け
```

> **Note:** Grok の検索・取得結果は完全ではないことがあります。削除前に必ず `--dry-run` で件数と先頭 ID を確認してください。他人の投稿 ID を入れても、自分のアカウントから削除できるのは自分の投稿だけです。

## Usage

実行前に件数を表示し、`yes` と入力したときだけ削除を開始します。

### 1. Dry run（API を呼ばない）

```bash
python delete_posts.py --dry-run
```

### 2. 少数件で試す

```bash
python delete_posts.py --limit 3
```

初回はブラウザで OAuth 認可します。トークンは `token.json` に保存され、期限切れ時は refresh します。

### 3. 本番

```bash
python delete_posts.py
```

進捗は `12/445 deleted` のように表示されます。

### Options

| Option | Description |
|--------|-------------|
| `--dry-run` | 削除予定の件数と先頭 10 ID を表示するだけ |
| `--limit N` | 未削除のうち先頭 N 件だけ処理 |
| `--ids-file PATH` | ID リストのパス（既定: `tweetdelete_ids.txt`） |

## Project layout

| Path | Description |
|------|-------------|
| `delete_posts.py` | メインスクリプト |
| `tweetdelete_ids.example.txt` | 個人 ID を含まない ID リストのひな形 |
| `tweetdelete_ids.txt` | ローカルに作成する削除対象 ID（Git 追跡対象外） |
| `.env.example` | 環境変数のひな形 |
| `token.json` | 取得トークン（gitignore） |
| `deleted.txt` | 削除済み / 404 ID（gitignore） |
| `errors.log` | API エラーログ（gitignore） |

## Safety notes

- 削除は取り消せません。必ず `--dry-run` → `--limit 3` → 本番の順で試してください。
- `.env` / `token.json` / `deleted.txt` / `errors.log` はコミットしないでください（`.gitignore` 済み）。
- Client Secret やトークンを Issue・チャットに貼らないでください。

## License

[MIT](./LICENSE)

## Contributing

Issue や Pull Request を歓迎します。大きな変更の前に、想定している振る舞いを Issue で共有してもらえると助かります。
