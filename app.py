from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import datetime

app = Flask(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ITEMS_FILE = os.path.join(SCRIPT_DIR, "items.json")
VERSIONS_FILE = os.path.join(SCRIPT_DIR, "versions.json")

def load_json(filepath):
    """JSONファイルを読み込み、存在しない場合は空リストを返す。"""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_json(filepath, data):
    """JSONファイルに保存する。"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_next_id(data_list):
    """リスト内の最大idから+1した値を返す。空リストの場合は1を返す。"""
    if not data_list:
        return 1
    return max(item["id"] for item in data_list) + 1

@app.route("/")
def index():
    """トップページ: メニューを表示。"""
    return render_template("index.html")

# ------------------------------
# アイテム管理
# ------------------------------
@app.route("/items")
def list_items():
    """アイテム一覧表示。"""
    items = load_json(ITEMS_FILE)
    return render_template("items.html", items=items)

@app.route("/items/create", methods=["POST"])
def create_item():
    """アイテム新規作成。"""
    name = request.form.get("name")
    category = request.form.get("category")
    items = load_json(ITEMS_FILE)

    new_id = get_next_id(items)
    new_item = {
        "id": new_id,
        "name": name,
        "category": category
    }
    items.append(new_item)
    save_json(ITEMS_FILE, items)

    return redirect(url_for("list_items"))

# ------------------------------
# バージョン管理
# ------------------------------
@app.route("/versions")
def list_versions():
    """バージョン一覧表示。"""
    versions = load_json(VERSIONS_FILE)
    return render_template("versions.html", versions=versions)

@app.route("/versions/create", methods=["POST"])
def create_version():
    """バージョン新規作成。"""
    version_name = request.form.get("versionName")
    versions = load_json(VERSIONS_FILE)

    new_id = get_next_id(versions)
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    new_version = {
        "id": new_id,
        "versionName": version_name,
        "createdAt": now,
        "items": []
    }
    versions.append(new_version)
    save_json(VERSIONS_FILE, versions)

    return redirect(url_for("list_versions"))

@app.route("/version/<int:version_id>")
def show_version(version_id):
    """バージョン詳細画面。含まれるアイテムも表示。"""
    versions = load_json(VERSIONS_FILE)
    items = load_json(ITEMS_FILE)

    version = next((v for v in versions if v["id"] == version_id), None)
    if version is None:
        return f"Version ID {version_id} not found.", 404

    # バージョンに含まれるアイテムオブジェクトのリストを作る
    version_items = []
    for item_id in version["items"]:
        it = next((i for i in items if i["id"] == item_id), None)
        if it:
            version_items.append(it)

    return render_template("version_detail.html", version=version, items=version_items)

@app.route("/version/<int:version_id>/add_item", methods=["POST"])
def add_item_to_version(version_id):
    """指定したバージョンにアイテムを追加。"""
    item_id = int(request.form.get("item_id"))
    versions = load_json(VERSIONS_FILE)
    version = next((v for v in versions if v["id"] == version_id), None)
    if version is None:
        return f"Version ID {version_id} not found.", 404

    # 既に含まれていない場合だけ追加
    if item_id not in version["items"]:
        version["items"].append(item_id)

    save_json(VERSIONS_FILE, versions)
    return redirect(url_for("show_version", version_id=version_id))

if __name__ == "__main__":
    # Flaskアプリを起動
    # デバッグモードで起動するなら: app.run(debug=True)
    app.run(debug=True)
