import os
from pathlib import Path
from typing import List, Optional
from .decorators import validate_path
from google.adk.tools.tool_context import ToolContext
from context_pilot.shared_libraries.tool_response import ToolResponse
from context_pilot.shared_libraries.state_keys import StateKeys

@validate_path
async def read_file_tool(
    path: str,
    tool_context: ToolContext,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> dict:
    """
    读取文件内容或列出目录。
    
    **最佳实践 (Best Practice)**:
    - 如果搜索结果返回了行号范围 (e.g., Lines 15-50)，
      请使用 `read_file_tool(path, start_line=15, end_line=50)` 只读取该片段
    - 这样可以 **节省 Token**，保留更多上下文窗口用于分析
    - 仅在需要查看 Imports 或完整文件结构时才完整读取
    
    **支持的操作**:
    - 读取文件: 支持按行号范围读取片段
    - 列出目录: 当 path 是目录时，返回目录列表（深度限制 2 层）

    Args:
        path: 文件或目录的**绝对路径**
        start_line: 可选，起始行号 (1-based)
        end_line: 可选，结束行号

    Returns:
        dict: 文件内容或目录列表
    """
    if not path:
        return ToolResponse.error("Path is required.")
        
    _path = Path(path)
    if not _path.is_absolute():
        return ToolResponse.error(f"Path must be absolute: {path}")
        
    if not _path.exists():
        return ToolResponse.error(f"Path does not exist: {path}")

    # Directory Listing
    if _path.is_dir():
        if start_line or end_line:
             return ToolResponse.error("Line range not allowed for directories.")
        return _handle_dir_list(_path)

    # File Reading
    try:
        content = _path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return ToolResponse.error("File is not valid UTF-8 text.")
    except Exception as e:
        return ToolResponse.error(f"Error reading file: {e}")

    # [NEW] Track active context
    _update_active_context(tool_context, str(_path))

    lines = content.splitlines()
    total_lines = len(lines)
    
    _start = 1
    _end = total_lines
    
    if start_line is not None:
        _start = start_line
    if end_line is not None:
        _end = end_line
        
    if _end == -1: _end = total_lines
    
    if _start < 1: _start = 1
    if _end > total_lines: _end = total_lines
    if _end < _start:
        return ToolResponse.error(f"Invalid range: end_line {_end} < start_line {_start}")

    selected_lines = lines[_start-1 : _end]
    
    formatted_output = []
    for i, line in enumerate(selected_lines):
        line_num = _start + i
        formatted_output.append(f"{line_num:6}\t{line}")
        
    final_output = "\n".join(formatted_output)
    summary_text = f"Read {len(selected_lines)} lines from {path} (lines { _start}-{_end})"
    return ToolResponse.success(
        summary=summary_text,
        output=f"File: {path}\n{final_output}"
    )

def _handle_dir_list(path: Path) -> dict:
    try:
        output = []
        output.append(f"Directory listing for {path}:")
        root_depth = len(path.parts)
        for root, dirs, files in os.walk(path):
            current_depth = len(Path(root).parts)
            if current_depth - root_depth >= 2:
                del dirs[:] 
                continue
            
            # Filter hidden
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            files = [f for f in files if not f.startswith('.')]
            
            rel_path = os.path.relpath(root, path)
            if rel_path == ".":
                rel_path = ""
            else:
                output.append(f"\n[{rel_path}]")
            
            for d in dirs:
                output.append(f"  {d}/")
            for f in files:
                output.append(f"  {f}")
                
        summary_text = f"Listed {len(files)} files and {len(dirs)} directories in {path}"
        return ToolResponse.success(
            summary=summary_text,
            output="\n".join(output)
        )
    except Exception as e:
        return ToolResponse.error(f"Error listing directory: {e}")

def _update_active_context(tool_context: ToolContext, path: str):
    """Updates the ACTIVE_CONTEXT_FILES list in state."""
    try:
        active_files = tool_context.state.get(StateKeys.ACTIVE_CONTEXT_FILES, [])
        # Ensure it's a list
        if not isinstance(active_files, list):
            active_files = []
        
        # Add to front (Most Recently Used) and deduplicate
        if path in active_files:
            active_files.remove(path)
        active_files.insert(0, path)
        
        # Keep only top 5 to avoid clutter
        # active_files = active_files[:5]
        
        tool_context.state[StateKeys.ACTIVE_CONTEXT_FILES] = active_files
    except Exception as e:
        # Don't fail the tool if state update fails
        pass
