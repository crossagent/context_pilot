import os
import sys
import uuid
import importlib.util
import importlib.machinery
import logging
from typing import List, Optional, Type, Dict, Any
from google.adk.tools import FunctionTool, BaseTool
from google.adk.tools.base_toolset import BaseToolset
import yaml

logger = logging.getLogger(__name__)

class SkillLoader:
    def __init__(self, skill_path: str):
        self.skill_path = skill_path
        # Store loaded extension instances by their class type
        # Key: The BaseToolset subclass type (interface)
        # Value: List of instantiated objects implementing that interface
        self.loaded_extensions: Dict[Type[BaseToolset], List[BaseToolset]] = {}

    def load_extensions(self, target_interfaces: List[Type[BaseToolset]]) -> None:
        """
        Scans and imports modules, finding instances of the specified target interfaces.
        """
        if not os.path.exists(self.skill_path):
            logger.warning(f"Skill path does not exist: {self.skill_path}")
            return

        # Initialize storage for targeted types
        for interface in target_interfaces:
            if interface not in self.loaded_extensions:
                self.loaded_extensions[interface] = []

        # Recursively search for .py files
        for root, dirs, files in os.walk(self.skill_path):
             for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    module_path = os.path.join(root, file)
                    self._load_module_and_extract(module_path, target_interfaces)

    def _load_module_and_extract(self, module_path: str, target_interfaces: List[Type[BaseToolset]]):
        module_name = f"skill_module_{uuid.uuid4().hex}"
        try:
            # 1. Load Module
            loader = importlib.machinery.SourceFileLoader(module_name, module_path)
            spec = importlib.util.spec_from_loader(loader.name, loader)
            if not spec or not spec.loader:
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 2. Inspect Module Content
            for name in dir(module):
                obj = getattr(module, name)
                
                # Check against all registered interfaces
                for interface in target_interfaces:
                    # We look for INSTANCES of the interface (e.g. instantiated toolsets)
                    # Note: We skip the interface definition itself if it happens to be imported
                    if isinstance(obj, interface):
                        logger.info(f"Loaded extension '{name}' implementing {interface.__name__} from {module_path}")
                        self.loaded_extensions[interface].append(obj)
                        
        except Exception as e:
            logger.error(f"Failed to load module {module_path}: {e}")

    def get_extensions_by_type(self, interface_type: Type[BaseToolset]) -> List[BaseToolset]:
        """
        Retrieve all loaded extensions that implement the specified interface.
        """
        return self.loaded_extensions.get(interface_type, [])



