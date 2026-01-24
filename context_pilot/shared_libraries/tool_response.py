"""
标准化工具响应 Schema
======================
所有后端工具应使用此模块定义的格式返回结果，
以便前端 (AG-UI) 能够统一渲染工具执行状态。

Usage:
    from context_pilot.shared_libraries.tool_response import ToolResponse

    # 成功
    return ToolResponse.success(
        summary="找到 3 个符号定义",
        data={"definitions": [...]}
    )

    # 失败
    return ToolResponse.error("未找到日志文件")
"""

from typing import Any, Dict, Optional, TypedDict, Literal


class ToolResponseDict(TypedDict, total=False):
    """工具响应的类型定义"""
    status: Literal["success", "error"]
    summary: str
    data: Any
    error: str


class ToolResponse:
    """
    标准化的工具响应构建器。
    
    所有工具应使用此类来构建返回值，确保前端能够正确渲染：
    - `status`: "success" 或 "error"
    - `summary`: 简短描述，用于前端显示（必须）
    - `data`: 实际返回数据 (成功时)
    - `error`: 错误详情 (失败时)
    
    前端 (ToolMonitor.tsx) 期望的格式：
    - 成功: {"status": "success", "summary": "...", "data": ...}
    - 失败: {"status": "error", "error": "...", "summary": "..."}
    """
    
    @staticmethod
    def success(
        summary: str,
        data: Optional[Any] = None,
        **extra_fields
    ) -> Dict[str, Any]:
        """
        构建成功响应。
        
        Args:
            summary: 简短摘要，前端会直接显示此内容
            data: 可选的返回数据
            **extra_fields: 额外字段（向后兼容）
            
        Returns:
            标准化的响应字典
            
        Example:
            return ToolResponse.success(
                summary="找到 3 个匹配结果",
                data={"results": [...], "count": 3}
            )
        """
        response: Dict[str, Any] = {
            "status": "success",
            "summary": summary,
        }
        if data is not None:
            response["data"] = data
        response.update(extra_fields)
        return response
    
    @staticmethod
    def error(
        error: str,
        summary: Optional[str] = None,
        **extra_fields
    ) -> Dict[str, Any]:
        """
        构建错误响应。
        
        Args:
            error: 错误详情
            summary: 简短摘要（默认使用 error）
            **extra_fields: 额外字段
            
        Returns:
            标准化的响应字典
            
        Example:
            return ToolResponse.error("文件不存在: /path/to/file")
        """
        response: Dict[str, Any] = {
            "status": "error",
            "error": error,
            "summary": summary or error,
        }
        response.update(extra_fields)
        return response
    
    @staticmethod
    def from_dict(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        将现有的响应字典规范化为标准格式。
        可用于兼容旧工具的返回值。
        
        Args:
            result: 现有的响应字典
            
        Returns:
            规范化后的响应字典
        """
        # 已经是标准格式
        if "status" in result and result["status"] in ("success", "error"):
            # 确保有 summary
            if "summary" not in result:
                if result["status"] == "error":
                    result["summary"] = result.get("error", "操作失败")
                else:
                    result["summary"] = result.get("message", "操作成功")
            return result
        
        # 兼容旧格式 - 有 error 字段
        if "error" in result:
            return ToolResponse.error(
                error=result["error"],
                **{k: v for k, v in result.items() if k != "error"}
            )
        
        # 默认成功
        return ToolResponse.success(
            summary=result.get("message", result.get("summary", "操作成功")),
            data=result
        )
