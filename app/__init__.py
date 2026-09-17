import os
import tempfile

from flask import Flask

from .db import close_db, get_db, init_db


def create_app(testing=False, db_path=None):
    """Application factory.

    testing=True configures the app to use a fresh temporary SQLite
    database file for the lifetime of the app instance, which is what the
    test suite uses so each test run starts from a clean schema.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "dev-secret-key-change-me"
    )

    if testing:
        # Use a fresh temp file (or override) per test app so tests never
        # touch the real instance database and never leak state between runs.
        fd, tmp_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        app.config.update(
            TESTING=True,
            DATABASE=db_path or tmp_path,
        )
    else:
        os.makedirs(app.instance_path, exist_ok=True)
        app.config.update(
            DATABASE=db_path or os.path.join(app.instance_path, "airbnb.db"),
        )

    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    from . import routes

    app.register_blueprint(routes.bp)

    return app
