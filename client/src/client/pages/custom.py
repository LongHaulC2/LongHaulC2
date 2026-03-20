from nicegui import ui


class BongoSpinner(ui.column):
    """
    Fun bongo cat spinner.

    Use when full page/larger spin items are needed.

    the normal ui.spinner is still used for smaller things, such as in-button spinners.
    """

    def __init__(self, message: str = "Loading..."):
        super().__init__()
        # absolute positioning, full coverage, semi-transparent background, and high z-index
        self.classes(
            "absolute top-0 left-0 w-full h-full z-50 bg-[#0a0a0a]/80 backdrop-blur-sm items-center justify-center"
        )

        with self:
            ui.image("/static/gif/bongo.gif").classes("w-40 h-40")
            # text right below bongo
            ui.label(message).classes("text-emerald-500 font-mono mt-4 animate-pulse")

        self.set_visibility(False)

    def start(self):
        self.set_visibility(True)

    def stop(self):
        self.set_visibility(False)
