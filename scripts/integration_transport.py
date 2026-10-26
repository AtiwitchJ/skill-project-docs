"""Read/write transports. MCP is an explicit agent-operated JSON request bridge."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from integration_core import digest, load, save

READ_OPERATIONS = {"doctor", "list", "get", "schema", "find", "comments", "download", "artifact"}


class Pending(RuntimeError):
    """An MCP request awaits an actual agent tool call, not fabricated tool discovery."""


class Bridge:
    def __init__(self, name, config, runtime, mode, writing=False):
        self.name, self.config = name, config
        self.runtime, self.mode, self.writing = Path(runtime), mode, writing

    def call(self, operation, **payload):
        if operation not in READ_OPERATIONS and not self.writing:
            raise ValueError("external writes are only allowed by migration apply/resume")
        request = {"version": 1, "connection": self.name, "provider": self.config["provider"],
                   "operation": operation, "payload": payload}
        request_id = digest(request)
        request["request_id"] = request_id
        if self.mode == "mcp":
            response = load(self.runtime / "responses" / (request_id + ".json"))
            if response is None:
                save(self.runtime / "requests" / (request_id + ".json"), request)
                raise Pending(f"MCP request {request_id}: agent must execute the real tool and write its response in {self.runtime / 'responses'}")
        else:
            command = self.config.get("cli", [])
            if not isinstance(command, list) or not command or not all(isinstance(c, str) for c in command):
                raise ValueError("cli must be a nonempty argv array for a JSON bridge executable")
            result = subprocess.run(command, input=json.dumps(request), capture_output=True, text=True,
                                    timeout=self.config.get("timeout", 30), check=False)
            if result.returncode:
                # stderr can contain a provider token. Do not relay it into tracked logs.
                raise RuntimeError(f"CLI bridge failed with exit code {result.returncode}")
            response = json.loads(result.stdout)
        if response.get("request_id") != request_id:
            raise ValueError("bridge response does not match request")
        if response.get("error"):
            raise RuntimeError("bridge operation failed; inspect the private bridge response")
        if "result" not in response:
            raise ValueError("bridge response has no result")
        return response["result"]


def availability(config):
    command = config.get("cli", [])
    return {"mcp": bool(config.get("mcp", {}).get("enabled")),
            "cli": bool(isinstance(command, list) and command and shutil.which(command[0])),
            "api": bool(config.get("token_env") and os.environ.get(config["token_env"]))}


def select(config, locked=None):
    available = availability(config)
    mode = locked or config.get("transport", "auto")
    if mode == "auto":
        mode = next((m for m in ("mcp", "cli", "api") if available[m]), None)
    if mode not in available or not available[mode]:
        raise ValueError(f"transport {mode or 'auto'} unavailable; configure MCP bridge, CLI argv or token_env")
    return mode


def transport(name, config, runtime, writing=False, locked=None):
    mode = select(config, locked)
    if mode == "api":
        from provider_api import API
        return API(name, config, writing)
    return Bridge(name, config, runtime, mode, writing)
