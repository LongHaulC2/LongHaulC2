import schemathesis
import sys
from pathlib import Path

# hack to allow this file to see the project root
sys.path.append(str(Path(__file__).resolve().parents[2]))
from server.src.server.main import app  # Import your Flask app instance

schema = schemathesis.openapi.from_wsgi("/api/v1/swagger.json", app)

@schema.parametrize()
def test_api(case):
    case.call_and_validate()