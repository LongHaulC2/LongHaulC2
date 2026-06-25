import base64
import io

import structlog
from edwh_uuid7 import uuid7
from flask import request, send_file
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from werkzeug.exceptions import abort

from ...api_models.error import COMMON_ERRORS
from ...api_models.filestore import FILE_GET_RESPONSE, FILE_POST_INPUT, FILE_POST_RESPONSE, FILEACTIONS_DELETE_RESPONSE
from ...db.mysql_connector import get_mysql_session
from ...db.mysql_functions import MySQLImplantFileService
from ...instance import api
from ...utils.checks import check_type
from ...utils.response import APIResponse

file_store_ns = Namespace("filestore", description="Filestore related operations")
api_logger = structlog.getLogger("api")
server_logger = structlog.getLogger("server")


# GET /filestore - all files in list
# POST /filestore - add new file
class File(Resource):
    @file_store_ns.doc(
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @file_store_ns.expect(FILE_POST_INPUT, validate=True)  # flip to True to enforce
    @file_store_ns.response(200, "File uploaded", FILE_POST_RESPONSE)
    @file_store_ns.marshal_with(FILE_POST_RESPONSE)
    @jwt_required()
    def post(self):
        """
        Upload a new file to the filestore
        """

        data = file_store_ns.payload

        file_name = data.get("file_name")
        # file_bytes = data.get("file_bytes")
        file_contents_b64 = data.get("file_contents")

        if not file_name or not file_contents_b64:
            abort(400, "Missing required data")

        file_bytes = base64.b64decode(file_contents_b64)

        file_uuid = str(uuid7())

        with get_mysql_session() as session:
            file_service = MySQLImplantFileService(session)
            # snag UUID
            file_uuid = file_service.register_file(file_name=file_name, file_bytes=file_bytes, file_uuid=file_uuid)

        response = {"file_uuid": file_uuid}
        # Return immediately
        return APIResponse(status="200", message="File uploaded successfully", data=response)

    @file_store_ns.doc(
        summary="Get all files",
        description="Get a list of all files in the Database",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @file_store_ns.response(200, "List of files", FILE_GET_RESPONSE)
    @file_store_ns.marshal_with(FILE_GET_RESPONSE)
    @jwt_required()
    def get(self):  # get one implant
        """
        Get a list of all files in the Database
        """
        ip = request.remote_addr

        api_logger.info("Getting all files", caller_ip=ip)

        # sql call to get implant data, return it as a dict (including bin data)
        with get_mysql_session() as session:
            ips = MySQLImplantFileService(session)

            data = ips.get_all_files()

        return APIResponse(status="200", message="Success", data=data)


# GET /filestore/uuid: Get singular file
# DELETE /filestore/uuid: Delete singular binary
# note: Bins shuold be stored in the DB, as a binary/blob field
class FileActions(Resource):
    @file_store_ns.doc(
        summary="Download a file",
        description="Downloads a single file",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @file_store_ns.produces(["application/octet-stream"])
    @file_store_ns.response(
        200,
        "Binary File Stream",
        headers={"Content-Disposition": "attachment; filename=file.bin"},
    )
    @jwt_required()
    @file_store_ns.response(404, "Payload Not Found")
    def get(self, file_uuid):
        """
        Download a specific file artifact, based on the provided uuid
        """
        ip = request.remote_addr

        # Validation
        check_type(file_uuid, str, "file_uuid")

        api_logger.info(
            "Download requested for file_uuid",
            file_uuid=file_uuid,
            caller_ip=ip,
        )

        # Fetch Data
        with get_mysql_session() as session:
            service = MySQLImplantFileService(session)
            file: bytes | None = service.get_file_by_uuid(file_uuid)

            if not file:
                api_logger.warning("Payload not found", file_uuid=file_uuid)
                return APIResponse(status="404", message="File not found")

            # Serve File
            # We wrap the bytes in BytesIO so Flask can treat it like a file
            return send_file(
                io.BytesIO(file.file_bytes),
                mimetype="application/octet-stream",
                as_attachment=True,
                download_name=file.file_name or f"{file.file_hash}.bin",
            )

    @file_store_ns.doc(
        summary="Delete a file",
        description="Deletes a single file",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @file_store_ns.response(200, "Deletion Successful", FILEACTIONS_DELETE_RESPONSE)
    @file_store_ns.response(404, "File Not Found")
    @file_store_ns.marshal_with(FILEACTIONS_DELETE_RESPONSE)
    @jwt_required()
    def delete(self, file_uuid):
        """
        Delete a specific file artifact, based on the provided uuid

        """
        ip = request.remote_addr

        api_logger.info("Getting file", file_uuid=file_uuid, caller_ip=ip)
        check_type(file_uuid, str, "file_uuid")

        with get_mysql_session() as session:
            file_service = MySQLImplantFileService(session)
            file_service.delete_file(file_uuid=file_uuid)

        return APIResponse(
            status="200",
            message="Success",
        )

    # need a post for new


file_store_ns.add_resource(File, "/")
file_store_ns.add_resource(FileActions, "/<string:file_uuid>")

api.add_namespace(file_store_ns)
