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

    # ソート: startPeriod(日付)が新しい順 → endPeriod(日付)が新しい順
    def version_sort_key(v):
        # parse_date で None になる可能性があるので、ソート用に補完
        sp = parse_date(v.get("startPeriod", "")) or datetime.min.date()
        ep = parse_date(v.get("endPeriod", "")) or datetime.min.date()
        return (sp, ep)

    versions_sorted = sorted(versions, key=version_sort_key, reverse=True)

    return render_template("index.html", versions=versions_sorted)

# ---------------------
# デスク環境バージョン 新規登録
# ---------------------
@app.route("/version/new", methods=["GET", "POST"])
def create_version():
    versions = load_json(VERSIONS_FILE)
    items = load_json(ITEMS_FILE)

    # 直前のデスク環境を取得
    last_version = None
    if versions:
        # startPeriodで降順ソートして最新を取得
        last_version = sorted(
            versions,
            key=lambda v: v.get("startPeriod", ""),
            reverse=True
        )[0]

    if request.method == "POST":
        version_name = request.form.get("versionName")
        start_period = request.form.get("startPeriod")  # yyyy-mm-dd形式

        new_id = get_next_id(versions)
        new_ver = {
            "id": new_id,
            "versionName": version_name,
            "startPeriod": start_period,
            "item_ids": []
        }

        # 直前バージョンの終期を更新
        if last_version:
            last_version["endPeriod"] = start_period
            
        # 既存アイテムのアタッチ
        attached_item_ids = request.form.getlist("attach_item_ids")
        for i_id in attached_item_ids:
            new_ver["item_ids"].append(int(i_id))

        # アイテム新規登録 → 即アタッチ
        new_item_name = request.form.get("new_item_name")
        if new_item_name:
            new_item_cat = request.form.get("new_item_category")
            new_item_link = request.form.get("new_item_link")
            item_id = get_next_id(items)
            new_item = {
                "id": item_id,
                "name": new_item_name,
                "category": new_item_cat,
                "productLink": new_item_link
            }
            items.append(new_item)
            new_ver["item_ids"].append(item_id)

        versions.append(new_ver)
        save_json(VERSIONS_FILE, versions)
        save_json(ITEMS_FILE, items)

        return redirect(url_for("show_version", version_id=new_id))

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
    attached_items = [i for i in items if i["id"] in version.get("item_ids", [])]

    # 前後のバージョンを取得
    start_period = version.get("startPeriod", "")
    prev_version = next(
        (v for v in sorted(
            versions,
            key=lambda x: x.get("startPeriod", ""),
            reverse=True
        ) if v.get("startPeriod", "") < start_period),
        None
    )
    next_version = next(
        (v for v in sorted(
            versions,
            key=lambda x: x.get("startPeriod", "")
        ) if v.get("startPeriod", "") > start_period),
        None
    )

    return render_template("version_detail.html",
                         version=version,
                         attached_items=attached_items,
                         all_items=items,
                         prev_version=prev_version,
                         next_version=next_version)

