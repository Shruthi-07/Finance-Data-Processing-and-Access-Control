from flask import Flask, jsonify, render_template
from flask_cors import CORS
from config import Config
from extensions import limiter
import mysql.connector
from routes.auth_routes import auth_bp
from extensions import init_db

init_db(app)
MYSQL_SSL_CA = "ca.pem"

print("✅ Database setup done!")

app = Flask(__name__)
app.config.from_object(Config)

CORS(app)
limiter.init_app(app)

# ── Blueprints 
from routes.auth_routes      import auth_bp
from routes.user_routes      import user_bp
from routes.record_routes    import record_bp
from routes.analytics_routes import analytics_bp

app.register_blueprint(auth_bp,       url_prefix="/api/auth")
app.register_blueprint(user_bp,       url_prefix="/api/users")
app.register_blueprint(record_bp,     url_prefix="/api/records")
app.register_blueprint(analytics_bp,  url_prefix="/api/analytics")

# ── Health check 
@app.route("/api/health")
def health():
    return {"status": "ok", "version": "2.0"}, 200

# ── Frontend 
@app.route("/")
def dashboard():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, port=5000)