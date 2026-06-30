import traceback
import urllib.parse

from nicegui import app, ui

from client.utils.helpers import notify


@app.on_page_exception
def generate_error(exception: Exception) -> None:
    # Capture the traceback upfront
    error_trace = traceback.format_exc(chain=False)

    # Center the whole layout and give it a max width for readability
    with ui.column().classes("absolute-center items-center w-full p-4"):  # noqa: SIM117
        with ui.card().classes("w-full items-center p-8 gap-4 max-w-1/2 shadow-xl rounded-2xl"):
            ui.label("LongHaulC2-Web Encountered An Unhandled Error").classes("tech-label-sub")
            ui.separator()

            if isinstance(exception, TimeoutError):
                ui.icon("sym_o_timer", size="4rem", color="warning")
            else:
                ui.icon("error_outline", size="4rem", color="negative")

            ui.label(f"{exception.__class__.__name__}: {exception}").classes("tech-label-sub")

            ui.code(error_trace).classes("w-full text-sm max-h-64 overflow-auto rounded-lg")

            api_host = app.storage.user.get("api_host", "Not Set")
            ui.label(f"API_HOST: {api_host}").classes("tech-label-sub")

            # Handler for the GitHub button
            def on_github_click():
                api_host = app.storage.user.get("api_host", "Not Set")

                issue_title = f"Bug Report: {exception.__class__.__name__}"
                issue_body = (
                    f"### Environment\n- **API_HOST:** `{api_host}`\n\n"
                    f"### Error Details\n**Exception:** `{exception}`\n\n"
                    f"### Traceback\n```python\n{error_trace}\n```"
                )

                params = urllib.parse.urlencode({"title": issue_title, "body": issue_body})

                github_url = f"https://github.com/LongHaulC2/LongHaulC2/issues/new?{params}"

                # write err to clipboard, disabled as the report issue now auto fills
                # ui.clipboard.write(issue_body)
                notify("Opening GitHub with error details pre-filled...", icon="rocket_launch")

                ui.run_javascript(f'window.open("{github_url}", "_blank")')

            # Action buttons grouped in a neat row
            with ui.row().classes("w-full justify-center gap-4 mt-4"):
                ui.button(
                    "Go to Login", icon="login", color="primary", on_click=lambda: ui.navigate.to("/login")
                ).props("outline")
                ui.button("Report Issue on GitHub", icon="bug_report", color="negative", on_click=on_github_click)


@ui.page("/raise_runtime_error")
def raise_runtime_error():
    raise RuntimeError("Something is wrong")
