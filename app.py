import os
from flask import Flask
from database import init_db
from models.models import db
from routes.auth_bp import auth_bp
from routes.worker_bp import worker_bp
from routes.admin_bp import admin_bp

app = Flask(__name__)
app.secret_key = "super_secret_dev_key"

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "db", "rendiciones.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

app.register_blueprint(auth_bp)
app.register_blueprint(worker_bp)
app.register_blueprint(admin_bp)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
