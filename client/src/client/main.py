from nicegui import ui

# import componenets
# need to do FULL path import, as the process forks off from the main py process
# still call with `python3 -m client.src.client.main`
from client.src.client.widgets.operations.implants import ImplantWidget

# setup structure
with ui.header().classes(replace='row items-center') as header:
    #ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white')
    with ui.tabs() as tabs:
        ui.tab('Operations')
        ui.tab('B')
        ui.tab('C')

with ui.footer(value=False) as footer:
    ui.label('Footer')

# with ui.left_drawer().classes('bg-blue-100') as left_drawer:
#     ui.label('Side menu')

with ui.page_sticky(position='bottom-right', x_offset=20, y_offset=20):
    ui.button(on_click=footer.toggle, icon='contact_support').props('fab')

with ui.tab_panels(tabs, value='A').classes('w-full h-full'):
    with ui.tab_panel('Operations'):
        implant_widget = ImplantWidget()
        implant_widget.render()
    with ui.tab_panel('C'):
        # b = implants()
        # b.render()
        ui.label('Content of C')


#ui.run(native=True, dark=True)
ui.run(native=False, dark=True, show=False)