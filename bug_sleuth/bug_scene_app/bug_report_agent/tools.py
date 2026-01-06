from typing import Any
import requests
import json
from datetime import datetime
from google.genai import types
from google.adk.tools import LongRunningFunctionTool
from google.adk.tools import ToolContext
from ..bug_analyze_agent import bug_analyze_agent
from ..shared_libraries.state_keys import AgentKeys
import os
import tempfile
import mimetypes
from typing import List, Optional

import ssl
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 创建自定义SSL上下文
class CustomHTTPAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

# 创建全局session
session = requests.Session()
session.mount('https://', CustomHTTPAdapter())
session.mount('http://', HTTPAdapter())

async def upload_files_to_server(tool_context: ToolContext) -> dict[str, Any]:
    """上传文件到服务器
    
    Args:
        tool_context: 工具上下文，包含状态信息和附件
    
    Returns:
        dict: 包含上传结果的字典
    """
    try:
        # 获取附件列表
        artifacts = await tool_context.list_artifacts()
        
        # 准备上传的文件数据
        files = {}
        data = {}
        
        # 处理媒体文件附件
        media_files = []
        for artifact in artifacts:
            if artifact.endswith(('.png', '.jpg', '.jpeg', '.mp4', '.avi')):
                parts = await tool_context.load_artifact(artifact, 0)
                if parts and parts.inline_data:
                    mime_type = parts.inline_data.mime_type or _get_mime_type(artifact)
                    media_files.append({
                        'name': artifact,
                        'data': parts.inline_data.data,
                        'mime_type': mime_type
                    })
        
        # 创建日志文件内容
        log_content = "用户提交了资源文件".encode('utf-8')

        # 准备上传数据
        # 'file' 字段用于上传日志
        # 'mediaFiles' 字段用于上传媒体文件列表
        upload_files = [
            ('file', ('bug_report_log.txt', log_content, 'text/plain'))
        ]
        
        # 添加mediaFiles列表
        if media_files:
            for media_file in media_files:
                filename = os.path.basename(media_file['name'])
                upload_files.append((
                    'mediaFiles',           # 字段名
                    (
                        filename,               # 文件名
                        media_file['data'],     # 文件内容
                        media_file['mime_type'] # MIME类型
                    )
                ))

        # 添加表单字段
        data = {
            'deviceName': tool_context.state.get(StateKeys.DEVICE_INFO, 'test_device'),
            'nickName': tool_context.state.get(StateKeys.NICK_NAME, 'test_user'),
            'clientVersion': tool_context.state.get(StateKeys.CLIENT_VERSION, 'test_version'),
            'errorCount': 'E0',
            'warningCount': 'W0',
            'infoCount': 'L0',
        }
        
        # 发送上传请求
        upload_url = os.getenv("BUG_REPORT_UPLOAD_URL", "http://localhost:9010/uploadLog")
        
        response = session.post(
            upload_url,
            files=upload_files,
            data=data,
            timeout=60,
            verify=False  # 添加此行以禁用SSL证书验证
        )
        
        if response.status_code == 200:
            try:
                # 解析服务器返回的JSON数据
                result = response.json() if response.content else {}
                
                return {
                    'status': 'success',
                    'message': result.get('message', '文件上传成功'),
                    'uploaded_files': list(files.keys()),  #type: ignore
                    'logLink': result.get('logLink', ''),
                    'mediaFiles': result.get('mediaFiles', []),
                    'totalMediaFiles': result.get('totalMediaFiles', len(media_files)),
                    'response_data': result
                }
            except json.JSONDecodeError as e:
                return {
                    'status': 'error',
                    'message': f'解析服务器响应失败: {str(e)}',
                    'uploaded_files': list(files.keys()), #type: ignore
                    'logLink': None,
                    'mediaFiles': [],
                    'totalMediaFiles': 0,
                    'response_text': response.text
                }
        else:
            return {
                'status': 'error',
                'message': f'文件上传失败，HTTP状态码: {response.status_code}',
                'uploaded_files': [],
                'logLink': None,
                'mediaFiles': [],
                'totalMediaFiles': 0,
                'response_text': response.text
            }
            
    except requests.exceptions.Timeout:
        return {
            'status': 'error',
            'message': '上传请求超时，请检查网络连接',
            'uploaded_files': [],
            'logLink': None,
            'mediaFiles': [],
            'totalMediaFiles': 0
        }
    except requests.exceptions.ConnectionError:
        return {
            'status': 'error',
            'message': '上传连接失败，请检查服务器地址是否正确',
            'uploaded_files': [],
            'logLink': None,
            'mediaFiles': [],
            'totalMediaFiles': 0
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'文件上传时发生错误: {str(e)}',
            'uploaded_files': [],
            'logLink': None,
            'mediaFiles': [],
            'totalMediaFiles': 0
        }

