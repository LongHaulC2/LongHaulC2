from pathlib import Path
import logging

# Define log directory
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# Log file paths for server and API
server_log_file = log_dir / "server.log"
api_log_file = log_dir / "api.log"

# Create separate loggers for server and api
server_logger = logging.getLogger("server")
api_logger = logging.getLogger("api")

# Set log level for each logger
server_logger.setLevel(logging.DEBUG)
api_logger.setLevel(logging.DEBUG)

# File handler to write server logs to a file
server_file_handler = logging.FileHandler(server_log_file, encoding="utf-8")
server_file_handler.setLevel(logging.DEBUG)

# File handler to write API logs to a separate file
api_file_handler = logging.FileHandler(api_log_file, encoding="utf-8")
api_file_handler.setLevel(logging.DEBUG)

# Stream handler to output logs to the console (same for both loggers)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Log format (same for both handlers)
log_format = logging.Formatter("[%(asctime)s] %(name)s - %(levelname)s - %(message)s")
server_file_handler.setFormatter(log_format)
api_file_handler.setFormatter(log_format)
console_handler.setFormatter(log_format)

# Add the handlers to the respective loggers
server_logger.addHandler(server_file_handler)
server_logger.addHandler(console_handler)

api_logger.addHandler(api_file_handler)
api_logger.addHandler(console_handler)

# Log a startup message for server
server_logger.info("Server Startup")

# Example API logging
# api_logger.info("API Endpoint '/login' was accessed")
