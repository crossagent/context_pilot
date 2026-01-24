from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools import BaseTool
from typing import List, Optional

class DynamicToolset(BaseToolset):
    """
    A Toolset that allows dynamic registration of tools at runtime.
    This acts as a global registry for skills to inject themselves into.
    """
    def __init__(self, prefix: Optional[str] = None):
        super().__init__(tool_name_prefix=prefix)
        self._tools: List[BaseTool] = []

    def add_tool(self, tool: BaseTool):
        """Dynamically registers a new tool to this toolset."""
        self._tools.append(tool)

    async def get_tools(self, readonly_context=None) -> List[BaseTool]:
        """Returns the currently registered tools."""
        return self._tools

# --- Global Registries ---
# Agents will include these registries in their static tool lists.
# Skills will import these registries and call .add_tool() at import time.

root_skill_registry = DynamicToolset()
report_skill_registry = DynamicToolset()
analyze_skill_registry = DynamicToolset()
