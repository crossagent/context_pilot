from google.adk.tools.base_toolset import BaseToolset

class RootAgentExtension(BaseToolset):
    """
    Abstract base class for extensions targeting the Root Agent (Bug Scene Agent).
    Implement this class to provide tools available to the top-level orchestrator.
    """
    pass

class BugReportExtension(BaseToolset):
    """
    Abstract base class for extensions targeting the Bug Report Agent.
    Implement this class to provide tools for bug reporting workflows.
    """
    pass
