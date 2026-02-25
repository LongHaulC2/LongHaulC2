from nicegui import ui

from ..utils.checks import check_type


async def open_notes_dialog(implant_uuid: str | str, populate_editor_with: str = "") -> str:
    check_type(implant_uuid, str, "implant_uuid")
    check_type(populate_editor_with, str, "populate_editor_with")

    with ui.dialog(), ui.card().classes("w-1/2 h-1/2 p-4"):
        # Title or header for the editor
        ui.label(f"Notes: {implant_uuid}").classes("tech-label-sub")

        # Textarea for taking notes
        # ui.textarea("somedata").classes(
        #     "w-full h-40 p-2 border border-gray-300 resize-none mb-4"
        # )
        # using editor for HTML stuff instead
        editor = ui.editor(placeholder="Type something here", value=populate_editor_with).classes("w-full h-full")

        # Footer with buttons for saving and quitting
        # with ui.row().classes("w-full justify-between"):
        #     ui.button("Save").on("click", dialog.close()).classes(
        #         "w-1/3 px-4 py-2 rounded-lg"
        #     )
        #     ui.button("Quit").on("click", dialog.close()).classes(
        #         "w-1/3 px-4 py-2 rounded-lg"
        #     )
        # need to figure out the logic of those

    # result = await dialog
    return editor.value


# ui.button("Await a dialog", on_click=show)

# ui.run()
