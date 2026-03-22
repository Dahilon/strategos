from flask import Flask
from flask_cors import CORS
from .config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Allow frontend dev server cross-origin requests
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from .api.planner import planner_bp
    app.register_blueprint(planner_bp, url_prefix='/api/planner')

    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'Border Stability Planner'}

    return app
