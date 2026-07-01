"""Shared AppKey definitions for the web module."""

from aiohttp import web

START_TIME = web.AppKey("start_time", float)
HOST = web.AppKey("host", str)
PORT = web.AppKey("port", int)
