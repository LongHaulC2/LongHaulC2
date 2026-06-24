# Scripting Overview


LongHaul allows for automation/scripting of C2 operations in the form of a RESTful API Interface. It enables operators to programmatically manage nearly everything offered by the platform.

The API is structured around three core operational categories:

* **Build Operations:** Endpoints for initiating, monitoring, and retrieving asynchronous payload compilation tasks.
* **Implant Operations:** Endpoints for tracking active agents, querying check-in history, and queuing tasks or commands for execution on target systems.
* **Listener Operations:** Endpoints for spawning, configuring, and terminating network listeners using malleable C2 profiles.

All endpoints utilize standard HTTP methods and return standardized JSON responses, facilitating predictable error handling and integration with external Python scripts or automation frameworks.

See the full API reference docs here: [API Docs](https://longhaulc2.github.io/api)

## Getting started:

... api at...

...example request...
