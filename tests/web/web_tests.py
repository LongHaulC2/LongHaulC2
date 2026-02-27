import pytest
from nicegui import ui
import sys
from pathlib import Path
# hack to allow this file to see the project root
sys.path.append(str(Path(__file__).resolve().parents[2]))

from nicegui.testing import User

@pytest.mark.nicegui_main_file('client/src/client/main.py')
async def test_client_ui(user: User):
    await user.open('/')
    # ... test logic ...