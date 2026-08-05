import structlog
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource

from ...api_models.error import COMMON_ERRORS
from ...api_models.template import TEMPLATE_GET_RESPONSE, TEMPLATE_LIST_RESPONSE
from ...instance import api
from ...modules.template_manager.manager import TemplateManager
from ...utils.response import APIResponse

template_ns = Namespace("templates", description="Implant template operations")
api_logger = structlog.getLogger("api")


class TemplateCollection(Resource):
    @jwt_required()
    @template_ns.doc(
        summary="List all implant templates",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @template_ns.response(200, "List of templates", TEMPLATE_LIST_RESPONSE)
    @template_ns.marshal_with(TEMPLATE_LIST_RESPONSE)
    def get(self):
        """List all available implant templates from disk."""
        templates = TemplateManager.get_all()
        return APIResponse(status="200", message="Success", data=templates)


class TemplateItem(Resource):
    @jwt_required()
    @template_ns.doc(
        summary="Get a template by name",
        responses=COMMON_ERRORS,
        security="Bearer Auth",
    )
    @template_ns.response(200, "Template details", TEMPLATE_GET_RESPONSE)
    @template_ns.marshal_with(TEMPLATE_GET_RESPONSE)
    def get(self, template_name):
        """Get full details of a specific implant template."""
        template = TemplateManager.get_by_name(template_name)
        if not template:
            return APIResponse(status="404", message="Template not found", data={})
        return APIResponse(status="200", message="Success", data=template)


template_ns.add_resource(TemplateCollection, "/")
template_ns.add_resource(TemplateItem, "/<string:template_name>")
api.add_namespace(template_ns)
