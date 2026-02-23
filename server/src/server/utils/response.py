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
    # errors: Optional[Any] = None
    # code: Optional[str] = None

    def to_dict(self) -> dict:
        """Return dict without None values, like your previous cleanup."""
        # return {k: v for k, v in asdict(self).items() if v is not None}
        # not removing null/none values, as null is a valid response for some API responses
        return {k: v for k, v in asdict(self).items()}

    def jsonify(self):
        """Return a Flask JSON response."""
        response_dict = self.to_dict()
        # api_logger.debug(f"Generating Response: {response_dict}")
        return jsonify(response_dict)
