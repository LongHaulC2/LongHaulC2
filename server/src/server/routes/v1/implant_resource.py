from ...instance import env_config, app, api
from flask_restx import Resource, Namespace


implants_ns = Namespace("implants", description="Implants related operations")


# Implant list
class Implants(Resource):
    # gets all  implants
    def get(self):
        return {"message": "Hello, World!"}

    # create an implant in DB
    def post(self): ...


# individual implaant
class Implant(Resource):
    def get(self, id): ...  # get one implant

    def put(self, id): ...  # update one implant based on ID

    def delete(self, id): ...  # delete one implant based on ID


# Add the HelloWorld resource to the API
implants_ns.add_resource(Implants, "/")
implants_ns.add_resource(Implant, "/<int:id>")

api.add_namespace(implants_ns)
