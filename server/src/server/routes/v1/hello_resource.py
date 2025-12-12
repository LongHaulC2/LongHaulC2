from ...instance import env_config, app, api
from flask_restx import Resource


# Define a simple resource that returns "Hello, World!"
class HelloWorld(Resource):
    def get(self):
        return {"message": "Hello, World!"}


# Add the HelloWorld resource to the API
api.add_resource(HelloWorld, "/hello")
