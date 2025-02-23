from flask import Flask, render_template, jsonify
import json

app = Flask(__name__)

def load_json(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/items')
def items():
    items_data = load_json('items.json')
    return render_template('items.html', items=items_data)

@app.route('/versions')
def versions():
    versions_data = load_json('versions.json')
    return render_template('versions.html', versions=versions_data)

@app.route('/version/<version_id>')
def version_detail(version_id):
    versions_data = load_json('versions.json')
    version = next((v for v in versions_data if v['id'] == version_id), None)
    if version:
        return render_template('version_detail.html', version=version)
    return "Version not found", 404

if __name__ == '__main__':
    app.run(debug=True) 