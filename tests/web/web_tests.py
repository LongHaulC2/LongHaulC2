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

@pytest.mark.nicegui_main_file('client/src/client/main.py')
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

@pytest.mark.nicegui_main_file('client/src/client/main.py')
async def test_client_operations_page(user: User, caplog):
    with caplog.at_level(logging.CRITICAL):

        print("Testing Login")
        await user.open('/operations')
        # make sure user sees this
        await user.should_see("OPERATIONS")
        await user.should_see("ACTIVE_SESSIONS")
        await user.should_see("PAYLOAD")
        await user.should_see("LISTENER")

@pytest.mark.nicegui_main_file('client/src/client/main.py')
async def test_listeners_page(user: User, caplog):
    with caplog.at_level(logging.CRITICAL):

        print("Testing Listeners Page Load")
        
        # Navigate to the listeners route
        await user.open('/listeners')
        
        # --- Header Section ---
        # Verifying the main title and the primary 'add' button label
        await user.should_see("LISTENERS //")
        await user.should_see("LISTENER")
        
        # --- Stat Widgets ---
        # Checking for the stat labels in the stat_widget elements
        await user.should_see("Total:")
        await user.should_see("Online:")
        
        # --- Interaction Buttons (Footer of Table) ---
        # These verify the batch action buttons at the bottom of the table
        await user.should_see("START")
        await user.should_see("RESTART")
        await user.should_see("STOP")
        await user.should_see("DELETE")
    
    # --- Search/Filter ---
    # Verifying the placeholder in the search input
    await user.should_see("FILTER...")

@pytest.mark.nicegui_main_file('client/src/client/main.py')
async def test_payloads_page(user: User, caplog):
    with caplog.at_level(logging.CRITICAL):
        print("Testing Payloads Library Page Load")
        
        # Navigate to the payloads route
        await user.open('/payloads')
        
        # --- Header Section ---
        # Verifying the main title and the build action button
        await user.should_see("PAYLOAD_LIBRARY //")
        await user.should_see("PAYLOAD")
        
        # --- Telemetry Widgets ---
        # Checking for the stat labels in the stat_widget elements
        await user.should_see("Total Artifacts:")
        await user.should_see("Active Listeners:")
        await user.should_see("Latest Build:")
        
        # --- Search Strip ---
        # Verifying the placeholder in the artifact filter input
        await user.should_see("FILTER ARTIFACTS...")

# @pytest.mark.nicegui_main_file('client/src/client/main.py')
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

@pytest.mark.nicegui_main_file('client/src/client/main.py')
async def test_scripts_page(user: User, caplog):
    print("Testing Scripts Page Load")
    
    # Wrap in caplog context to ignore ERROR logs during page initialization
    with caplog.at_level(logging.CRITICAL):
        # 1. Open the page
        await user.open('/scripts')
        
        # --- File Picker (Left Sidebar) ---
        await user.should_see("SCRIPTS //")
        # Check for the action buttons in the file picker header
        await user.should_see("folder_open") # Icon check if supported, or labels below
        
        # --- Editor Section (Top Right) ---
        await user.should_see("EDITOR //")
        # CodeMirror might not render text immediately, 
        # but we check the container header is there.
        await user.should_see("code") 
        
        # --- Terminal Section (Bottom Right) ---
        await user.should_see("TERMINAL_OUTPUT //")
        await user.should_see("terminal")
        