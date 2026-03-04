"""
services.py — ADK Service Registry Overrides for `remote_a2a` agents directory.

This file is auto-loaded by `adk api_server` when it starts from the `remote_a2a`
directory (as specified by `load_services_module(agents_dir=...)`).

It registers a Windows-compatible `file://` artifact service factory that
correctly handles absolute Windows paths like `file:///D:/foo/bar`.
"""
import platform
import urllib.parse
import logging

from google.adk.cli.service_registry import get_service_registry
from google.adk.artifacts import file_artifact_service

logger = logging.getLogger(__name__)


def _create_artifact_service_windows(uri: str, **kwargs):
    """
    Windows-compatible factory for file:// artifact URIs.

    Fixes the issue where urlparse('file:///D:/foo').path == '/D:/foo'
    which is invalid on Windows. We strip that leading slash to get 'D:/foo'.
    """
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme != "file":
        return None

    path_str = parsed.path
    # On Windows, file:///D:/foo → path='/D:/foo', so strip the leading slash.
    if path_str.startswith("/") and ":" in path_str:
        path_str = path_str[1:]

    logger.info("[Services] Windows file:// patch: resolved '%s' → '%s'", uri, path_str)
    return file_artifact_service.FileArtifactService(root_dir=path_str)


if platform.system() == "Windows":
    logger.info("[Services] Registering Windows artifact service patch for remote_a2a agents.")
    registry = get_service_registry()
    registry.register_artifact_service("file", _create_artifact_service_windows)
