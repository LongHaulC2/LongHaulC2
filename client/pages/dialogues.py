from nicegui import events, ui

from client.modules.api_calls import post_new_file_to_server_filestore, queue_task
from client.modules.task_definitions import FileUpload, MemStoreUpload
from client.utils.helpers import notify


async def upload_to_implant_dialog(implant_uuids: list):
    """
    Opens a styled dialog for uploading files to selected implants.
    """

    # mutable state to hold data between upload and submit
    state = {
        "mode": "disk",  # 'disk' or 'memstore'
        "dest": "",  # Remote path or memstore key
        "file_bytes": b"",  # Raw content
        "filename": "",  # Original filename
    }

    # Logic
    def check_ready():
        """Enables the submit button only when we have destination + file."""
        if state["dest"] and state["file_bytes"]:
            submit_btn.enable()
            # Add a visual glow when ready
            submit_btn.classes(add="shadow-[0_0_15px_rgba(16,185,129,0.4)]")
        else:
            submit_btn.disable()
            submit_btn.classes(remove="shadow-[0_0_15px_rgba(16,185,129,0.4)]")

    async def handle_upload(e: events.UploadEventArguments):
        try:
            # nicegui 3.0.0+ uses e.file.read()
            file_bytes = await e.file.read()
            state["file_bytes"] = file_bytes

            # notify(
            #     f"Staged: {e.file.name} ({len(file_bytes)} bytes)",
            #     type="positive",
            #     color="emerald",
            #     icon="check_circle",
            # )
            check_ready()
        except Exception as err:
            notify(f"Failed to read file: {err}", type="negative")

    async def submit_tasks():
        submit_btn.props("loading")
        try:
            for uuid in implant_uuids:
                if state["mode"] == "disk":
                    task = FileUpload(
                        implant_uuid=uuid,
                        file_path=state["dest"],
                        file_contents=state["file_bytes"],
                    )
                else:
                    task = MemStoreUpload(
                        implant_uuid=uuid,
                        file_name=state["dest"],
                        file_contents=state["file_bytes"],
                    )

                await queue_task(implant_uuid=uuid, task=task.to_task())

            notify(
                f"Queued upload for {len(implant_uuids)} targets",
                type="positive",
                color="emerald",
            )
            dialog.close()

        except Exception as err:
            notify(f"Task Error: {str(err)}", type="negative")
            submit_btn.props(remove="loading")

    # UI Layout
    with ui.dialog() as dialog, ui.card().classes("tech-dialog w-[500px] p-0 overflow-hidden"):
        # Header
        with ui.row().classes("tech-header-bar w-full items-center justify-between"):
            with ui.row().classes("gap-3 items-center"):
                ui.icon("upload_file", color="emerald-500").classes("text-xl")
                # Uses .tech-label-title for the monospace/tracking look
                ui.label(f"TASK_UPLOAD :: {len(implant_uuids)} TARGETS").classes("tech-label-sub")

            # Close button styled as a ghost icon
            ui.button(icon="close", on_click=dialog.close).props("square flat dense text-color=grey").classes(
                "opacity-70 hover:opacity-100 transition-opacity"
            )

        # Body
        with ui.column().classes("p-6 gap-5 w-full"):
            # Validation
            if len(implant_uuids) == 0:
                notify("Please select at least one implant to upload to", type="warning")
                return None

            # Target List
            # We removed the inline bg classes here so your CSS
            # .q-expansion-item rules can apply the blur/zinc-bg automatically
            with ui.expansion(f"Target List ({len(implant_uuids)})", icon="hub").classes("w-full"):  # noqa: SIM117
                with ui.column().classes("py-2 gap-1"):
                    for uid in implant_uuids:
                        ui.label(f"• {uid}").classes("tech-label-sub")

            # Controls
            def _update_mode(e):
                state["mode"] = e.value
                dest_input.label = "REMOTE FILE PATH" if e.value == "disk" else "MEMSTORE KEY"
                dest_input.placeholder = "C:\\\\Temp\\\\file.exe" if e.value == "disk" else ""
                dest_input.value = ""
                path_hint.set_visibility(e.value == "disk")
                check_ready()

            # Mode Selector
            ui.select(
                options={"disk": "Write to Disk", "memstore": "Write to Memstore"},
                value="disk",  # disk by default
                label="METHOD",
                on_change=_update_mode,
            ).props("outlined dense dark color=emerald options-dense").classes("w-full tech-select")

            # Destination Input
            dest_input = (
                ui.input(
                    label="REMOTE FILE PATH",
                    placeholder="C:\\\\Windows\\\\Temp\\\\payload.exe",
                    on_change=lambda e: (
                        state.update({"dest": e.value}),
                        check_ready(),
                    ),
                )
                .props("outlined dense dark color=emerald")
                .classes("w-full tech-input")
            )
            path_hint = ui.label("Use double backslashes for Windows paths (e.g. C:\\\\Temp\\\\file.exe)").classes(
                "text-xs text-amber-400/80 -mt-3 ml-1"
            )

            # File Upload
            ui.upload(
                label="SELECT FILE",
                auto_upload=True,
                max_files=1,
                on_upload=handle_upload,
            ).props("flat bordered dark color=emerald").classes("w-full bg-black/20")

        # Footer
        with ui.row().classes("w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"):
            ui.button("CANCEL", on_click=dialog.close).props("flat dense no-caps").classes(
                "tech-btn-action-2 font-bold tracking-wide"
            )

            submit_btn = (
                ui.button("QUEUE TASK", on_click=submit_tasks)
                .props("unelevated dense no-caps")
                .classes("tech-btn-action font-bold tracking-wide px-4")
            )

            submit_btn.disable()

    return await dialog


