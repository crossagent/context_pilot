import os
import yaml
import glob
import logging
import importlib.util
from typing import List, Dict, Any, Optional
from google.adk.tools import FunctionTool
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LoadedSkill:
    name: str
    target_agent: str
    tools: List[FunctionTool]

class SkillLoader:
    def __init__(self, skill_path: str):
        self.skill_path = skill_path
        self.skills: List[LoadedSkill] = []
        
    def load_skills(self) -> List[LoadedSkill]:
        """Scans the skill_path and loads all valid skills."""
        if not self.skill_path or not os.path.exists(self.skill_path):
            logger.warning(f"Skill path not found: {self.skill_path}")
            return []

        # Find all directories containing SKILL.md
        skill_dirs = glob.glob(os.path.join(self.skill_path, "*", "SKILL.md"))
        
        for md_path in skill_dirs:
            skill_dir = os.path.dirname(md_path)
            try:
                skill = self._load_single_skill(skill_dir, md_path)
                if skill:
                    self.skills.append(skill)
            except Exception as e:
                logger.error(f"Failed to load skill from {skill_dir}: {e}")
                
        return self.skills

    def _load_single_skill(self, skill_dir: str, md_path: str) -> Optional[LoadedSkill]:
        # 1. Parse Metadata from SKILL.md
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        metadata = {}
        
        # Simple YAML Frontmatter parser
        if content.startswith("---"):
            try:
                parts = content.split("---", 2)
                if len(parts) >= 2:
                     yaml_text = parts[1]
                     metadata = yaml.safe_load(yaml_text) or {}
            except Exception as e:
                logger.warning(f"Error parsing YAML in {md_path}: {e}")

        skill_name = metadata.get("name", os.path.basename(skill_dir))
        target_agent = metadata.get("target_agent", "bug_analyze_agent") # Default target
        
        # 2. Load Tools from tool.py
        tools = []
        tool_py = os.path.join(skill_dir, "tool.py")
        if os.path.exists(tool_py):
            tools = self._load_tools_from_module(tool_py, skill_name)

        logger.info(f"Loaded skill '{skill_name}' for agent '{target_agent}' with {len(tools)} tools.")
        
        return LoadedSkill(
            name=skill_name,
            target_agent=target_agent,
            tools=tools
        )

    def _load_tools_from_module(self, module_path: str, skill_name: str) -> List[FunctionTool]:
        spec = importlib.util.spec_from_file_location(f"skills.{skill_name}", module_path)
        if not spec or not spec.loader:
            return []
        
        module = importlib.util.module_from_spec(spec)
        sys_modules_key = f"bug_sleuth_skills_{skill_name}"
        # Prevent module collision by strictly naming
        
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error(f"Error executing tool module {module_path}: {e}")
            return []
            
        found_tools = []
        # Validation Logic: strict check using ADK types
        for name, obj in vars(module).items():
            if name.startswith("_"):
                continue
                
            # Accept explicitly defined FunctionTool objects
            if isinstance(obj, FunctionTool):
                found_tools.append(obj)
            # Decorator usually returns a FunctionTool-like object or the wrapper
            # We assume our @tool decorator returns FunctionTool
            
            # Reject bare functions (User Requirement)
            # Note: We can't easily distinguish a bare function from an internal helper unless we enforce @tool
            # So we ONLY accept FunctionTool objects.
            
        return found_tools

    def get_tools_for_agent(self, agent_name: str) -> List[FunctionTool]:
        """Returns aggregated tools for a specific agent."""
        all_tools = []
        for skill in self.skills:
            if skill.target_agent == agent_name:
                all_tools.extend(skill.tools)
        return all_tools


