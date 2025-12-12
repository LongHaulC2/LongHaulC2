from pathlib import Path
import logging

# Define log directory
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# Log file path
log_file = Path(log_dir) / "server.log"

# Create a logger
logger = logging.getLogger("server")
logger.setLevel(logging.DEBUG)  # Set the minimum level of logs to capture

# File handler to write logs to a file
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)  # You can adjust this level as needed

# Stream handler to output logs to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Log format (same for both handlers)
log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(log_format)
console_handler.setFormatter(log_format)

# Add both handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Log a startup message
logger.info("Server Startup")
