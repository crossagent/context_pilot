
from typing import AsyncGenerator
from google.adk.agents.llm_agent import LlmAgent
from google.adk.events.event import Event
from google.adk.agents.invocation_context import InvocationContext
from google.genai import types
import logging

logger = logging.getLogger(__name__)

class VisualLlmAgent(LlmAgent):
    """
    A custom LlmAgent that visualizes tool outputs by MERGING a visual text part
    into the existing FunctionCall or FunctionResponse event.
    
    This "Lossless" strategy ensures:
    1. Frontend UIs can render the tool activity (via the Text Part).
    2. Backend Agents/Tools see the correct event history structure (via the Function Part),
       preserving compatibility with tools like `load_artifacts`.
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Overrides the base execution loop to intercept and augment the event stream.
        This version implements "Event Merging" to preserve conversation history integrity.
        Text bubbles are appended as additional Parts to the standard FunctionCall/Response events.
        """
        # Track pending function calls by ID to retrieve arguments later
        pending_calls = {}

        # Iterate over the original event stream from LlmAgent
        async for event in super()._run_async_impl(ctx):
            
            # --- 0. Clean Empty Text Parts (Fix for "Unparseable Bubble") ---
            # LLM sometimes emits standalone newlines or whitespace before tool calls.
            # These cause empty bubbles in the UI. We filter them out here.
            if event.content and event.content.parts:
                # Filter out parts that are TEXT and contain only whitespace
                # But keep parts that are function calls/responses or non-empty text.
                new_parts = []
                for part in event.content.parts:
                    # Check if it's a text part (using duck typing or explicit type check)
                    text_val = getattr(part, "text", None)
                    if text_val is not None:
                         # It is a text part.
                         stripped_text = text_val.strip()
                         # [UI Fix] Filter out empty whitespace AND trivial punctuation (like ".") 
                         # that leads to "extra dot" bubbles.
                         # Also catch Markdown horizontal rules "---" which LLMs use as separators.
                         if stripped_text and stripped_text not in [".", "...", ",", "-", "---", "----"]:
                             new_parts.append(part)
                         else:
                             # It's empty or just noise. Skip it.
                             pass
                    else:
                        # Non-text part (e.g. FunctionCall/Response), keep it.
                        new_parts.append(part)
                
                event.content.parts = new_parts

            # --- 1. Handle Function Calls ---
            # --- 1. Handle Function Calls ---
            try:
                function_calls = event.get_function_calls()
                if function_calls:
                    full_msg_list = []
                    for call in function_calls:
                        call_id = getattr(call, 'id', call.name)
                        pending_calls[call_id] = call
                        
                        tool_name = call.name
                        args = call.args
                        
                        # --- FILTER: Only visualize args for specific tools ---
                        # User Request: "Only see execution call... detailed params [for list]"
                        ALLOWED_ARG_TOOLS = [
                            "run_bash_command", 
                            "read_file_tool", 
                            "read_code_tool",
                            "search_code_tool", 
                            "list_dir_tool", 
                            "run_python_code"
                        ]
                        
                        show_args = tool_name in ALLOWED_ARG_TOOLS
                        args_str = ""

                        if show_args and args:
                             if tool_name == "run_bash_command":
                                 cmd = args.get('command') or args.get('cmd')
                                 if cmd: args_str = f"`{cmd}`"
                             elif tool_name == "read_file_tool":
                                 path = args.get('file_path') or args.get('path')
                                 if path: args_str = f"`{path}`"
                             elif tool_name == "search_code_tool":
                                 query = args.get('query')
                                 pattern = args.get('file_pattern')
                                 if query:
                                     args_str = f"关键词 `{query}`"
                                     if pattern: args_str += f" in `{pattern}`"
                             elif tool_name == "run_python_code":
                                 code = args.get('code')
                                 if code:
                                     # Truncate code if too long
                                     preview = code[:50].replace("\n", " ") + "..." if len(code) > 50 else code
                                     args_str = f"`{preview}`"
                             else:
                                 # list_dir_tool or others in whitelist
                                 args_str = str(args)
                                 if len(args_str) > 100: args_str = args_str[:100] + "..."

                        # Icons
                        icons = {
                            "run_bash_command": "🖥️",
                            "read_file_tool": "📄",
                            "read_code_tool": "💻",
                            "run_python_code": "🐍"
                        }
                        icon = icons.get(tool_name, "🔧")
                        
                        # Format Message
                        # FILTER: Strictly only visualize if in whitelist.
                        # If not in whitelist, we skip creating textual part (Native UI handles it).
                        if show_args:
                            full_msg = f"{icon} **{tool_name}**"
                            if args_str:
                                full_msg += f": {args_str}"
                            
                            full_msg_list.append(full_msg)
                            logger.info(f"VisualLlmAgent merged action: {full_msg}")

                    if full_msg_list and event.content:
                        combined_text = "\n".join(full_msg_list)
                        event.content.parts.append(types.Part.from_text(text=combined_text))
                    
                    yield event
                    continue

            except Exception as e:
                logger.error(f"Error in VisualLlmAgent call merge: {e}")
                yield event
                continue

            # --- 2. Handle Function Responses ---
            try:
                # We need to reconstruct the parts list to interleave Text after each FunctionResponse
                if event.content and event.content.parts:
                    new_parts = []
                    
                    # Iterate through existing parts
                    for part in event.content.parts:
                        new_parts.append(part)
                        
                        # Check if this part is a FunctionResponse
                        # Duck typing check matching get_function_responses implementation
                        response_part = getattr(part, 'function_response', None)
                        if response_part:
                            tool_name = response_part.name
                            response_payload = response_part.response
                            
                            result_str = ""
                            icon = "✅"

                            
                            if isinstance(response_payload, dict):
                                is_error = response_payload.get("status") == "error" or response_payload.get("exit_code", 0) != 0
                                if is_error:
                                    icon = "❌"
                                    error_detail = response_payload.get("error", "")
                                    summary_text = response_payload.get("summary", "")
                                    if summary_text:
                                        result_str = summary_text
                                    elif error_detail:
                                        display_err = error_detail if len(error_detail) < 200 else error_detail[:200] + "..."
                                        result_str = f"Error: {display_err}"
                                    else:
                                        result_str = "Command failed"
                                elif "summary" in response_payload:
                                    result_str = response_payload['summary']
                            
                            # Construct and INSERT immediately after this part
                            if result_str:
                                full_msg = f"{icon} {result_str}"
                                new_text_part = types.Part.from_text(text=full_msg)
                                new_parts.append(new_text_part)
                                logger.info(f"VisualLlmAgent interleaved result: {full_msg[:50]}...")

                    # Replace the event parts with the new interleaved list
                    event.content.parts = new_parts
                    yield event
                    continue

            except Exception as e:
                logger.error(f"Error in VisualLlmAgent response merge: {e}")
                yield event
                continue

            # --- 3. Default Pass-through ---
            yield event

    def _format_value(self, val, depth=0, max_depth=2) -> str:
        """
        Safely formats a value for visual display, truncating long strings and 
        masking binary/complex objects to prevent API errors.
        """
        if depth > max_depth:
            return "..."
            
        try:
            # Handle list
            if isinstance(val, list):
                items = [self._format_value(x, depth+1) for x in val[:5]] # Max 5 items
                if len(val) > 5:
                    items.append(f"...(+{len(val)-5})")
                return "[" + ", ".join(items) + "]"
                
            # Handle dict
            if isinstance(val, dict):
                items = []
                for k, v in list(val.items())[:5]: # Max 5 keys
                   items.append(f"{k}: {self._format_value(v, depth+1)}")
                if len(val) > 5:
                   items.append("...")
                return "{" + ", ".join(items) + "}"
            
            # Handle Blob/Part/Bytes (The likely cause of 500 error)
            type_str = str(type(val))
            if "Blob" in type_str or "Part" in type_str or isinstance(val, bytes):
                return "<Binary/Complex Data>"
            
            # Handle String
            s = str(val)
            if len(s) > 200:
                return s[:200] + "..."
            return s
            
        except Exception:
            return "<Unformattable>"
