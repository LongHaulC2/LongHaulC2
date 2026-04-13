import json

from nicegui import ui


class MetadataView(ui.scroll_area):
    """
    A modular component for rendering dynamic metadata in a dashboard.
    Simple values are displayed in a responsive grid of cards, while complex values
    (JSON blobs, lists, long strings) are displayed in expandable code blocks below.
    Uses existing 'tech-' CSS classes for styling.
    """

    def __init__(self, metadata: dict, **kwargs):
        super().__init__(**kwargs)
        self.classes("w-full h-full").classes("p-4 gap-6 flex flex-col")
        with self:
            self.render_content(metadata or {})

    @ui.refreshable
    def render_content(self, metadata: dict):
        """
        Refreshable render block. Call `view.render_content.refresh(new_data)`
        to seamlessly update the UI when new metadata arrives.
        """
        if not metadata:
            ui.label("NO METADATA AVAILABLE").classes("tech-label-sub text-neutral-500 italic")
            return

        simple_data = {}
        complex_data = {}
        STRING_LENGTH_THRESHOLD = 80

        for k, v in metadata.items():
            if isinstance(v, (dict, list)) or (isinstance(v, str) and len(v) > STRING_LENGTH_THRESHOLD):  # noqa
                complex_data[k] = v
            else:
                simple_data[k] = v

        if simple_data:
            with ui.grid(columns="repeat(auto-fit, minmax(280px, 1fr))").classes("w-full gap-4"):
                for key, value in simple_data.items():
                    self._render_stat_card(key, value)

        if complex_data:
            with ui.column().classes("w-full gap-4 mt-2"):
                for key, value in complex_data.items():
                    self._render_complex_block(key, value)

    def _render_stat_card(self, key: str, value: any):
        formatted_key = str(key).replace("_", " ").upper()

        # Added .props('flat bg-transparent') instead of shadow-none
        with (
            ui.card()
            .props("flat bg-transparent")
            .classes(
                "tech-glass-panel rounded border border-white/5 p-4 gap-1 "
                "hover:border-emerald-500/30 hover:bg-white/5 transition-all"
            )
        ):
            ui.label(formatted_key).classes("tech-label-sub text-[11px] opacity-70 tracking-wider mb-1")
            ui.label(str(value)).classes("tech-data-mono text-sm text-emerald-50 break-words")

    def _render_complex_block(self, key: str, value: any):
        formatted_key = str(key).replace("_", " ").upper()
        is_json = isinstance(value, (dict, list))  # noqa
        display_text = json.dumps(value, indent=2) if is_json else str(value)

        with ui.column().classes("w-full gap-1 tech-glass-panel border-white/5 rounded p-4"):
            with ui.row().classes("w-full justify-between items-center mb-1"):
                ui.label(f"{formatted_key} //").classes("tech-label-sub text-xs text-emerald-500")
                ui.icon("data_object" if is_json else "article", size="xs", color="grey-5")

            ui.label(display_text).classes(
                "tech-data-mono w-full text-emerald-400 font-mono text-xs overflow-x-auto p-3 m-0 "
                "bg-black/40 rounded shadow-inner border border-white/5 whitespace-pre"
            )
