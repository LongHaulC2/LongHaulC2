import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog

# SETUP DIRECTORIES
log_dir = Path("/var/log/longhaulc2/server/")
log_dir.mkdir(parents=True, exist_ok=True)

# SHARED PROCESSORS
# These run for EVERY log entry, regardless of where it goes.
shared_processors = [
    structlog.contextvars.merge_contextvars,  # Async context (IP, UUID)
    structlog.stdlib.add_logger_name,  # Adds "logger": "api"
    structlog.stdlib.add_log_level,  # Adds "level": "info"
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
    structlog.stdlib.ExtraAdder(),  # allows for kwarg args in logs
]

# CONFIGURE STRUCTLOG BACKEND
structlog.configure(
    processors=shared_processors
    + [
        # Prepare the event dict so the stdlib Formatter can render it
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# DEFINE FORMATTERS
# Both use ConsoleRenderer now.

# Console: Colors = True (Pretty for Terminal)
console_formatter = structlog.stdlib.ProcessorFormatter(
    processor=structlog.dev.ConsoleRenderer(colors=True),
    foreign_pre_chain=shared_processors,
)

# File: Colors = False (Exact same text layout, just no ANSI color codes)
file_formatter = structlog.stdlib.ProcessorFormatter(
    processor=structlog.dev.ConsoleRenderer(colors=False),
    foreign_pre_chain=shared_processors,
)


# BUILD LOGGERS
def setup_logger(name, filename):
    """
    Configures a logger to write to a specific file and the console.
    """
    # Create File Handler
    file_handler = RotatingFileHandler(log_dir / filename, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Create Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    # Configure the Standard Library Logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if imported multiple times
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    logger.propagate = False

    # Return a structlog-wrapped version
    return structlog.wrap_logger(logger)


# EXPORT LOGGERS
api_logger = setup_logger("api", "api.log")
server_logger = setup_logger("server", "server.log")
listener_logger = setup_logger("listener", "listener.log")
# needed to change name from neo4j -> internal_neo4j, otherwise it picks up neo4j logs from neomodel
neo4j_logger = setup_logger("internal_neo4j", "neo4j.log")
response_pipeline_logger = setup_logger("response_pipeline", "response_pipeline.log")
