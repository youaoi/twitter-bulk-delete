# twitter-bulk-delete

自分の X アカウント（@youaoi0819）の投稿のうち、`tweetdelete_ids.txt` に列挙した ID だけを [X API v2](https://developer.x.com/) で削除するスクリプトです。

## 必要なもの

- Python 3
- `requests`（`pip install requests`）
- X Developer Portal のアプリ（OAuth 2.0、Confidential / Web App）

## X Developer Portal での設定

1. [Developer Portal](https://developer.x.com/) で Project / App を作成する
2. **User authentication settings** で **OAuth 2.0** を有効化する
3. App type は **Web App / Confidential** を選ぶ（Client Secret が必要）
4. **Callback URI / Redirect URL** に例えば `http://127.0.0.1:8765/callback` を登録する
5. アプリの権限を **Read and write** にする
6. Client ID / Client Secret を控える

## セットアップ

```bash
cp .env.example .env
# .env に X_CLIENT_ID / X_CLIENT_SECRET / X_REDIRECT_URI を記入

pip install requests
```

`tweetdelete_ids.txt` は 1 行 1 ID（リポジトリ同梱）。削除済み ID は `deleted.txt` に追記され、再実行時はスキップされます。

## 実行手順（推奨）

### 1. dry-run（API は呼ばない）

```bash
python delete_posts.py --dry-run
```

削除予定件数と先頭 10 件の ID を表示します。

### 2. 少数件で試す

```bash
python delete_posts.py --limit 3
```

初回はブラウザで認可（スコープ: `tweet.read tweet.write users.read offline.access`）。トークンは `token.json` に保存され、期限切れ時は refresh します。実行前に件数を出し、`yes` と入力すると開始します。

### 3. 本番（全件）

```bash
python delete_posts.py
```

進捗は `12/445 deleted` のように表示されます。404（既に無い投稿）は成功扱いです。429 のときは `x-rate-limit-reset` まで待って再試行します。その他のエラーは `errors.log` に記録して次の ID へ進みます。

## ファイル

| ファイル | 説明 |
|----------|------|
| `delete_posts.py` | 削除スクリプト |
| `tweetdelete_ids.txt` | 削除対象 ID（1 行 1 ID） |
| `.env.example` | 環境変数のひな形 |
| `token.json` | 取得トークン（gitignore） |
| `deleted.txt` | 削除済み / 404 ID（gitignore） |
| `errors.log` | API エラーログ（gitignore） |
