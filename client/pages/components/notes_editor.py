from nicegui import ui

from client.modules.api_calls import get_single_node_data, update_node_data


class GenericNotesEditor:
    def __init__(self, node_type: str, node_id: str):
        """
        A generic CodeMirror editor with conflict-detection.

        :param node_type: The type of entity (e.g., 'file', 'user').
        :param node_id: The UUID or ID of the specific entity.
        """
        self.node_type = node_type
        self.node_id = node_id

        # State tracking for the diff checker
        self.original_content = ""

        # UI Layout
        with ui.column().classes("w-full h-full p-0 gap-0"):
            # --- Toolbar ---
            with ui.row().classes(
                "w-full h-12 shrink-0 items-center justify-between px-4 border-b border-white/10 bg-black/20"
            ):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("edit_note", color="emerald-400")
                    ui.label(f"Editing {self.node_type.upper()} Notes").classes("text-xs text-gray-400 font-mono")

                with ui.row().classes("items-center gap-3"):
                    self.status_label = ui.label("").classes("text-xs text-gray-500 italic")
                    self.save_btn = (
                        ui.button("SAVE CHANGES", on_click=self.handle_save)
                        .props("dense outline size=sm")
                        .classes("tech-btn-action")
                    )

            # --- Editor ---
            self.editor = ui.codemirror(value="Loading...", theme="androidstudio", language="yaml").classes(
                "w-full flex-grow bg-transparent text-emerald-400 font-mono text-xs"
            )

        # Trigger data load on mount
        ui.timer(0, self.load_data, once=True)

    async def load_data(self):
        self.save_btn.disable()
        self.editor.value = "Fetching latest notes..."
        try:
            request_data = await get_single_node_data(self.node_type, self.node_id)
            if not request_data:
                # this means something bugged out
                self.editor.value = "Could not retrieve notes"
                return

            note_variable_name = f"{self.node_type}_notes"
            content = request_data.get("data", {}).get(note_variable_name, "")

            self.original_content = content or ""
            self.editor.value = self.original_content
        except Exception as e:
            ui.notify(f"Failed to load notes: {e}", type="negative")
            self.editor.value = "ERROR LOADING DATA"
        finally:
            self.save_btn.enable()

    async def handle_save(self):
        self.save_btn.disable()
        self.status_label.text = "Checking for conflicts..."

        try:
            # Pull latest to check for differences
            request_data = await get_single_node_data(self.node_type, self.node_id)
            note_variable_name = f"{self.node_type}_notes"
            latest_content = request_data.get("data", {}).get(note_variable_name, "")

            # Check for conflicts
            if latest_content != self.original_content:
                self.show_conflict_dialog()
                self.status_label.text = "Conflict detected!"
                return

            # If safe, execute save
            await self.execute_save()

        except Exception as e:
            ui.notify(f"Error during save prep: {e}", type="negative")
        finally:
            self.save_btn.enable()

    async def execute_save(self):
        self.status_label.text = "Saving..."
        try:
            note_variable_name = f"{self.node_type}_notes"
            note_data = {note_variable_name: self.editor.value}

            await update_node_data(self.node_type, self.node_id, note_data)
            self.original_content = self.editor.value  # Update baseline
            ui.notify("Notes saved successfully", type="positive")
            self.status_label.text = "Saved."
        except Exception as e:
            ui.notify(f"Failed to save notes: {e}", type="negative")
            self.status_label.text = "Save failed."

    def show_conflict_dialog(self):
        """Displays a warning if the database was updated while the user was editing."""
        with ui.dialog() as dialog, ui.card().classes("bg-slate-900 border border-red-500/50"):
            ui.label("Conflict Detected").classes("text-lg text-red-400 font-bold")
            ui.label("These notes were modified elsewhere since you opened them.")
            ui.label("Saving now will overwrite the other changes.")

            with ui.row().classes("w-full justify-end mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("flat color=white")
                ui.button("Force Overwrite", color="red", on_click=lambda: self._force_save(dialog))
        dialog.open()

    async def _force_save(self, dialog):
        dialog.close()
        await self.execute_save()
