from nicegui import ui


def formatted_tooltip(title: str, body: str, footer: str | None = None, max_width: int = 260):
    """
    Creates a styled NiceGUI tooltip with consistent formatting.

    :param title: Bold header text
    :param body: Main body text (plain text, line breaks allowed with \n)
    :param footer: Optional subtle footer text
    :param max_width: Tooltip max width in px
    """
    # Convert newline to <br>
    body_html = body.replace("\n", "<br>")

    footer_html = ""
    if footer:
        footer_html = f'<br><br><span style="opacity: 0.8;">{footer}</span>'

    html = f"""
        <div style="max-width: {max_width}px;">
            <b>{title}</b><br>
            {body_html}
            {footer_html}
            <br>
        </div>
    """

    with ui.tooltip("").classes("text-body2"):
        ui.html(html)
