import asyncio

import hexdump
from nicegui import ui

from client.pages.custom import BongoSpinner
from client.utils.helpers import notify


class GenericHexViewer:
    def __init__(self, entity_id: str, fetch_bytes_api):
        """
        A generic read-only CodeMirror viewer for displaying hexdumps.

        :param entity_id: The UUID or ID of the file/entity.
        :param fetch_bytes_api: Async function `async def fetch(id) -> bytes`
        """
        self.entity_id = entity_id
        self.fetch_bytes_api = fetch_bytes_api

        # UI Layout
        with ui.column().classes("w-full h-full p-0 gap-0 relative"):
            # --- Spinner & Viewer ---
            self.spinner = BongoSpinner("Processing hexdump (this may take a moment)...")

            self.viewer = ui.codemirror(
                value="Waiting for data...",
                theme="androidstudio",
                language="yaml",  # 'yaml' or 'plaintext' work fine for basic syntax highlighting
            ).classes("w-full flex-grow bg-transparent text-emerald-400 font-mono text-xs")

        # Trigger data load on mount
        ui.timer(0, self.load_hexdump, once=True)

    async def load_hexdump(self):
        await asyncio.sleep(0.1)  # Brief yield to ensure UI paints before heavy lifting
        self.spinner.start()

        try:
            # 1. Fetch the raw bytes
            data = await self.fetch_bytes_api(self.entity_id)

            if not data:
                self.viewer.value = "ERROR: No data returned or file is empty."
                return

            # 2. Process hexdump in a background thread to prevent UI freezing
            hex_str = await asyncio.to_thread(hexdump.hexdump, data, result="return")

            # 3. Display result
            self.viewer.value = hex_str

        except Exception as e:
            self.viewer.value = f"ERROR processing hexdump: {e}"
            notify("Failed to generate hexdump", type="negative")

        finally:
            self.spinner.stop()
