import httpx
from nicegui import ui

@ui.page('/operations')
async def operations():
    a = ui.label("Loading...")  # create the label first

    async with httpx.AsyncClient() as client:
        response = await client.get('http://10.0.0.30:45045/api/v1/implants/')
        data = response.json()

    # Update the label after async I/O
    a.set_text(str(data))