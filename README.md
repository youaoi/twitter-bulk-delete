# twitter-bulk-delete

<p align="center">
  <img src="assets/own-post-cleanup.png" alt="own-post-cleanup の登録用アイコン" width="128">
</p>

自分の X アカウントのポストを扱うローカルツールです。ここでは [X Developer Console](https://console.x.com/) でアプリと資格情報を作り、このリポジトリを手元で起動するところまでを説明します。

削除したいポストの持ち主である X アカウントで Console にサインインしてください。パスワードや鍵はチャットや Git に貼りません。鍵は手元の `.env` だけに置きます。

## 用意するもの

- その X アカウント
- Python 3.11 以降

公式の流れは [Getting Access](https://docs.x.com/x-api/getting-started/getting-access) と [Developer Console](https://docs.x.com/fundamentals/developer-portal) にあります。

## 1. 開発者アカウントを作る

1. [https://console.x.com/](https://console.x.com/) を開き、対象の X アカウントでサインインします。
2. 初めての場合は [https://console.x.com/onboarding](https://console.x.com/onboarding) で開発者登録に進みます。
3. [Developer Agreement and Policy](https://developer.x.com/en/developer-terms/agreement-and-policy) と [Developer Policy](https://developer.x.com/en/developer-terms/policy) を確認して同意します。
4. API の使い方を聞かれたら、次の趣旨を入力します。

   > A personal, local tool that reads and deletes posts on my own X account.

登録が終わると、ブラウザのアドレスが `https://console.x.com/accounts/<アカウントID>/...` になります。`<アカウントID>` はこのあとクレジット画面を開くときに使います。

## 2. アプリを作る

1. [https://console.x.com/apps](https://console.x.com/apps) を開きます。左の **Apps** からでも同じ一覧に入れます。
2. **Pay Per Use** を選び、**Create App**（表示が **Create New Client Application** の場合はそのボタン）を押します。
3. 次のとおり入力して作成します。

   | 項目 | 入力する値 |
   | --- | --- |
   | App name | `own-post-cleanup` |
   | Environment | `Production` |
   | Description / use case | `Delete posts on my own account from a local app.` |

   App name は `own-post-cleanup` にしてください。Console は、`twitter` という綴りに加えて、キリル文字・ギリシャ文字・アクセント付きラテン文字への置き換えや、数字への置き換え（`tw1tter` など）もアプリ名として拒否します。

4. アイコンのアップロード欄がある場合は、この PNG を指定します。一辺 1024px の正方形です。

   <img src="assets/own-post-cleanup.png" alt="own-post-cleanup の登録用アイコン" width="192">

   元の SVG は [assets/own-post-cleanup.svg](assets/own-post-cleanup.svg)、アップロード用 PNG は [assets/own-post-cleanup.png](assets/own-post-cleanup.png) です。

5. 作成直後のダイアログに、一度だけ **Consumer Key**、**Secret Key**、**Bearer Token** が出ます。Consumer Key と Secret Key をパスワードマネージャに控えます。Bearer Token はこのツールでは使いません。

ダイアログを閉じたあとでも、アプリの **Keys and tokens** から Consumer Key は再表示できます。Secret を控え損ねた場合は、その場の **Regenerate** で作り直します。作り直すと以前の Secret は無効になります。

アプリの設定項目自体は [Apps](https://docs.x.com/fundamentals/developer-apps) にまとまっています。

## 3. ユーザー認証を Read and write にする

ポストの削除には、アプリ所有者のユーザー権限が必要です。作成直後の権限は読み取りだけなので、ここで書き込みに変えます。

1. [https://console.x.com/apps](https://console.x.com/apps) で今作ったアプリを開きます。
2. **Keys and tokens** を開きます。
3. 下の方にある **User authentication settings** の **Set up** を押します。
4. 次のとおり選びます。

   | 項目 | 選ぶ値 |
   | --- | --- |
   | App permissions | **Read and write** |
   | Type of App | **Web App, Automated App or Bot** |
   | Callback URI / Redirect URL | `http://127.0.0.1:8787/callback` |
   | Website URL | `https://github.com/youaoi/twitter-bulk-delete` |

5. **Save** します。

Callback URI はプロトコル、ホスト、ポート、パスまで完全一致です。`localhost` や末尾の `/` は別 URL として扱われます。ローカル開発のコールバックは `127.0.0.1` を使います。根拠は [Apps の Callback URLs](https://docs.x.com/fundamentals/developer-apps) です。

OAuth 2.0 のスコープを個別に選ぶ画面が出た場合は、次の 4 つを有効にします。

- `tweet.read`
- `tweet.write`
- `users.read`
- `offline.access`

DM 用の権限と `dm.read` / `dm.write` は付けません。スコープの意味は [OAuth 2.0 Authorization Code Flow with PKCE](https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code) にあります。

保存直後に **Client ID** と **Client Secret** が一度だけ表示されます。両方控えます。Client Secret を閉じたあとに再表示できない場合は、**Keys and tokens** の OAuth 2.0 Client Secret を **Regenerate** します。

## 4. 自分のアカウント用 Access Token を発行する

User authentication settings を保存したあとで発行します。それより前の Access Token は Read only のままです。

1. 同じアプリの **Keys and tokens** を開きます。
2. **Access Token and Secret** の **Generate**（既にある場合は **Regenerate**）を押します。
3. 権限が **Read and write** になっていることを確認してから、**Access Token** と **Access Token Secret** を控えます。

削除 API がこのユーザートークンを要求する理由は [Manage Posts の quickstart](https://docs.x.com/x-api/posts/manage-tweets/quickstart) と [Delete Post](https://docs.x.com/x-api/posts/delete-post) にあります。

## 5. クレジットを確認する

X API は従量課金です。サインイン後のクレジット残高は次の URL です。`<アカウントID>` はアドレスバーに出ている値に置き換えます。

- 残高と購入: `https://console.x.com/accounts/<アカウントID>/billing/credits`
- 支払い方法: `https://console.x.com/accounts/<アカウントID>/billing/info`
- 利用量: `https://console.x.com/accounts/<アカウントID>/usage`

公開の料金説明は [Pricing](https://docs.x.com/x-api/getting-started/pricing) と [developer.x.com の料金](https://developer.x.com/#pricing) です。いまの単価 JSON は [https://console.x.com/api/credits/pricing](https://console.x.com/api/credits/pricing) です。

自分のポストを読んで消すときに関係する単価は、2026-10-13 時点で次のとおりです。

| 操作 | 単価 |
| --- | --- |
| 自分のポストの読み取り（Owned Reads） | 1 件あたり $0.001 |
| ポストの削除（Interaction: Delete） | 1 リクエストあたり $0.010 |

初回の支払いカード登録とオートチャージで付くクレジットの条件は [Free credits](https://docs.x.com/x-api/getting-started/free-credits) にあります。

## 6. `.env` に書いて起動する

コンソールの表示名と、このリポジトリが読む変数の対応です。

| Console の表示 | `.env` の変数 |
| --- | --- |
| API Key / Consumer Key | `X_API_KEY` |
| API Key Secret / Secret Key | `X_API_SECRET` |
| Access Token | `X_ACCESS_TOKEN` |
| Access Token Secret | `X_ACCESS_TOKEN_SECRET` |
| OAuth 2.0 Client ID | `X_CLIENT_ID` |
| OAuth 2.0 Client Secret | `X_CLIENT_SECRET` |

```bash
git clone https://github.com/youaoi/twitter-bulk-delete.git
cd twitter-bulk-delete
cp .env.example .env
```

`.env` を開き、上の 6 つを貼ります。引用符は不要です。空欄が 1 つでもあると起動しません。

```bash
python3 app.py
```

次の行が出たら起動できています。

```text
http://127.0.0.1:8787/ で起動しました。
```

ブラウザで [http://127.0.0.1:8787/](http://127.0.0.1:8787/) を開きます。6 つの資格情報を読み込んだ旨が表示され、値そのものは出ません。止めるときはそのターミナルで Ctrl+C です。

足りない変数があるときは、不足している名前を出して終了します。表示された名前だけを [https://console.x.com/apps](https://console.x.com/apps) の **Keys and tokens** から取り直してください。

## 起動時に止まりやすいところ

- **Callback URL not approved** と出る場合は、Console の Callback URI を `http://127.0.0.1:8787/callback` に合わせます。
- 削除や書き込みが拒否される場合は、**User authentication settings** が **Read and write** になったあとで Access Token を発行し直します。
- 資格情報を作り直したあとは、`.env` の該当行を新しい値に置き換えてから `python3 app.py` をやり直します。
- 残高が足りないと API 呼び出しは拒否されます。`https://console.x.com/accounts/<アカウントID>/billing/credits` でクレジットを足します。
