import logging

server_logger = logging.getLogger("server")


def check_type(obj, expected_type, var_name="variable"):
    """
    A defensive Dev helper to log type mismatches without stopping execution. Makes runtime errors easier
    to debug
    """
    if not isinstance(obj, expected_type):
        server_logger.warning(
            f"Potential Type Mismatch [{var_name}]: "
            f"Expected '{expected_type.__name__}', "
            f"but got '{type(obj).__name__}'. Value: {obj}"
        )

    # can switch to an assert if this ever needs to fail on mismatch type
