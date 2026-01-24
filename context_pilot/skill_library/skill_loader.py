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

    def load_skills(self) -> None:
        """
        Scans and imports packages from the skill directory.
        Standard Python import mechanism triggers __init__.py, where registration happens.
        """
        if not os.path.exists(self.skill_path):
            logger.warning(f"Skill path does not exist: {self.skill_path}")
            return

        logger.info(f"Loading skills from: {self.skill_path}")
        
        # 1. Add skill directory to sys.path to allow imports
        # We use a context manager approach or just insert/remove, but for a server run, 
        # keeping it in path is usually fine if we don't expect conflicts.
        # To be safe and clean, we append.
        if self.skill_path not in sys.path:
            sys.path.insert(0, self.skill_path)
            
        # 2. Iterate and Import
        try:
             # Only scan top-level directories or files in the skill folder
            for item in os.listdir(self.skill_path):
                full_path = os.path.join(self.skill_path, item)
                module_name = None
                
                # Case A: Directory (Package) -> Check for __init__.py
                if os.path.isdir(full_path):
                    if os.path.exists(os.path.join(full_path, "__init__.py")):
                        module_name = item
                
                # Case B: Single File Module -> .py file
                elif os.path.isfile(full_path) and item.endswith(".py") and item != "__init__.py":
                    module_name = os.path.splitext(item)[0]
                    
                if module_name:
                    try:
                        importlib.import_module(module_name)
                        logger.info(f"[SkillLoader] Successfully loaded skill module/package: {module_name}")
                    except Exception as e:
                        logger.error(f"[SkillLoader] Failed to load skill {module_name}: {e}")
                        
        except Exception as e:
             logger.error(f"[SkillLoader] Critical error scanning skills: {e}")