async def upload_to_server_filestore_dialog():
    state = {"files": []}

    def check_ready():
        if state["files"]:
            submit_btn.enable()
            submit_btn.classes(add="shadow-[0_0_15px_rgba(16,185,129,0.4)]")
            submit_btn.text = f"UPLOAD {len(state['files'])} FILES" if len(state["files"]) > 1 else "UPLOAD FILE"
        else:
            submit_btn.disable()
            submit_btn.classes(remove="shadow-[0_0_15px_rgba(16,185,129,0.4)]")
            submit_btn.text = "UPLOAD FILE"

    async def handle_upload(e: events.UploadEventArguments):
        try:
            file_bytes = await e.file.read()
            state["files"].append({"filename": e.file.name, "file_bytes": file_bytes})

            # notify(
            #     f"Staged: {e.file.name} ({len(file_bytes)} bytes)",
            #     type="positive",
            #     color="emerald",
            #     icon="check_circle",
            # )
            check_ready()
        except Exception as err:
            notify(f"Failed to read file: {err}", type="negative")

    async def submit_upload():
        if not state["files"]:
            return

        submit_btn.disable()
        submit_btn.text = "UPLOADING..."

        success_count = 0
        failed_files = []

        for f in state["files"]:
            try:
                response = await post_new_file_to_server_filestore(file_name=f["filename"], file_bytes=f["file_bytes"])
                if response:
                    success_count += 1
                else:
                    failed_files.append(f["filename"])
            except Exception as e:
                failed_files.append(f"{f['filename']} ({str(e)})")

        if success_count == len(state["files"]):
            notify(f"Successfully uploaded {success_count} files", type="positive")
            dialog.submit(True)
        elif success_count > 0:
            notify(f"Uploaded {success_count} files, but {len(failed_files)} failed.", type="warning")
            dialog.submit(True)
        else:
            notify("Failed to upload files.", type="negative")
            submit_btn.enable()
            check_ready()

    with ui.dialog() as dialog, ui.card().classes("tech-dialog w-[500px] p-0 overflow-hidden"):
        with ui.row().classes("tech-header-bar w-full items-center justify-between"):
            with ui.row().classes("gap-3 items-center"):
                ui.icon("cloud_upload", color="emerald-500").classes("text-xl")
                ui.label("SERVER FILESTORE UPLOAD").classes("tech-label-sub")

            ui.button(icon="close", on_click=dialog.close).props("square flat dense text-color=grey").classes(
                "opacity-70 hover:opacity-100 transition-opacity"
            )

        with ui.column().classes("p-6 gap-5 w-full"):
            ui.upload(
                label="SELECT FILES FOR SERVER",
                auto_upload=True,
                multiple=True,
                on_upload=handle_upload,
            ).props("flat bordered dark color=emerald").classes("w-full bg-black/20")

        with ui.row().classes("w-full bg-black/20 p-4 border-t border-white/5 justify-end gap-3"):
            ui.button("CANCEL", on_click=dialog.close).props("flat dense no-caps").classes(
                "tech-btn-action-2 font-bold tracking-wide"
            )

            submit_btn = (
                ui.button("UPLOAD FILE", on_click=submit_upload)
                .props("unelevated dense no-caps")
                .classes("tech-btn-action font-bold tracking-wide px-4")
            )

            submit_btn.disable()

    return await dialog
