"""
Google Docs API を使って「新しいGoogleドキュメントを作成し、テキストを挿入する」スクリプト

【認証方式について（重要）】
最初はスプレッドシート課題と同じ「サービスアカウント」認証で作っていましたが、
個人のGoogleアカウント（Google Workspaceではない、通常のGmailアカウント）では、
サービスアカウントは自分専用のドライブ容量を持っていないため、
新しいファイルを作ろうとすると "storageQuotaExceeded"（容量オーバー）エラーになります。

そのため、このスクリプトでは「OAuth認証」という方式を使います。
これは、プログラムを実行するたびに（初回のみ）ブラウザが開き、
あなた自身のGoogleアカウントで「このアプリを許可しますか？」と聞かれるので、
許可すると、あなたの名義でドキュメントが作られる、という仕組みです。

事前準備:
1. Google Cloud Console で以下のAPIを有効化する
   - Google Docs API
2. Google Cloud Console で「OAuth同意画面」を設定し、
   自分のGoogleアカウントを「テストユーザー」として追加する
3. Google Cloud Console で「OAuthクライアントID」（種類: デスクトップアプリ）を作成し、
   ダウンロードしたJSONファイルを "client_secret.json" という名前でこのフォルダに置く
4. pip install -r requirements.txt
"""

import os

# ブラウザでのログイン許可（OAuth認証）を行うためのライブラリ
from google_auth_oauthlib.flow import InstalledAppFlow

# 一度ログインして得た認証情報を、ファイルに保存・読み込みするためのライブラリ
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Google の各種API（Docs など）を呼び出すためのライブラリ
from googleapiclient.discovery import build

# ---------------------------------------------------------------------------
# 設定（ここを自分の環境に合わせて変更する）
# ---------------------------------------------------------------------------

# OAuthクライアントの設定ファイル（Cloud Consoleでダウンロードしたもの）
CLIENT_SECRET_FILE = "client_secret.json"

# ログイン情報（アクセストークン）を保存しておくファイル
# 初回はブラウザでログインが必要だが、2回目以降はこのファイルを使って自動でログインする
TOKEN_FILE = "token.json"

# 作成するドキュメントのタイトル
DOCUMENT_TITLE = "APIで作成したテスト用ドキュメント"

# ドキュメントに挿入したいテキスト（\n は改行を表す）
DOCUMENT_TEXT = (
    "こんにちは。\n"
    "このドキュメントは Python と Google Docs API を使って自動作成されました。\n"
    "2行目以降もこのようにまとめて書き込めます。\n"
)

# このプログラムがGoogleに対して「何をしたいか」を宣言するもの（スコープ＝権限の範囲）
# documents権限だけで「作成」も「編集」もできる（自分名義で作るので共有の権限は不要）
SCOPES = ["https://www.googleapis.com/auth/documents"]


# ---------------------------------------------------------------------------
# 処理の本体
# ---------------------------------------------------------------------------

def get_credentials():
    """OAuth認証を行い、Docs APIを呼び出すための認証情報を取得する"""
    creds = None

    # 以前ログイン済みで、token.json が残っていればそれを読み込む
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # 有効な認証情報がない場合（初回、または期限切れの場合）
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # 期限切れだが refresh_token があれば、再ログインなしで更新できる
            creds.refresh(Request())
        else:
            # 初回はブラウザを開いてログイン・許可を行ってもらう
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # 次回から使えるように、認証情報をファイルに保存しておく
        with open(TOKEN_FILE, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return creds


def create_document(docs_service, title: str) -> str:
    """空のGoogleドキュメントを新規作成し、そのドキュメントID（識別番号）を返す"""
    # body に {"title": タイトル} を渡すと、そのタイトルで新規作成される
    document = docs_service.documents().create(body={"title": title}).execute()

    # 作成結果の中から documentId（URLに含まれる長い文字列）を取り出す
    return document["documentId"]


def insert_text(docs_service, document_id: str, text: str):
    """指定したドキュメントの先頭にテキストを挿入する"""
    # Docs API は「どこに何をするか」を requests というリストで指定する
    requests = [
        {
            "insertText": {
                # index: 1 は「本文のいちばん先頭」を意味する
                # （index 0 は本文の開始位置そのものなので指定できない）
                "location": {"index": 1},
                "text": text,
            }
        }
    ]

    # batchUpdate で、上で作った編集命令をまとめて実行する
    docs_service.documents().batchUpdate(
        documentId=document_id,
        body={"requests": requests},
    ).execute()


def main():
    # 1. OAuth認証を行い、Docsを操作する準備をする（初回はブラウザが開く）
    creds = get_credentials()
    docs_service = build("docs", "v1", credentials=creds)

    # 2. 空のドキュメントを新規作成する（自分のアカウント名義で作られる）
    document_id = create_document(docs_service, DOCUMENT_TITLE)
    print(f"ドキュメントを作成しました（ID: {document_id}）")

    # 3. 作成したドキュメントにテキストを挿入する
    insert_text(docs_service, document_id, DOCUMENT_TEXT)
    print("テキストを挿入しました。")

    # 4. ブラウザで開くためのURLを表示する
    print(f"URL: https://docs.google.com/document/d/{document_id}/edit")


# このファイルを直接実行したときだけ main() を動かす、という決まり文句
if __name__ == "__main__":
    main()
