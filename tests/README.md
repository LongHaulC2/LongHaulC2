# Running:
1. Start server
2. Run server tests: `make server_tests` — all should pass green, tests just the API functionality
3. Run UI tests: `make web_tests` — all should pass (no server needed)
4. Run everything: `make local_tests`
Confirm integration tests still work: `make no_fail_test` (existing target unchanged)

Note - Do not need an implant for these tests
Note - These are contained in the main makefile