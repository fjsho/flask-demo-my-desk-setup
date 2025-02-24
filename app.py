from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import datetime

app = Flask(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ITEMS_FILE = os.path.join(SCRIPT_DIR, "items.json")
VERSIONS_FILE = os.path.join(SCRIPT_DIR, "versions.json")

def load_json(filepath):
    """JSONファイルを読み込み、存在しない/破損している場合は空リストを返す。"""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_json(filepath, data):
    """JSONファイルに保存する。"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_next_id(data_list):
    """リスト中の最大idに+1した値を返す。空なら1を返す。"""
    if not data_list:
        return 1
    return max(item["id"] for item in data_list) + 1

# --------------------------------------------------
# トップ画面(ホーム)
# --------------------------------------------------
@app.route("/")
def index():
    """
    トップ画面:
     - バージョン一覧(デスク環境の履歴)を表示
     - 新規登録画面への導線
     - アイテム一覧画面への導線
    """
    versions = load_json(VERSIONS_FILE)
    # 最新が上に来るよう、createdAt 降順でソート (任意)
    versions_sorted = sorted(versions, key=lambda v: v["createdAt"], reverse=True)
    return render_template("index.html", versions=versions_sorted)

# --------------------------------------------------
# デスク環境(バージョン) 新規登録
# --------------------------------------------------
@app.route("/version/new", methods=["GET", "POST"])
def create_version():
    """
    新規バージョン登録画面:
      - GET: フォームを表示
      - POST: フォーム送信を受け取り、versions.jsonに保存
    """
    if request.method == "POST":
        version_name = request.form.get("versionName")
        # 作成日時は自動付与
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        versions = load_json(VERSIONS_FILE)
        new_id = get_next_id(versions)

        new_version = {
            "id": new_id,
            "versionName": version_name,
            "createdAt": now,
            "items": []  # 登録時点ではまだアイテムを持たない想定
        }

        versions.append(new_version)
        save_json(VERSIONS_FILE, versions)
        # 登録後はトップ画面or詳細画面に飛ばす
        return redirect(url_for("show_version", version_id=new_id))

    # GET: フォームを表示
    return render_template("version_new.html")

# --------------------------------------------------
# バージョン詳細画面
# --------------------------------------------------
@app.route("/version/<int:version_id>")
def show_version(version_id):
    """
    バージョン詳細:
      - バージョン名、作成日時、紐づくアイテム一覧を表示
      - アイテム追加フォームあり
    """
    versions = load_json(VERSIONS_FILE)
    items_all = load_json(ITEMS_FILE)

    version = next((v for v in versions if v["id"] == version_id), None)
    if version is None:
        return f"Version ID {version_id} not found.", 404

    # バージョンに含まれるアイテムを抽出
    version_items = [i for i in items_all if i["id"] in version["items"]]

    return render_template("version_detail.html",
                           version=version,
                           version_items=version_items,
                           all_items=items_all)

@app.route("/version/<int:version_id>/add_item", methods=["POST"])
def add_item_to_version(version_id):
    """
    バージョンにアイテムをアタッチする。
    (既存アイテムのIDを選択してPOSTする形)
    """
    item_id = int(request.form.get("item_id", 0))
    versions = load_json(VERSIONS_FILE)
    items_all = load_json(ITEMS_FILE)

    version = next((v for v in versions if v["id"] == version_id), None)
    if version is None:
        return f"Version ID {version_id} not found.", 404

    # 該当アイテムが存在するかチェック
    item = next((i for i in items_all if i["id"] == item_id), None)
    if item is None:
        return f"Item ID {item_id} not found.", 404

    # すでに含まれていなければ追加
    if item_id not in version["items"]:
        version["items"].append(item_id)
        save_json(VERSIONS_FILE, versions)

    return redirect(url_for("show_version", version_id=version_id))

@app.route("/version/<int:version_id>/remove_item", methods=["POST"])
def remove_item_from_version(version_id):
    """
    バージョンからアイテムをデタッチする。
    """
    item_id = int(request.form.get("item_id", 0))
    versions = load_json(VERSIONS_FILE)

    version = next((v for v in versions if v["id"] == version_id), None)
    if version is None:
        return f"Version ID {version_id} not found.", 404

    if item_id in version["items"]:
        version["items"].remove(item_id)
        save_json(VERSIONS_FILE, versions)

    return redirect(url_for("show_version", version_id=version_id))

# --------------------------------------------------
# アイテム一覧 (＋新規作成)
# --------------------------------------------------
@app.route("/items", methods=["GET", "POST"])
def items():
    """
    GET: アイテム一覧を表示
    POST: 新規アイテムを登録
    """
    if request.method == "POST":
        name = request.form.get("name")
        category = request.form.get("category")
        items_list = load_json(ITEMS_FILE)
        new_id = get_next_id(items_list)
        new_item = {
            "id": new_id,
            "name": name,
            "category": category
        }
        items_list.append(new_item)
        save_json(ITEMS_FILE, items_list)
        return redirect(url_for("items"))

    # GET: 一覧表示
    items_list = load_json(ITEMS_FILE)
    return render_template("items.html", items=items_list)

# --------------------------------------------------
# Flask起動
# --------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
