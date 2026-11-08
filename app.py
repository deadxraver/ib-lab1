import os

import bcrypt
from flask import Flask, jsonify, request
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from markupsafe import escape

from models import Post, User, db

HOUR = 60 * 60

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///app.db"
)
app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 1 * HOUR

db.init_app(app)
jwt = JWTManager(app)


def init_db() -> None:
    with app.app_context():
        db.create_all()


@app.errorhandler(404)
def not_found(_err):
    return jsonify({"msg": "Not found"}), 404


@app.errorhandler(405)
def method_not_allowed(_err):
    return jsonify({"msg": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(_err):
    return jsonify({"msg": "Internal server error"}), 500


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not username or not password:
        return jsonify({"msg": "username and password required"}), 400

    user = User.query.filter_by(username=username).first()
    if user is None or not bcrypt.checkpw(
        password.encode("utf-8"), user.password_hash.encode("utf-8")
    ):
        return jsonify({"msg": "username or password incorrect"}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "token_type": "Bearer"}), 200 #nosec B105


@app.route("/api/data", methods=["GET"])
@jwt_required()
def get_data():
    current_user_id = int(get_jwt_identity())
    posts = Post.query.filter_by(author_id=current_user_id).all()
    return (
        jsonify(
            {
                "user_id": current_user_id,
                "data": [
                    {
                        "id": p.id,
                        "title": str(escape(p.title)),
                        "content": str(escape(p.content)),
                    }
                    for p in posts
                ],
            }
        ),
        200,
    )


@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if len(username) < 3:
        return jsonify({"msg": "username should be >= 3 symbols"}), 400
    if len(password) < 8:
        return jsonify({"msg": "password should be >= 8 symbols"}), 400

    if User.query.filter_by(username=username).first() is not None:
        return jsonify({"msg": "User already exists"}), 409

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    user = User(username=str(escape(username)), password_hash=password_hash)
    db.session.add(user)
    db.session.commit()

    return jsonify({"msg": "Registration successful", "id": user.id}), 201


@app.route("/api/posts", methods=["POST"])
@jwt_required()
def create_post():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    content = str(data.get("content", "")).strip()

    if not title or not content:
        return jsonify({"msg": "title and content required"}), 400

    post = Post(
        title=str(escape(title)),
        content=str(escape(content)),
        author_id=int(get_jwt_identity()),
    )
    db.session.add(post)
    db.session.commit()

    return jsonify({"msg": "Post created", "id": post.id}), 201


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
