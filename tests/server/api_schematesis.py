import schemathesis
from hypothesis import strategies as st
import sys
from pathlib import Path
from edwh_uuid7 import uuid7

# hack to allow this file to see the project root
sys.path.append(str(Path(__file__).resolve().parents[2]))
from server.src.server.main import app  # Import your Flask app instance




# UUID7 testing
uuid7_strategy = st.builds(uuid7).map(str)

# 2. Tell Schemathesis to use this strategy whenever it sees format="uuid"
schemathesis.openapi.format("uuid", uuid7_strategy)

schema = schemathesis.openapi.from_wsgi("/api/v1/swagger.json", app)

@schema.parametrize()
def test_api(case):
    case.call_and_validate()