import os

import psycopg2
import psycopg2.extras
from flask import Flask, g, jsonify, render_template, request

DATABASE_URL = os.environ["DATABASE_URL"]

app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    with conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
    conn.close()


@app.before_request
def ensure_db():
    init_db()


@app.route("/")
def index():
    return render_template("index.html")


# Read：查全部留言，DESC 讓最新的排最前面——每個人打開頁面看到的都是同一份
@app.route("/api/messages", methods=["GET"])
def list_messages():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id, name, content, created_at FROM messages ORDER BY id DESC")
        rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)


# Create：沒填名字就存「匿名」，內容一定要有；前端顯示時會做逃逸處理，這裡只管存
@app.route("/api/messages", methods=["POST"])
def create_message():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip() or "匿名"
    content = str(data.get("content", "")).strip()

    if not content:
        return jsonify({"error": "留言內容不能是空的"}), 400
    if len(name) > 30:
        return jsonify({"error": "名字太長了（上限 30 字）"}), 400
    if len(content) > 500:
        return jsonify({"error": "留言太長了（上限 500 字）"}), 400

    from datetime import datetime
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO messages (name, content, created_at) VALUES (%s, %s, %s) RETURNING id",
            (name, content, created_at),
        )
        new_id = cur.fetchone()["id"]
    db.commit()
    return jsonify({"id": new_id, "name": name, "content": content, "created_at": created_at}), 201


# Delete：這個範例沒有登入機制，任何人都能刪任何一則——刻意留給你思考的地方，見 README
@app.route("/api/messages/<int:message_id>", methods=["DELETE"])
def delete_message(message_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM messages WHERE id = %s", (message_id,))
    db.commit()
    return "", 204


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5051, debug=False)
