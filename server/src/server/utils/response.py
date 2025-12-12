from flask import jsonify
import logging

api_logger = logging.getLogger("api")


def response_generator(
    status,
    message,
    data=None,
    errors=None,
    pagination=None,
    code=None,
    documentation_url=None,
):
    """
    Generate a standardized API response in the Microsoft-style format.

    :param status: 'success' or 'error' to indicate the response status.
    :param message: Human-readable message indicating the result.
    :param data: The actual data to be returned, if applicable (default: None).
    :param errors: Detailed errors, if any (default: None).
    :param pagination: Pagination details if the data is a list (default: None).
    :param code: Optional error code for detailed error identification (default: None).
    :param documentation_url: URL for error documentation (default: None).

    :return: A Flask `jsonify` response object.
    """

    response = {
        "status": status,
        "message": message,
        "data": data,
        # "pagination": pagination,
        "errors": errors,
        "code": code,
        "documentation_url": documentation_url,
    }

    # Clean up the response to remove any keys that are None
    response = {key: value for key, value in response.items() if value is not None}

    api_logger.debug(f"Generating Response: {response}")

    return jsonify(response)
