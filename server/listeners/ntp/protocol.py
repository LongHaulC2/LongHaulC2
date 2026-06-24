import struct
from ctypes import BigEndianStructure, c_int8, c_uint8, c_uint32, c_uint64


class NtpPacket(BigEndianStructure):
    # basic NTP packet outline, without extensions.
    _fields_ = [
        ("LI", c_uint8, 2),  # fyi - this is in BITS, not bytes :)
        ("VN", c_uint8, 3),
        ("Mode", c_uint8, 3),
        # Bytes 1-3
        ("Stratum", c_uint8),
        ("Poll", c_int8),  # RFC specifies signed 8-bit
        ("Precision", c_int8),  # RFC specifies signed 8-bit
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
        # ("ImplantUUID", c_uint8 * 16), # implant uuid7 - 16 byte field.
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
            padded_payload = ext_payload + (b"\x00" * padding_needed)

            # Calculate length and pack header
            total_len = 4 + len(padded_payload)
            ext_header = struct.pack(">HH", field_type, total_len)

            # Append this specific extension to the bytearray
            final_packet.extend(ext_header)
            final_packet.extend(padded_payload)

        return bytes(final_packet)

    @staticmethod
    def parse_extensions(raw_data: bytes) -> dict[int, bytes]:
        """
        Extracts all NTP extensions appended after the 48-byte base header.

        Args:
            raw_data: The completely raw incoming UDP packet bytes.

        Returns:
            dict: Mapping of {field_type (int): payload (bytes)}
        """
        extensions = {}

        # Base NTP header is strictly 48 bytes.
        # Anything after that is an extension (or a MAC).
        offset = 48

        # We need at least 4 bytes to read the (Type, Length) header
        while offset + 4 <= len(raw_data):
            # Unpack the 4-byte extension header (Big Endian: unsigned short, unsigned short)
            ext_type, ext_len = struct.unpack(">HH", raw_data[offset : offset + 4])

            # RFC 5906 Sanity Checks:
            # 1. Minimum length for an extension is 8 bytes (4 header + 4 data)
            # 2. Length must be padded to a multiple of 4
            # 3. The stated length cannot exceed the remaining bytes in the packet
            if ext_len < 8 or ext_len % 4 != 0 or offset + ext_len > len(raw_data):
                # We either hit a malformed packet, or we hit a trailing MAC signature.
                # Stop parsing extensions.
                break

            # Extract the payload (skipping the 4-byte header)
            payload = raw_data[offset + 4 : offset + ext_len]

            extensions[ext_type] = payload

            # Move our pointer to the start of the next potential extension
            offset += ext_len

        return extensions
