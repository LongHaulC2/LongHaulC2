from dataclasses import asdict, dataclass
from typing import Any

import structlog
from flask import jsonify

api_logger = structlog.getLogger("api")


@dataclass
class APIResponse:
    status: str
    message: str
    data: Any | None = None

    def to_dict(self) -> dict:
        """Return dict, excluding fields that are None."""
        # This keeps the key if v is 0, "", or {}, but removes it if v is None
        return {k: v for k, v in asdict(self).items() if v is not None}

    def jsonify(self):
        """Return a Flask JSON response."""
        return jsonify(self.to_dict())