def _get_mime_type(file_path: str) -> str:
    """根据文件扩展名获取MIME类型"""
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        return mime_type
    
    # 手动映射常见文件类型
    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.mp4': 'video/mp4',
        '.avi': 'video/avi'
    }
    return mime_map.get(ext, 'application/octet-stream')

async def submit_bug_report(tool_context: ToolContext) -> dict[str, Any]:
    """submit the bug report to the platform.
    
    Args:
        tool_context: 工具上下文，包含bug信息等状态
    
    Returns:
        dict: 包含提交状态的字典
    """

    bug_description = tool_context.state.get(StateKeys.BUG_DESCRIPTION, "暂无")
    bug_reproduce_steps = tool_context.state.get(StateKeys.BUG_REPRODUCTION_STEPS, "暂无")
    bug_reproduce_confidence = tool_context.state.get(StateKeys.BUG_REPRODUCTION_CONFIDENCE, "1")
    bug_reproduce_guess_cause = tool_context.state.get(StateKeys.BUG_REPRODUCTION_GUESS_CAUSE, "暂无")
    
    bug_info = "BUG现场整理信息:\n\n"
    bug_info += f"BUG现象: {bug_description}\n\n"
    bug_info += f"重现步骤: {bug_reproduce_steps}\n\n"
    bug_info += f"原因推测: {bug_reproduce_guess_cause}\n\n"
    bug_info += f"重现信心: {bug_reproduce_confidence}\n\n"

    response = await upload_files_to_server(tool_context)

    if response['status'] == 'success':
        bug_info += "\n\n -----以下是现场环境信息-----"
        bug_info += "\n\n 代码分支: " + tool_context.state.get("productBranch", "未知设备")  # 添加设备信息到bug_info中
        bug_info += "\n\n 设备信息: " + tool_context.state.get("deviceInfo", "未知设备")  # 添加设备信息到bug_info中
        bug_info += "\n\n 设备名称: " + tool_context.state.get(StateKeys.DEVICE_NAME, "未知版本")  # 添加客户端版本到bug_info中
        bug_info += "\n\n 客户端日志地址: " + tool_context.state.get("clientLogUrl", "")  # 添加文件信息到bug_info中
        bug_info += "\n\n 客户端版本号: " + tool_context.state.get("clientVersion", "")  
        bug_info += "\n\n 链接的服务器id: " + tool_context.state.get("serverId", "")  
        bug_info += "\n\n 用户的roleid: " + tool_context.state.get("roleId", "")  # 添加用户的roleid到bug_info中
        bug_info += "\n\n 用户昵称: " + tool_context.state.get("nickName", "未知用户")  # 添加用户昵称到bug_info中
        bug_info += "\n\n 当前帧率: " + str(tool_context.state.get(StateKeys.FPS, "未知FPS"))
        bug_info += "\n\n 网络延迟: " + str(tool_context.state.get(StateKeys.PING, "未知PING"))
        
        # 添加上传的媒体文件信息
        media_files = response.get('mediaFiles', [])
        total_media_files = response.get('totalMediaFiles', 0)
        client_log_link = response.get('logLink', '')
        
        if total_media_files > 0 and media_files:
            bug_info += f"\n\n 上传文件数量: {total_media_files}"
            bug_info += "\n\n 上传的媒体文件:"
            
            if client_log_link:
                # Extract base path from full URL
                base_url = "/".join(client_log_link.split("/")[:-1]) + "/"
            else:
                base_url = ""
            
            for media_file in media_files:
                if isinstance(media_file, str):
                    # 如果media_file只是文件名
                    file_name = media_file
                elif isinstance(media_file, dict) and 'name' in media_file:
                    # 如果media_file是包含name字段的字典
                    file_name = media_file['name']
                else:
                    # 其他情况，尝试转换为字符串
                    file_name = str(media_file)
                
                # 构建完整的文件链接
                if base_url and file_name:
                    full_url = base_url + file_name
                    bug_info += f"\n   - {file_name}: {full_url}"
                else:
                    bug_info += f"\n   - {file_name}"

        response_feedback = post_result_to_feedback(bug_info)
        response_dingtalk = post_result_to_dingtalk(bug_info)

        # 合并两个结果
        return {
            'status': 'success' if response_feedback['status'] == 'success' and response_dingtalk['status'] == 'success' else 'partial_success' if response_feedback['status'] == 'success' or response_dingtalk['status'] == 'success' else 'error',
            'feedback_result': response_feedback,
            'dingtalk_result': response_dingtalk,
            'message': f"平台上报: {response_feedback['message']}; 钉钉转发: {response_dingtalk['message']}"
        }
    else:
        return response

