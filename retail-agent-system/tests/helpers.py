"""Helpers for invoking @function_tool-decorated tools in tests."""
import asyncio
import json

from agents import FunctionTool
from agents.tool_context import ToolContext


def call_tool(tool: FunctionTool, *args, **kwargs):
    """Invoke a FunctionTool the way the Agents SDK does at runtime.

    @function_tool replaces the function with a FunctionTool object, so it can't
    be called directly. Positional args are mapped to parameter names in
    signature order (the order of the tool's JSON schema properties).
    """
    param_names = list(tool.params_json_schema.get("properties", {}))
    if len(args) > len(param_names):
        raise TypeError(f"{tool.name}() takes {len(param_names)} arguments, got {len(args)}")
    arguments = {**dict(zip(param_names, args)), **kwargs}

    payload = json.dumps(arguments)
    ctx = ToolContext(
        context=None,
        tool_name=tool.name,
        tool_call_id="test-call",
        tool_arguments=payload,
    )
    return asyncio.run(tool.on_invoke_tool(ctx, payload))
