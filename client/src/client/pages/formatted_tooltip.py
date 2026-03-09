from nicegui import ui


def formatted_tooltip(title: str, body: str, footer: str | None = None, max_width: int = 260):
    """
    Creates a styled NiceGUI tooltip with consistent formatting.
    Takes HTML args! i.e., <i>...</i> for italicized

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
            <b><u>{title}</u></b><br>
            <br>
            {body_html}
            {footer_html}
            <br>
        </div>
    """

    with ui.tooltip("").classes("tech-tooltip"):
        ui.html(html)
