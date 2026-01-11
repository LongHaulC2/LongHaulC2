import logging

server_logger = logging.getLogger("server")


# def check_type(obj, expected_type, var_name="variable"):
#     """
#     A defensive Dev helper to log type mismatches without stopping execution. Makes runtime errors easier
#     to debug
#     """
#     if not isinstance(obj, expected_type):
#         server_logger.warning(
#             f"Potential Type Mismatch [{var_name}]: "
#             f"Expected '{expected_type.__name__}', "
#             f"but got '{type(obj).__name__}'. Value: {obj}"
#         )

#     # can switch to an assert if this ever needs to fail on mismatch type


"""
This is the much more useful/stack trace version of check_type. Use for debugging, but use the above one for prod. 
This is a lot heaver on resources, etc.
"""
import inspect


def check_type(obj, expected_type, var_name="variable"):
    """
    A defensive Dev helper to log type mismatches without stopping execution.
    Logs caller context to make runtime errors easier to debug.
    """
    try:
        if not isinstance(obj, expected_type):
            frame = inspect.currentframe()
            caller = frame.f_back if frame else None

            if caller:
                func_name = caller.f_code.co_name
                file_name = caller.f_code.co_filename
                line_no = caller.f_lineno
                caller_info = f"{func_name}() @ {file_name}:{line_no}"
            else:
                caller_info = "<unknown caller>"

            server_logger.warning(
                f"Potential Type Mismatch [{var_name}]: "
                f"Expected '{getattr(expected_type, '__name__', repr(expected_type))}', "
                f"but got '{type(obj).__name__}'. Value: {obj}. "
                f"Caller: {caller_info}"
            )
    except Exception as e:
        # Never let debug helpers cause crashes
        server_logger.debug(f"check_type inspection failed: {e}")
