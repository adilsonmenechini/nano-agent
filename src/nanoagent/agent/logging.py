from __future__ import annotations

import logging
import sys
from enum import IntEnum
from typing import TextIO


class LogLevel(IntEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    SILENT = logging.CRITICAL + 1


_VERBOSITY_MAP: dict[int, LogLevel] = {
    0: LogLevel.WARNING,
    1: LogLevel.INFO,
    2: LogLevel.DEBUG,
}

_loggers: dict[str, AgentLogger] = {}


class AgentLogger:
    _instance: AgentLogger | None = None

    def __init__(self, name: str = "nanoagent", level: LogLevel = LogLevel.INFO, stream: TextIO | None = None) -> None:
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level.value)
        self._logger.handlers.clear()
        handler = logging.StreamHandler(stream or sys.stderr)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
        handler.setLevel(level.value)
        self._logger.addHandler(handler)
        self._level = level

    @classmethod
    def get(cls, name: str = "nanoagent") -> AgentLogger:
        if name not in _loggers:
            _loggers[name] = AgentLogger(name=name)
        return _loggers[name]

    @classmethod
    def configure(cls, verbosity: int = 0, name: str = "nanoagent") -> AgentLogger:
        level = _VERBOSITY_MAP.get(verbosity, LogLevel.WARNING)
        logger = AgentLogger(name=name, level=level)
        _loggers[name] = logger
        return logger

    @property
    def level(self) -> LogLevel:
        return self._level

    def debug(self, msg: str, *args: object) -> None:
        self._logger.debug(msg, *args)

    def info(self, msg: str, *args: object) -> None:
        self._logger.info(msg, *args)

    def warning(self, msg: str, *args: object) -> None:
        self._logger.warning(msg, *args)

    def error(self, msg: str, *args: object) -> None:
        self._logger.error(msg, *args)

    def state_transition(self, from_state: str, to_state: str, reason: str) -> None:
        self._logger.info("STATE %s -> %s (%s)", from_state, to_state, reason)

    def tool_call(self, name: str, args: dict) -> None:
        self._logger.debug("TOOL %s args=%s", name, args)

    def llm_request(self, model: str, tokens: int) -> None:
        self._logger.debug("LLM %s %d tokens", model, tokens)

    def turn_complete(self, response: str, duration_ms: int) -> None:
        self._logger.info("Turn completed in %dms — response: %s chars", duration_ms, len(response))
