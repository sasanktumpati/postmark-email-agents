import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


class AppLogger:
    _instance: Optional["AppLogger"] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls) -> "AppLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is None:
            self._setup_logger()

    def _setup_logger(self) -> None:
        self._logger = logging.getLogger("email-agents")
        self._logger.setLevel(logging.DEBUG)

        if self._logger.handlers:
            return

        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)

        error_handler = logging.handlers.RotatingFileHandler(
            filename=log_dir / "errors.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=10,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)

        security_handler = logging.handlers.RotatingFileHandler(
            filename=log_dir / "security.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=15,
            encoding="utf-8",
        )
        security_handler.setLevel(logging.INFO)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        detailed_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        security_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | SECURITY | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        simple_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S"
        )

        file_handler.setFormatter(detailed_formatter)
        error_handler.setFormatter(detailed_formatter)
        security_handler.setFormatter(security_formatter)
        console_handler.setFormatter(simple_formatter)

        self._logger.addHandler(file_handler)
        self._logger.addHandler(error_handler)
        self._logger.addHandler(console_handler)

        self._security_handler = security_handler

        self._logger.info(
            "Logger initialized successfully with separate error and security logs"
        )

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def security_logger(self) -> logging.Logger:
        security_logger = logging.getLogger("email-agents.security")
        if not security_logger.handlers:
            security_logger.addHandler(self._security_handler)
            security_logger.setLevel(logging.INFO)
            security_logger.propagate = False
        return security_logger

    def set_level(self, level: str) -> None:
        """
        Set the logging level.

        Args:
            level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        """
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        if level.upper() in level_map:
            self._logger.setLevel(level_map[level.upper()])
            self._logger.info(f"Log level set to {level.upper()}")
        else:
            self._logger.warning(f"Invalid log level: {level}")

    def add_file_handler(self, filename: str, level: str = "DEBUG") -> None:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        handler = logging.handlers.RotatingFileHandler(
            filename=log_dir / filename,
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )

        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        handler.setLevel(level_map.get(level.upper(), logging.DEBUG))

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

        self._logger.addHandler(handler)
        self._logger.info(f"Added additional file handler: {filename}")


_app_logger = AppLogger()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    if name:
        return _app_logger.logger.getChild(name)
    return _app_logger.logger


def get_security_logger() -> logging.Logger:
    return _app_logger.security_logger


def set_log_level(level: str) -> None:
    _app_logger.set_level(level)


def add_log_file(filename: str, level: str = "DEBUG") -> None:
    _app_logger.add_file_handler(filename, level)


def debug(message: str, *args, **kwargs) -> None:
    _app_logger.logger.debug(message, *args, **kwargs)


def info(message: str, *args, **kwargs) -> None:
    _app_logger.logger.info(message, *args, **kwargs)


def warning(message: str, *args, **kwargs) -> None:
    _app_logger.logger.warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs) -> None:
    _app_logger.logger.error(message, *args, **kwargs)


def critical(message: str, *args, **kwargs) -> None:
    _app_logger.logger.critical(message, *args, **kwargs)


def exception(message: str, *args, **kwargs) -> None:
    _app_logger.logger.exception(message, *args, **kwargs)


def log_api_access(
    ip: str,
    user_id: str,
    api_key_truncated: str,
    method: str,
    endpoint: str,
    status: str = "SUCCESS",
) -> None:
    security_logger = get_security_logger()
    security_logger.info(
        "API_ACCESS | Status: %s | IP: %s | User: %s | API_Key: %s | Request: %s %s",
        status,
        ip,
        user_id,
        api_key_truncated,
        method,
        endpoint,
    )


def log_auth_event(
    event_type: str,
    ip: str,
    api_key_truncated: str,
    user_id: Optional[str] = None,
    details: str = "",
) -> None:
    security_logger = get_security_logger()
    security_logger.info(
        "AUTH_EVENT | Type: %s | IP: %s | API_Key: %s | User: %s | Details: %s",
        event_type,
        ip,
        api_key_truncated,
        user_id or "UNKNOWN",
        details,
    )
