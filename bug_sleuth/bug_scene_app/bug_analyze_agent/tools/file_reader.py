import os
from pathlib import Path
from typing import List, Optional
from .decorators import validate_path
from google.adk.tools.tool_context import ToolContext

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
        return {"status": "error", "error": "Path is required."}
        
    _path = Path(path)
    if not _path.is_absolute():
        return {"status": "error", "error": f"Path must be absolute: {path}"}
        
    if not _path.exists():
        return {"status": "error", "error": f"Path does not exist: {path}"}

    # Directory Listing
    if _path.is_dir():
        if start_line or end_line:
             return {"status": "error", "error": "Line range not allowed for directories."}
        return _handle_dir_list(_path)

    # File Reading
    try:
        content = _path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return {"status": "error", "error": "File is not valid UTF-8 text."}
    except Exception as e:
        return {"status": "error", "error": f"Error reading file: {e}"}

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
        return {"status": "error", "error": f"Invalid range: end_line {_end} < start_line {_start}"}

    selected_lines = lines[_start-1 : _end]
    
    formatted_output = []
    for i, line in enumerate(selected_lines):
        line_num = _start + i
        formatted_output.append(f"{line_num:6}\t{line}")
        
    final_output = "\n".join(formatted_output)
    summary_text = f"Read {len(selected_lines)} lines from {path} (lines { _start}-{_end})"
    return {
        "status": "success", 
        "output": f"File: {path}\n{final_output}",
        "summary": summary_text
    }

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
        return {
            "status": "success", 
            "output": "\n".join(output),
            "summary": summary_text
        }
    except Exception as e:
        return {"status": "error", "error": f"Error listing directory: {e}"}

@validate_path
async def read_code_tool(
    path: str,
    tool_context: ToolContext
) -> dict:
    """
    Read a CODE file completely to understand full context.
    Use this for .cs, .py, .cpp, .lua, etc.
    
    Args:
        path: Absolute path to the code file.
        
    Returns:
        dict: Full file content.
    """
    MAX_CHARS = 100000  # 100k chars limit (~20k-30k tokens)
    
    if not path:
        return {"status": "error", "error": "Path is required."}
        
    _path = Path(path)
    if not _path.is_absolute():
        return {"status": "error", "error": f"Path must be absolute: {path}"}
        
    if not _path.exists():
        return {"status": "error", "error": f"Path does not exist: {path}"}
        
    if _path.is_dir():
         return {"status": "error", "error": f"Path is a directory, not a file: {path}. Use list_dir_tool."}

    try:
        # Read text
        content = _path.read_text(encoding='utf-8')
        
        if len(content) > MAX_CHARS:
            # Safety Truncation
            head = content[:2000]
            tail = content[-2000:]
            return {
                "status": "error", 
                "error": (
                    f"File too large ({len(content)} chars). Limit is {MAX_CHARS}. "
                    "Reading huge files can overflow the context window.\n"
                    "Showing Head (2000) and Tail (2000) only.\n\n"
                    f"{head}\n\n...[Truncated]...\n\n{tail}"
                )
            }
            
        # Add line numbers for reference
        lines = content.splitlines()
        formatted_output = []
        for i, line in enumerate(lines):
            formatted_output.append(f"{i+1:4} | {line}")
            
        final_output = "\n".join(formatted_output)
        
        # Determine language for markdown
        ext = _path.suffix.lstrip('.') if _path.suffix else 'text'
        
        return {
            "status": "success",
            "output": f"Code File: {path}\n```{ext}\n{final_output}\n```",
            "summary": f"Read full code file {path} ({len(lines)} lines)"
        }
        
    except UnicodeDecodeError:
         return {"status": "error", "error": "File is not valid UTF-8 text."}
    except Exception as e:
         return {"status": "error", "error": f"Error reading code file: {e}"}
