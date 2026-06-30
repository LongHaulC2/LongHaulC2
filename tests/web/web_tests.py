import pytest
from nicegui import ui
import sys
from pathlib import Path
import logging
# hack to allow this file to see the project root
sys.path.append(str(Path(__file__).resolve().parents[2]))

from nicegui.testing import User

'''
Note - logging in and using cookies is a PITA.
This testing is just going through each page and making sure key elements are there/the page actually renders.

It's not much but its something rather than nothing

Note: caplog is set at critical, as ERROR happens in this due to not being able to make HTTP req's.  This is expected,
see above about cookies being a PITA
'''

@pytest.mark.nicegui_main_file('client/main.py')
async def test_client_login_page(user: User, caplog):
    with caplog.at_level(logging.CRITICAL):

        print("Testing Login")
        await user.open('/login')
        # make sure user sees this
        await user.should_see("LONGHAULC2")
        await user.should_see("USERNAME")
        await user.should_see("PASSWORD")
        await user.should_see("LOGIN")

    # not doing further testing cuz it's a PITA with cookies

@pytest.mark.nicegui_main_file('client/main.py')
async def test_client_operations_page(user: User, caplog):
    # Operations requires auth (api_host set in storage). Without it, setup_menu
    # redirects to /login. This test verifies that auth guard is active.
    with caplog.at_level(logging.CRITICAL):
        await user.open('/operations')
        await user.should_see("USERNAME")
        await user.should_see("PASSWORD")

@pytest.mark.nicegui_main_file('client/main.py')
async def test_listeners_page(user: User, caplog):
    # Listeners requires auth. Without api_host in storage, setup_menu redirects
    # to /login. This test verifies that auth guard is active.
    with caplog.at_level(logging.CRITICAL):
        await user.open('/listeners')
        await user.should_see("USERNAME")
        await user.should_see("PASSWORD")

@pytest.mark.nicegui_main_file('client/main.py')
async def test_payloads_page(user: User, caplog):
    # Payloads requires auth. Without api_host in storage, setup_menu redirects
    # to /login. This test verifies that auth guard is active.
    with caplog.at_level(logging.CRITICAL):
        await user.open('/payloads')
        await user.should_see("USERNAME")
        await user.should_see("PASSWORD")

@pytest.mark.nicegui_main_file('client/main.py')
async def test_profile_preview_page(user: User, caplog):
    # Profile Preview requires auth. Without api_host in storage, setup_menu redirects
    # to /login. This test verifies that auth guard is active.
    with caplog.at_level(logging.CRITICAL):
        await user.open('/profile-preview')
        await user.should_see("USERNAME")
        await user.should_see("PASSWORD")

# @pytest.mark.nicegui_main_file('client/main.py')
# async def test_graph_page(user: User, caplog):
#     print("Testing Network Topology Graph Page Load")
    
#     # Using caplog to ignore potential ECharts or API correlation errors on load
#     with caplog.at_level(logging.CRITICAL):
#         await user.open('/graph')
        
#         # --- Header Section ---
#         # Verifying the main section title and icon label
#         await user.should_see("NETWORK_TOPOLOGY //")
        
#         # Verifying the timestamp label is present (partial match for "UTC:")
#         await user.should_see("UTC:")
        
#         # --- Graph Controls ---
#         # Verifying the toggle for node physics exists
#         await user.should_see("Freeze Nodes")
        
#         # --- Sidebar / Inspector ---
#         # The sidebar is initialized empty but with specific classes.
#         # We check for the details header which appears once a node is clicked,
#         # but for a smoketest, we verify the "DETAILS:" label doesn't crash the UI.
#         # Note: If no node is clicked, this might not be visible yet, 
#         # so we check for the sidebar container area.
#         assert await user.find("NETWORK_TOPOLOGY //") is not None
        
#         # --- Refresh Button ---
#         # Check for the refresh button icon/action presence
#         await user.should_see("refresh")

# --- Additional page smoke tests ---
# All pages below follow the same pattern: open the route, verify key static
# labels are rendered.  API calls on page-load will fail (no server running),
# which is expected — errors are suppressed via caplog.CRITICAL.

@pytest.mark.nicegui_main_file('client/main.py')
async def test_filestore_page(user: User, caplog):
    with caplog.at_level(logging.CRITICAL):
        await user.open('/filestore')
        await user.should_see("FILE STORE //")


@pytest.mark.nicegui_main_file('client/main.py')
async def test_status_page(user: User, caplog):
    with caplog.at_level(logging.CRITICAL):
        await user.open('/status')
        await user.should_see("SYSTEM STATUS //")
        await user.should_see("CORE")
        await user.should_see("LISTENERS")


@pytest.mark.nicegui_main_file('client/main.py')
async def test_comms_page(user: User, caplog):
    with caplog.at_level(logging.CRITICAL):
        await user.open('/comms')
        await user.should_see("SECURE COMMS")
        await user.should_see("CHANNEL // GLOBAL_OP")


@pytest.mark.nicegui_main_file('client/main.py')
async def test_user_settings_page(user: User, caplog):
    with caplog.at_level(logging.CRITICAL):
        await user.open('/settings')
        await user.should_see("USER SETTINGS //")
        await user.should_see("Element Auto Refresh Rate")


