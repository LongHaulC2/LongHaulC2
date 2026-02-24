from nicegui import app, ui

from client.src.client.modules.api_calls import get_health_status

previous_status = {}
first_check = True


async def health_check():
    global previous_status, first_check

    response = await get_health_status()
    current_data = response.get("data", {})

    # join dicts together for comparison
    current_status = {**current_data.get("core", {}), **current_data.get("listeners", {})}

    # skip on first check, it needs to get the status populated once.
    if first_check:
        previous_status = current_status.copy()
        first_check = False
        return

    # check differences
    changes = {k: v for k, v in current_status.items() if k not in previous_status or previous_status[k] != v}

    # on change, alert
    if changes:
        core_keys = current_data.get("core", {}).keys()

        for name, status in changes.items():
            display_name = name.replace("_", " ").title()

            # check critical
            if name in core_keys:
                if status != "running":
                    message = (
                        f"CRITICAL FAILURE: {display_name} is now '{status}'. "
                        f"The server cannot continue to function with {display_name} down. "
                    )

                    ui.notification(message=message, timeout=None, close_button="OK", type="negative")
                else:
                    ui.notification(
                        f"CORE RECOVERY: {display_name} is '{status}'", timeout=None, type="positive", close_button="OK"
                    )

            # check listeners/noncritical
            else:
                if status != "running":
                    message = f"Listener {display_name}: '{status}'"
                    ui.notification(message=message, type="warning", close_button="OK")
                else:
                    message = f"Listener {display_name}: '{status}'"
                    ui.notification(message=message, type="positive", close_button="OK")

    # update previous state
    previous_status = current_status.copy()


# This runs globally, but only starts when a browser tab is open
app.on_connect(lambda: ui.timer(1.0, health_check))
