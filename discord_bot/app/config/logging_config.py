"""
Logging Configuration.

Configures application-wide logging with colored console output
and file logging.
"""

import logging


class LoggingFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    # Colors
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: red + bold,
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelno, self.gray)
        fmt = "(black){asctime}(reset) (levelcolor){levelname:<8}(reset) (green){name}(reset) {message}"
        fmt = fmt.replace("(black)", self.black + self.bold)
        fmt = fmt.replace("(reset)", self.reset)
        fmt = fmt.replace("(levelcolor)", log_color)
        fmt = fmt.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(fmt, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


def setup_logging(
    name: str = "discord_bot",
    level: int = logging.INFO,
    log_file: str = "discord.log"
) -> logging.Logger:
    """
    Configure and return the application logger.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Path to log file
    
    Returns:
        Configured logger instance
    """
    log = logging.getLogger(name)
    log.setLevel(level)
    
    # Avoid adding handlers multiple times
    if log.handlers:
        return log
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(LoggingFormatter())
    log.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(
        filename=log_file,
        encoding="utf-8",
        mode="w"
    )
    file_handler.setFormatter(logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}",
        "%Y-%m-%d %H:%M:%S",
        style="{"
    ))
    log.addHandler(file_handler)
    
    return log


# Pre-configured logger instance
logger = setup_logging()

