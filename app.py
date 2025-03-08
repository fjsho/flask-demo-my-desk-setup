from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import datetime

app = Flask(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ITEMS_FILE = os.path.join(SCRIPT_DIR, "items.json")
VERSIONS_FILE = os.path.join(SCRIPT_DIR, "versions.json")


# ---------------------
# ユーティリティ
# ---------------------
def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_next_id(data_list):
    if not data_list:
        return 1
    return max(item["id"] for item in data_list) + 1

def parse_date(date_str):
    """
    'yyyy-mm-dd' 形式の文字列を datetime.date に変換。
    不正値や空文字の場合は None を返す簡易実装。
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

# ---------------------
# トップ画面
# ---------------------
@app.route("/")
def index():
    """トップ画面: バージョン一覧、ボタン類を表示"""
    versions = load_json(VERSIONS_FILE)

    # ソート: startPeriod(日付)が早い順 → endPeriod(日付)が早い順
    # データは文字列だが、正しくソートするには date にパースして比較する
    def version_sort_key(v):
        # parse_date で None になる可能性があるので、ソート用に補完
        sp = parse_date(v.get("startPeriod", "")) or datetime.min.date()
        ep = parse_date(v.get("endPeriod", "")) or datetime.min.date()
        return (sp, ep)

    versions_sorted = sorted(versions, key=version_sort_key)

    return render_template("index.html", versions=versions_sorted)

# ---------------------
# デスク環境バージョン 新規登録
# ---------------------
@app.route("/version/new", methods=["GET", "POST"])
def create_version():
    versions = load_json(VERSIONS_FILE)
    items = load_json(ITEMS_FILE)

    # 直前のデスク環境を取得 (最後に登録されたversion)
    last_version = versions[-1] if versions else None

    if request.method == "POST":
        version_name = request.form.get("versionName")
        start_period = request.form.get("startPeriod")
        end_period = request.form.get("endPeriod")

        new_id = get_next_id(versions)
        new_ver = {
            "id": new_id,
            "versionName": version_name,
            "startPeriod": start_period,
            "endPeriod": end_period,
            "items": []
        }

        # 既存アイテムのアタッチ
        attached_item_ids = request.form.getlist("attach_item_ids")
        for i_id in attached_item_ids:
            new_ver["items"].append(int(i_id))

        # アイテム新規登録 → 即アタッチ
        new_item_name = request.form.get("new_item_name")
        new_item_cat = request.form.get("new_item_category")
        new_item_link = request.form.get("new_item_link")
        if new_item_name:
            item_id = get_next_id(items)
            new_item = {
                "id": item_id,
                "name": new_item_name,
                "category": new_item_cat,
                "productLink": new_item_link
            }
            items.append(new_item)
            new_ver["items"].append(item_id)

        versions.append(new_ver)
        save_json(VERSIONS_FILE, versions)
        save_json(ITEMS_FILE, items)

        return redirect(url_for("show_version", version_id=new_id))

    # GETリクエスト時: フォーム表示
    return render_template("version_new.html", last_version=last_version, items=items)

# ---------------------
# デスク環境バージョン 詳細 & 更新
# ---------------------
@app.route("/version/<int:version_id>", methods=["GET"])
def show_version(version_id):
    versions = load_json(VERSIONS_FILE)
    items = load_json(ITEMS_FILE)

    version = next((v for v in versions if v["id"] == version_id), None)
    if not version:
        return "Version not found.", 404

    # このバージョンに紐づくアイテム
    attached_items = [i for i in items if i["id"] in version["items"]]

    return render_template("version_detail.html",
                           version=version,
                           attached_items=attached_items,
                           all_items=items)

@app.route("/version/<int:version_id>/update", methods=["POST"])
def update_version_info(version_id):
    """バージョン名, startPeriod, endPeriod の更新 (yyyy-mm-dd形式)"""
    versions = load_json(VERSIONS_FILE)
    version = next((v for v in versions if v["id"] == version_id), None)
    if not version:
        return "Version not found.", 404

    version["versionName"] = request.form.get("versionName")
    version["startPeriod"] = request.form.get("startPeriod")
    version["endPeriod"] = request.form.get("endPeriod")

    save_json(VERSIONS_FILE, versions)
    return redirect(url_for("show_version", version_id=version_id))

@app.route("/version/<int:version_id>/add_item", methods=["POST"])
def add_item_to_version(version_id):
    """既存アイテム or 新規アイテムをバージョンにアタッチ"""
    versions = load_json(VERSIONS_FILE)
    items = load_json(ITEMS_FILE)
    version = next((v for v in versions if v["id"] == version_id), None)

    if not version:
        return "Version not found.", 404

    # 既存アイテムID
    existing_item_id = request.form.get("existing_item_id")
    if existing_item_id:
        i_id = int(existing_item_id)
        if i_id not in version["items"]:
            version["items"].append(i_id)

    # 新規アイテム
    new_item_name = request.form.get("new_item_name")
    if new_item_name:
        new_item_cat = request.form.get("new_item_category")
        new_item_link = request.form.get("new_item_link")
        new_id = get_next_id(items)
        new_item = {
            "id": new_id,
            "name": new_item_name,
            "category": new_item_cat,
            "productLink": new_item_link
        }
        items.append(new_item)
        version["items"].append(new_id)

    save_json(VERSIONS_FILE, versions)
    save_json(ITEMS_FILE, items)

    return redirect(url_for("show_version", version_id=version_id))

@app.route("/version/<int:version_id>/remove_item", methods=["POST"])
def remove_item_from_version(version_id):
    """バージョンからアイテムをデタッチ"""
    versions = load_json(VERSIONS_FILE)
    version = next((v for v in versions if v["id"] == version_id), None)
    if not version:
        return "Version not found.", 404

    item_id = int(request.form.get("item_id"))
    if item_id in version["items"]:
        version["items"].remove(item_id)

        save_json(VERSIONS_FILE, versions)
        save_json(VERSIONS_FILE, versions)

    save_json(VERSIONS_FILE, versions)

    return redirect(url_for("show_version", version_id=version_id))

# ---------------------
# アイテム一覧 (CRUD)
# ---------------------
@app.route("/items", methods=["GET", "POST"])
def items_list():
    """GET: 一覧表示, POST: 新規アイテム作成"""
    if request.method == "POST":
        # 新規アイテム
        name = request.form.get("name")
        category = request.form.get("category")
        link = request.form.get("productLink")

        items_data = load_json(ITEMS_FILE)
        new_id = get_next_id(items_data)
        new_item = {
            "id": new_id,
            "name": name,
            "category": category,
            "productLink": link
        }
        items_data.append(new_item)
        save_json(ITEMS_FILE, items_data)
        return redirect(url_for("items_list"))

    # GET: 一覧表示
    items_data = load_json(ITEMS_FILE)
    versions = load_json(VERSIONS_FILE)

    # アイテムごとに使用されているバージョンを収集
    def find_versions_for_item(item_id):
        used_in = []
        for v in versions:
            if item_id in v["items"]:
                used_in.append(v)
        return used_in

    items_with_usage = []
    for it in items_data:
        used_in = find_versions_for_item(it["id"])
        items_with_usage.append({
            "item": it,
            "versions": used_in
        })

    return render_template("items.html", items_with_usage=items_with_usage)

@app.route("/items/<int:item_id>/edit", methods=["GET"])
def edit_item(item_id):
    items_data = load_json(ITEMS_FILE)
    item = next((i for i in items_data if i["id"] == item_id), None)
    if not item:
        return "Item not found.", 404
    return render_template("item_edit.html", item=item)

@app.route("/items/<int:item_id>/update", methods=["POST"])
def update_item(item_id):
    items_data = load_json(ITEMS_FILE)
    item = next((i for i in items_data if i["id"] == item_id), None)
    if not item:
        return "Item not found.", 404

    item["name"] = request.form.get("name")
    item["category"] = request.form.get("category")
    item["productLink"] = request.form.get("productLink")

    save_json(ITEMS_FILE, items_data)
    return redirect(url_for("items_list"))

@app.route("/items/<int:item_id>/delete", methods=["POST"])
def delete_item(item_id):
    """どのバージョンにも使われていない場合のみ削除"""
    items_data = load_json(ITEMS_FILE)
    versions = load_json(VERSIONS_FILE)

    item = next((i for i in items_data if i["id"] == item_id), None)
    if not item:
        return "Item not found.", 404

    # 使われているかチェック
    used = any(item_id in v["items"] for v in versions)
    if used:
        return "このアイテムはバージョンで使用中のため削除できません。", 400

    # 削除
    items_data = [i for i in items_data if i["id"] != item_id]
    save_json(ITEMS_FILE, items_data)
    return redirect(url_for("items_list"))

# ---------------------
# Flask起動
# ---------------------
if __name__ == "__main__":
    app.run(debug=True)
