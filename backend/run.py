import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('BACKEND_PORT', 5001))
    # Solo desarrollo: produccion arranca con gunicorn (backend/entrypoint.sh), no con este archivo.
    # nosemgrep: python.flask.security.audit.app-run-param-config.avoid_app_run_with_bad_host
    app.run(host='0.0.0.0', port=port)