@app.route("/version/<int:version_id>/update", methods=["POST"])
def update_version_info(version_id):
    """バージョン情報の更新"""
    versions = load_json(VERSIONS_FILE)
    version = next((v for v in versions if v["id"] == version_id), None)
    if not version:
        return "Version not found.", 404

    # 更新前の始期を保持
    old_start_period = version.get("startPeriod")
    
    # フォームからの入力を取得
    version["versionName"] = request.form.get("versionName")
    new_start_period = request.form.get("startPeriod")  # yyyy-mm-dd形式
    
    # 始期が変更された場合
    if new_start_period and new_start_period != old_start_period:
        version["startPeriod"] = new_start_period
        
        # 全バージョンを始期でソート
        sorted_versions = sorted(
            versions,
            key=lambda x: x.get("startPeriod", ""),
            reverse=True
        )
        
        # 直前のバージョンを探す（現在のバージョンより前で最も近いもの）
        prev_version = next(
            (v for v in sorted_versions 
             if v.get("startPeriod", "") < new_start_period 
             and v["id"] != version_id),  # 自分自身は除外
            None
        )
        
        # 直前のバージョンが存在する場合、その終期を更新
        if prev_version:
            prev_version["endPeriod"] = new_start_period
    
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

    # 既存アイテムID（複数可）
    existing_item_ids = request.form.getlist("existing_item_ids")
    for i_id in existing_item_ids:
        item_id = int(i_id)
        if item_id not in version["item_ids"]:
            version["item_ids"].append(item_id)

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
        version["item_ids"].append(new_id)

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
    if item_id in version["item_ids"]:
        version["item_ids"].remove(item_id)

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
        # 新規アイテム（必須項目のバリデーション）
        name = request.form.get("name")
        category = request.form.get("category")
        if not name or not category:
            return "アイテム名とカテゴリは必須です。", 400

        link = request.form.get("productLink", "")  # 任意項目

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
        """アイテムが使用されているバージョンを始期降順で取得"""
        used_in = []
        for v in versions:
            if item_id in v.get("item_ids", []):
                used_in.append(v)
        # ここでソート
        return sorted(
            used_in,
            key=lambda x: x.get("startPeriod", ""),
            reverse=True
        )

    # カテゴリ別にソートしたアイテムリストを作成
    items_with_usage = []
    sorted_items = sorted(
        items_data,
        key=lambda x: (x["category"], x["name"])  # カテゴリでグループ化し、名前でソート
    )
    
    for item in sorted_items:
        used_in = find_versions_for_item(item["id"])
        items_with_usage.append({
            "item": item,
            "versions": used_in
        })

    return render_template("items.html", items_with_usage=items_with_usage)

@app.route("/items/<int:item_id>/edit", methods=["GET"])
def edit_item(item_id):
    """アイテム編集画面の表示"""
    items_data = load_json(ITEMS_FILE)
    item = next((i for i in items_data if i["id"] == item_id), None)
    if not item:
        return "Item not found.", 404
    return render_template("item_edit.html", item=item)

@app.route("/items/<int:item_id>/update", methods=["POST"])
def update_item(item_id):
    """アイテム情報の更新"""
    # 必須項目のバリデーション
    name = request.form.get("name")
    category = request.form.get("category")
    if not name or not category:
        return "アイテム名とカテゴリは必須です。", 400

    items_data = load_json(ITEMS_FILE)
    item = next((i for i in items_data if i["id"] == item_id), None)
    if not item:
        return "Item not found.", 404

    item["name"] = name
    item["category"] = category
    item["productLink"] = request.form.get("productLink", "")  # 任意項目

    save_json(ITEMS_FILE, items_data)
    return redirect(url_for("items_list"))

@app.route("/items/<int:item_id>/delete", methods=["POST"])
def delete_item(item_id):
    """どのバージョンにも使われていない場合のみ削除可能"""
    items_data = load_json(ITEMS_FILE)
    versions = load_json(VERSIONS_FILE)

    item = next((i for i in items_data if i["id"] == item_id), None)
    if not item:
        return "Item not found.", 404

    # 使われているかチェック
    used = any(item_id in v.get("item_ids", []) for v in versions)
    if used:
        return "このアイテムはバージョンで使用中のため削除できません。", 400

    # 削除
    items_data = [i for i in items_data if i["id"] != item_id]
    save_json(ITEMS_FILE, items_data)
    return redirect(url_for("items_list"))

@app.template_filter('format_date')
def format_date(date_str):
    """yyyy-mm-dd形式の日付文字列をyyyy年MM月形式に変換"""
    if not date_str:  # None や Undefined の場合
        return ''
    try:
        date_obj = datetime.strptime(str(date_str), '%Y-%m-%d')
        return date_obj.strftime('%Y年%m月')
    except (ValueError, TypeError):
        return str(date_str)

@app.template_filter('match_date_format')
def match_date_format(date_str):
    """yyyy-mm-dd形式の日付文字列かどうかを判定"""
    if not date_str:  # None や Undefined の場合
        return False
    try:
        datetime.strptime(str(date_str), '%Y-%m-%d')
        return True
    except (ValueError, TypeError):
        return False

@app.template_filter('has_item')
def has_item(version, item_id):
    """バージョンが特定のアイテムIDを持っているかチェック"""
    if not version:
        return False
    return item_id in version.get("item_ids", [])

# ---------------------
# Flask起動
# ---------------------
if __name__ == "__main__":
    app.run(debug=True)
