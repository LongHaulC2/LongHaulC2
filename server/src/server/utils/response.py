from dataclasses import dataclass, field, asdict
from typing import Any, Optional, Dict
from flask import jsonify
import logging

api_logger = logging.getLogger("api")

@dataclass
class APIResponse:
    status: str
    message: str
    data: Optional[Any] = None
    errors: Optional[Any] = None
    pagination: Optional[Dict[str, Any]] = None
    code: Optional[str] = None
    documentation_url: Optional[str] = None

    def to_dict(self) -> dict:
        """Return dict without None values, like your previous cleanup."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def jsonify(self):
        """Return a Flask JSON response."""
        response_dict = self.to_dict()
        api_logger.debug(f"Generating Response: {response_dict}")
        return jsonify(response_dict)
