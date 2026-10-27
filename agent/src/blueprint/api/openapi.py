"""Export the REST contract (SPECS S3.7): ``python -m blueprint.api.openapi > ../web/openapi.json``.

The document is generated from the same router and error handlers the service
mounts, without a database or models, so the frontend's types can be
regenerated offline.
"""

import json
from typing import Any, cast

from fastapi import FastAPI

from blueprint.api.routes import install_error_handlers, session_routes

TITLE = "Blueprint Studio agent"
VERSION = "0.1.0"


def rest_document() -> dict[str, Any]:
    app = FastAPI(title=TITLE, version=VERSION)
    install_error_handlers(app)
    unused = cast(Any, None)
    app.include_router(session_routes(unused, unused, unused, 0, True))
    return app.openapi()


if __name__ == "__main__":
    print(json.dumps(rest_document(), indent=2, sort_keys=True))
