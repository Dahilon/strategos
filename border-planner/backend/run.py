import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config


def main():
    errors = Config.validate()
    if errors:
        print("Configuration warnings:")
        for e in errors:
            print(f"  ⚠ {e}")
        print("  Config/health endpoints will work. Simulation endpoints need a valid key.\n")

    app = create_app()
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5002))
    print(f"\n  Border Stability Planner API")
    print(f"  Running on http://{host}:{port}")
    print(f"  Health: http://localhost:{port}/health")
    print(f"  Config: http://localhost:{port}/api/planner/config\n")
    app.run(host=host, port=port, debug=Config.DEBUG)


if __name__ == '__main__':
    main()
