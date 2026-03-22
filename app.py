from flask import Flask
from database import init_db
from routes_auth import register_auth_routes
from routes_worker import register_worker_routes
from routes_admin import register_admin_routes

app = Flask(__name__)
app.secret_key = "super_secret_dev_key"

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

register_auth_routes(app)
register_worker_routes(app)
register_admin_routes(app)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)