def post_result_to_dingtalk(bug_info: str) -> dict[str, Any]:
    try:
        # Generic webhook URL from environment
        url = os.getenv("DINGTALK_WEBHOOK_URL")
        if not url:
            return {'status': 'skipped', 'message': 'DingTalk webhook not configured'}
        
        # Construct generic message body
        payload = {
            "content": bug_info,
            "title": "Bug Report",
            "btnOrientation": "0",  
            "btns": []
        }

        # 设置请求头
        headers = {
            'Content-Type': 'application/json'
        }

        # 发送POST请求
        response = session.post(url, json=payload, headers=headers, timeout=30)
        
        # 检查响应状态
        if response.status_code == 200:
            return {
                'status': 'success',
                'status': 'success',
                'message': 'Bug report forwarded to IM group.',
                'response_data': response.text
            }
        else:
            return {
                'status': 'error',
                'message': f'提交失败，HTTP状态码: {response.status_code}',
                'response_text': response.text
            }
            
    except requests.exceptions.Timeout:
        return {
            'status': 'error',
            'message': '请求超时，请检查网络连接'
        }
    except requests.exceptions.ConnectionError:
        return {
            'status': 'error',
            'message': '连接失败，请检查服务器地址是否正确'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'提交Bug报告时发生未知错误: {str(e)}'
        }

def post_result_to_feedback(bug_info: str) -> dict[str, Any]:
    try:
        # Feedback Service URL
        url = os.getenv("FEEDBACK_SERVICE_URL")
        if not url:
             return {'status': 'skipped', 'message': 'Feedback service not configured'}
        
        # Construct message body
        payload = {
            "senderPlatform": "Win",
            "msgId": f"msg{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "senderNick": "BugSleuth Agent",
            "createAt": int(datetime.now().timestamp() * 1000),
            "text": {
                "content": f"Bug Report:\n{bug_info}"
            },
            "msgtype": "text"
        }

        # 设置请求头
        headers = {
            'Content-Type': 'application/json'
        }

        # 发送POST请求
        response = session.post(url, json=payload, headers=headers, timeout=30)
        
        # 检查响应状态
        if response.status_code == 200:
            return {
                'status': 'success',
                'status': 'success',
                'message': 'Bug report submitted successfully.',
                'response_data': response.json() if response.content else None
            }
        else:
            return {
                'status': 'error',
                'message': f'提交失败，HTTP状态码: {response.status_code}',
                'response_text': response.text
            }
            
    except requests.exceptions.Timeout:
        return {
            'status': 'error',
            'message': '请求超时，请检查网络连接'
        }
    except requests.exceptions.ConnectionError:
        return {
            'status': 'error',
            'message': '连接失败，请检查服务器地址是否正确'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'提交Bug报告时发生未知错误: {str(e)}'
        }