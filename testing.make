API_URL := http://10.0.0.30:4504
SWAGGER_URL := $(API_URL)/swagger.json

.PHONY: test-contract benchmark

test-contract:
	@echo "Running Schemathesis API fuzzing..."
	# This pulls the OpenAPI spec from Flask-RESTX and tests all endpoints
	schemathesis run $(SWAGGER_URL) --checks all

benchmark:
	@echo "Benchmarking Core API Endpoints..."
	# Testing the health check 
	hey -n 500 -c 50 $(API_URL)/api/v1/health/
	@echo "--------------------------------------------------------"
	# Testing the implants endpoint (DB read-heavy)
	hey -n 200 -c 20 $(API_URL)/api/v1/implants/