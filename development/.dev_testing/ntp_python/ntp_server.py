from ctypes import BigEndianStructure, c_uint8, c_int8, c_uint32, c_uint64
import struct
# /*
# * 
# * NTP Packet Reference

#  *    Byte     | Length | Field Name              | Description
#  * ------------|--------|-------------------------|-----------------------------------------------------
#  *      0      |   1    | LI | VN | Mode          | Leap Indicator (2 bits), Version (3 bits), Mode (3 bits)
#  *      1      |   1    | Stratum                 | Stratum level of the local clock
#  *      2      |   1    | Poll                    | Max interval between messages (log2 seconds)
#  *      3      |   1    | Precision               | Precision of local clock (log2 seconds)

#  *      4      |   4    | Root Delay              | Total round trip delay to the reference clock (signed 16.16 fixed-point)
#  *      8      |   4    | Root Dispersion         | Nominal error relative to the reference clock (unsigned 16.16 fixed-point)
#  *     12      |   4    | Reference ID            | Reference clock identifier (IP, ASCII, or KISS code)

#  *     16      |   8    | Reference Timestamp     | Time when the system clock was last set or corrected
#  *     24      |   8    | Originate Timestamp     | Time request departed the client for the server
#  *     32      |   8    | Receive Timestamp       | Time request arrived at the server
#  *     40      |   8    | Transmit Timestamp      | Time reply departed the server for client
 

#  * LI (Leap Indicator): Warns of impending leap second (00 = no warning)
#  * VN (Version Number): NTP version (e.g., 4 for NTPv4)
#  * Mode: 3 = client, 4 = server, 5 = broadcast, etc.

#  * Stratum:
#  *   0 = unspecified or invalid
#  *   1 = primary server (e.g., GPS, atomic clock)
#  *   2-15 = secondary server
#  *   16+ = reserved

#  * Timestamps (64-bit):
#  *   First 32 bits: seconds since Jan 1, 1900 (NTP epoch)
#  *   Last 32 bits: fractional seconds

# */

class ProtocolHeader(BigEndianStructure):
    # basic NTP packet outline, without extensions.
    _fields_ = [ 
        ("LI", c_uint8, 2),# fyi - this is in BITS, not bytes :)
        ("VN", c_uint8, 3),
        ("Mode", c_uint8, 3),
        
        # Bytes 1-3
        ("Stratum", c_uint8),
        ("Poll", c_int8),      # RFC specifies signed 8-bit
        ("Precision", c_int8), # RFC specifies signed 8-bit
        
        # Bytes 4-15
        ("RootDelay", c_uint32),
        ("RootDispersion", c_uint32),
        ("ReferenceID", c_uint32),
        
        # Bytes 16-47 (64-bit Timestamps)
        ("ReferenceTimestamp", c_uint64),
        ("OriginateTimestamp", c_uint64),
        ("ReceiveTimestamp", c_uint64),
        ("TransmitTimestamp", c_uint64),
        # extension fields:
        #("ImplantUUID", c_uint8 * 16), # implant uuid7 - 16 byte field.
        # each extension field is:
        # 4 bytes for overhead (2 field type, 2 length)
        # X bytes for data (up to 65532 bytes)
    ]

    def with_extensions(self, extensions: list[tuple[int, bytes]]) -> bytes:
        """
        Serializes the base header and appends multiple NTP extensions.
        
        Args:
            extensions: A list of tuples containing (field_type, payload).
                        Example: [(0x1337, b'uuid_data...'), (0x1338, b'other_data')]

        Returns:
            bytes: The complete, ready-to-send raw packet.
        """
        # Start with the pure 48-byte C-struct memory block
        final_packet = bytearray(bytes(self))
        
        # Iterate through all extensions and append them sequentially
        for field_type, ext_payload in extensions:
            # Pad payload to 4-byte boundary
            padding_needed = (4 - (len(ext_payload) % 4)) % 4
            padded_payload = ext_payload + (b'\x00' * padding_needed)
            
            # Calculate length and pack header
            total_len = 4 + len(padded_payload)
            ext_header = struct.pack('>HH', field_type, total_len)
            
            # Append this specific extension to the bytearray
            final_packet.extend(ext_header)
            final_packet.extend(padded_payload)
            
        return bytes(final_packet)

# Simulating an incoming raw byte packet
# Real NTP Server Response (48 bytes)
raw_ntp_packet = (
    b'\x24\x02\x04\xef'  # LI/VN/Mode, Stratum, Poll, Precision
    b'\x00\x00\x00\x00'  # Root Delay
    b'\x00\x00\x00\x0b'  # Root Dispersion
    b'\x4e\x49\x53\x54'  # Reference ID ("NIST")
    b'\xde\x4a\xc9\xd1\x2d\xec\xcc\xc0'  # Reference Timestamp
    b'\xde\x4a\xcb\x56\xc2\xdb\xd5\x00'  # Originate Timestamp
    b'\xde\x4a\xcb\x56\xc3\xd2\xf0\x00'  # Receive Timestamp
    b'\xde\x4a\xcb\x56\xc3\xd3\x1c\x00'  # Transmit Timestamp
)
# # "Cast" the bytes to the struct/turn it into an object
# header = ProtocolHeader.from_buffer_copy(raw_ntp_packet)

# for field_name in header._fields_:
#         print(f"{field_name[0]}:{field_name[1]}")

# if len(raw_ntp_packet) > 48:
#       print("Packet extensions found")

# Convert back to bytes to send
#out_bytes = bytes(header)

# server impl

import socket
import threading

def process_udp_packet(server_socket, raw_data, client_address):
    """Parses the packet and sends a response back to the client."""
    print(f"[Worker] Processing {len(raw_data)} bytes from {client_address}")
    
    # handle incoming packet...

    # placeholder response packet
    response_packet = ProtocolHeader.from_buffer_copy(raw_data)
    for field_name in response_packet._fields_:
        print(f"{field_name[0]}:{field_name[1]}")


    # Send directly back to the client address using the main server socket
    server_socket.sendto(response_packet, client_address)

def start_udp_server(host='0.0.0.0', port=123): # Port 123 is standard NTP
    # AF_INET = IPv4, SOCK_DGRAM = UDP
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((host, port))
    print(f"[*] UDP Server listening on {host}:{port}")

    try:
        while True:
            # Blocks until ANY packet arrives on this port
            raw_data, client_address = server.recvfrom(1024)
            
            # For high throughput, immediately hand off to a thread so the 
            # main loop can get back to recvfrom() instantly.
            threading.Thread(
                target=process_udp_packet,
                args=(server, raw_data, client_address),
                daemon=True
            ).start()
            
    except KeyboardInterrupt:
        print("\n[*] Shutting down server.")
    finally:
        server.close()

if __name__ == "__main__":
    start_udp_server(port=9999) # Using 9999 for testing so you don't need sudo