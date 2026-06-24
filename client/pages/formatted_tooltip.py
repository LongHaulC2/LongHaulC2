from nicegui import ui


def formatted_tooltip(title: str, body: str = "", footer: str | None = None, max_width: int = 260):
    """
    Creates a styled NiceGUI tooltip with consistent formatting.
    Takes HTML args! i.e., <i>...</i> for italicized

    :param title: Bold header text
    :param body: Main body text (plain text, line breaks allowed with \n)
    :param footer: Optional subtle footer text
    :param max_width: Tooltip max width in px
    """
    # start with title (as it's req'd)
    parts = [f"<b>{title}</b>"]

    # Only add body if it has content
    if body:
        # \n/<br> makes it look nice & seperate from title
        parts.append(body.replace("\n", "<br>"))

    # Only add footer if it exists
    if footer:
        parts.append(f'<span style="opacity: 0.8;">{footer}</span>')

    # Join the existing parts with a double break for clean paragraph spacing
    content_html = "<br><br>".join(parts)

    # Wrap in the container
    html = f"""
        <div style="max-width: {max_width}px; white-space: normal;">
            {content_html}
        </div>
    """

    with ui.tooltip("").classes("tech-tooltip"):
        ui.html(html)
