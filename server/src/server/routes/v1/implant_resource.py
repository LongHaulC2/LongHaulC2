from ...instance import env_config, app, api
from flask_restx import Resource, Namespace, fields
from ...utils.response import APIResponse
from ...modules.mysql_functions import ImplantService, ImplantCreate
from ...db.mysql_connector import get_mysql_engine, get_mysql_session
import logging 
implants_ns = Namespace("implants", description="Implant related operations")

api_logger = logging.getLogger("api")
server_logger = logging.getLogger("server")

# Implant list
class Implants(Resource):
    # gets all  implants
    @implants_ns.doc(
        summary="Get all implants",
        description="Retrieve all implants the server knows about."
    )
    def get(self):
        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            implants = implant_service.get_all()
            data = [i.to_dict() for i in implants]
            
        api_response = APIResponse(            
            status=200,
            message="Success",
            data=data,
        )
        return api_response.jsonify()
        
    # create an implant in DB
    @implants_ns.doc(
        summary="Create a new implant entry.",
        description="Create a new implant entry. Returns an Implant ID to use with that implant"
    )
    def post(self): 
        '''
        1. Gets a MYSQL Session

        2. Creates a new record in the 'implants' table

        3. Returns ID of new record in response

        Note: This will create "ghost" sessions with no metadata. Metadata gets updated when 'PUT /v1/api/implants/{id}/' is called.
        '''
        # get a seession
        with get_mysql_session() as session:
            implant_service = ImplantService(session)
            #data = ImplantCreate(notes="TESTNOTES")
            data = ImplantCreate()
            implant_object = implant_service.create(data)
            implant_id = implant_object.id

        # need to get ID from DB
        data = {"id":implant_id}

        api_response = APIResponse(            
            status=200,
            message="Implant created",
            data=data,
        )

        return api_response.jsonify()

# individual implaant
class Implant(Resource):
    @implants_ns.doc(
        summary="Get implant",
        description="[Not Implemented] Retrieve a single implant by its unique ID.",
        params={'id': {'description': 'Agent ID (64-bit integer)','in': 'path'}}
    )
    def get(self, id): ...  # get one implant

    @implants_ns.doc(
        summary="Update implant",
        description="[Not Implemented] Update a single implant by its unique ID.",
        params={'id': {'description': 'Agent ID (64-bit integer)','in': 'path'}}
    )
    def put(self, id): ...  # update one implant based on ID

    @implants_ns.doc(
        summary="Delete implant",
        description="[Not Implemented] Delete a single implant by its unique ID.",
        params={'id': {'description': 'Agent ID (64-bit integer)','in': 'path'}}
    )
    def delete(self, id): ...  # delete one implant based on ID


# Add the HelloWorld resource to the API
implants_ns.add_resource(Implants, "/")
implants_ns.add_resource(Implant, "/<int:id>")

api.add_namespace(implants_ns)
