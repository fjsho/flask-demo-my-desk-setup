# デスク環境バージョン管理システムデモ

## 概要
このプロジェクトは、アイテムのバージョン管理を行うWebアプリケーションのデモです。

## 機能
- アイテムの登録・編集
- バージョン履歴の管理
- バージョンの詳細表示
- 新規バージョンの作成

## 技術スタック
- Python
- Flask (Webフレームワーク)
- HTML/CSS
- SQLite (データベース)

## プロジェクト構造 
```
version-management-system
├── app.py
├── db.sqlite3
├── requirements.txt
├── README.md
└── templates
    ├── index.html
    ├── items.html
    ├── item_edit.html
    ├── versions.html
    └── version_edit.html
``` 

## 環境構築
```
# 依存パッケージをインストール
pip install -r requirements.txt

# アプリケーションを起動
python app.py
```
