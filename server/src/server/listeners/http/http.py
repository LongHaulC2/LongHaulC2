# PLACEHOLDER while I figure out the supervisor logic

# must haves: run entrypoint, that is a func, most flexible + no class init then by the supervisor (adds complexity)

from time import sleep
from edwh_uuid7 import uuid7


# entrypoint
def run(listener_uuid: str):
    while True:
        print(f"listener {listener_uuid}")
        sleep(1)
