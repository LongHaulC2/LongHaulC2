from nicegui import ui

class ImplantWidget:
    def init(self):
        ...

    def render(self):
        implant_widget = Implants()
        implant_widget.render()


class Implants:
    def __init__(self):
        # aligns fields to left
        ui.add_css("""
        .q-table th,
        .q-table td {
            text-align: left !important;
        }
        """)


    def render(self):
        with ui.card().classes("w-full h-full no-shadow").classes('tight-card'):

            columns = [
                {'name': 'id', 'label': 'ID', 'field': 'id', 'required': True, 'align': 'left', 'sortable': True},
                {'name': 'external_ip', 'label': 'External IP', 'field': 'external_ip', 'sortable': True},
                {'name': 'internal_ip', 'label': 'Internal IP', 'field': 'internal_ip'},
                {'name': 'listener', 'label': 'Listener', 'field': 'listener'},
                {'name': 'user', 'label': 'User', 'field': 'user'},
                {'name': 'hostname', 'label': 'Hostname', 'field': 'hostname'},
                {'name': 'notes', 'label': 'Notes', 'field': 'notes'},
                {'name': 'process', 'label': 'Process', 'field': 'process'},
                {'name': 'pid', 'label': 'PID', 'field': 'pid', 'sortable': True},
                {'name': 'arch', 'label': 'Arch', 'field': 'arch'},
                {'name': 'last_checkin', 'label': 'Last Check-in', 'field': 'last_checkin', 'sortable': True},
                {'name': 'sleep', 'label': 'Sleep (s)', 'field': 'sleep', 'sortable': True},
            ]

            rows = [
                {
                    'id': 1,
                    'external_ip': '34.118.92.10',
                    'internal_ip': '10.0.1.23',
                    'listener': 'https-main',
                    'user': 'CORP\\jdoe',
                    'hostname': 'WS-ACCT-01',
                    'notes': 'Initial foothold',
                    'process': 'explorer.exe',
                    'pid': 4120,
                    'arch': 'x64',
                    'last_checkin': '2025-12-14 14:02:11',
                    'sleep': 30,
                },
                {
                    'id': 2,
                    'external_ip': '52.184.33.77',
                    'internal_ip': '192.168.56.104',
                    'listener': 'dns-fallback',
                    'user': 'NT AUTHORITY\\SYSTEM',
                    'hostname': 'DB-SRV-02',
                    'notes': 'High privilege',
                    'process': 'svchost.exe',
                    'pid': 1024,
                    'arch': 'x64',
                    'last_checkin': '2025-12-14 14:01:02',
                    'sleep': 60,
                },
                {
                    'id': 3,
                    'external_ip': '18.204.199.3',
                    'internal_ip': '172.16.5.88',
                    'listener': 'http-backup',
                    'user': 'CORP\\asmith',
                    'hostname': 'ENG-LT-07',
                    'notes': '',
                    'process': 'chrome.exe',
                    'pid': 8760,
                    'arch': 'x86',
                    'last_checkin': '2025-12-14 13:59:47',
                    'sleep': 15,
                },
                {
                    'id': 4,
                    'external_ip': '44.201.11.92',
                    'internal_ip': '10.10.10.42',
                    'listener': 'https-main',
                    'user': 'CORP\\svc-backup',
                    'hostname': 'FILE-SRV-01',
                    'notes': 'Service account',
                    'process': 'powershell.exe',
                    'pid': 3321,
                    'arch': 'x64',
                    'last_checkin': '2025-12-14 14:03:45',
                    'sleep': 120,
                },
            ]

            with ui.scroll_area():
                ui.table(columns=columns, rows=rows, row_key='name').classes("w-full no-shadow").props("dense")
