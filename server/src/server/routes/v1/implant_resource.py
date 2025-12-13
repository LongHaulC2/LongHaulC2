from ...instance import env_config, app, api
from flask_restx import Resource, Namespace, fields
from ...utils.response import APIResponse
from ...modules.mysql_functions import ImplantService, ImplantCreate
from ...db.mysql_connector import get_mysql_engine, get_mysql_session
implants_ns = Namespace("implants", description="Implant related operations")

# Implant list
class Implants(Resource):
    # gets all  implants
    @implants_ns.doc(
        summary="Get all implants",
        description="[Not Implemented] Retrieve all implants the server knows about."
    )
    def get(self):
        response = response_generator(status=200, message="Success")
        return response

    # create an implant in DB
    @implants_ns.doc(
        summary="Create a new implant entry.",
        description="[Not Implemented] Create a new implant"
    )
    def post(self): 
        # get a seession
        with get_mysql_session() as session:
            implant = ImplantService(session)
            data = ImplantCreate(notes="TESTNOTES")
            implant.create(data)

        # need to get ID from DB
        data = {"id":1234}

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
