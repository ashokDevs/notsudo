import json
import os
import hashlib
from pathlib import Path
from openai import OpenAI
from utils.logger import get_logger

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Available models for OpenRouter
AVAILABLE_MODELS = {
    'claude-3-5-sonnet': {
        'id': 'anthropic/claude-3.5-sonnet',
        'name': 'Claude 3.5 Sonnet',
        'provider': 'anthropic'
    },
}

DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

# Enable LLM caching during development
ENABLE_LLM_CACHE = os.environ.get('ENABLE_LLM_CACHE', 'false').lower() == 'true'
LLM_CACHE_DIR = Path(os.environ.get('LLM_CACHE_DIR', '/tmp/llm_cache'))

logger = get_logger(__name__)


class AIService:
    def __init__(self, api_key, model=None):
        self.client = OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL
        )
        self.model = model or DEFAULT_MODEL
        self.cache_enabled = ENABLE_LLM_CACHE
        self.cache_dir = LLM_CACHE_DIR
        
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("llm_cache_enabled", cache_dir=str(self.cache_dir))
        
        logger.info("ai_service_initialized", model=self.model, base_url=OPENROUTER_BASE_URL)
    
    def _get_cache_key(self, *args) -> str:
        """Generate a cache key from the input arguments."""
        content = json.dumps(args, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _get_cached_response(self, cache_key: str):
        """Try to get a cached response."""
        if not self.cache_enabled:
            return None
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                logger.info("llm_cache_hit", cache_key=cache_key)
                return cached
            except (json.JSONDecodeError, IOError):
                pass
        return None
    
    def _save_to_cache(self, cache_key: str, response: dict):
        """Save a response to the cache."""
        if not self.cache_enabled:
            return
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(response, f)
            logger.info("llm_cache_saved", cache_key=cache_key)
        except IOError as e:
            logger.warning("llm_cache_save_failed", error=str(e))
        
    def analyze_issue_and_plan_changes(self, issue_title, issue_body, comment_body, codebase_files, custom_rules=None, repo_url=None, code_execution_service=None, job_id=None):
        logger.info(
            "analyzing_issue",
            issue_title=issue_title,
            comment_length=len(comment_body),
            codebase_files_count=len(codebase_files)
        )
        
        # Build codebase context with truncation warnings for large files
        MAX_FILE_CHARS = 2000
        context_parts = []
        
        for file in codebase_files:
            content = file['content']
            is_truncated = len(content) > MAX_FILE_CHARS
            
            if is_truncated:
                context_parts.append(
                    f"File: {file['path']} [TRUNCATED - showing {MAX_FILE_CHARS}/{len(content)} chars]\n```\n{content[:MAX_FILE_CHARS]}\n```"
                )
            else:
                context_parts.append(
                    f"File: {file['path']}\n```\n{content}\n```"
                )
        
        codebase_context = "\n\n".join(context_parts)
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Replace entire file content. Use for new files or when the whole file structure needs to change.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file to edit"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Explanation of why this change is needed"
                            },
                            "new_content": {
                                "type": "string",
                                "description": "The complete new content for the file"
                            }
                        },
                        "required": ["file_path", "reason", "new_content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "patch_file",
                    "description": "Apply a targeted structural transformation using pattern matching. Use for renaming, updating calls, or changing specific code patterns without replacing the entire file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file to modify"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Explanation of the transformation"
                            },
                            "match_pattern": {
                                "type": "string",
                                "description": "Pattern to match using :[hole] syntax for wildcards. Example: 'print(:[arg])' matches any print call."
                            },
                            "replace_pattern": {
                                "type": "string",
                                "description": "Replacement pattern using the same :[hole] names. Example: 'logging.info(:[arg])'"
                            }
                        },
                        "required": ["file_path", "reason", "match_pattern", "replace_pattern"]
                    }
                }
            }
        ]
        
        # Add exec tool if code execution service is available
        if code_execution_service and repo_url:
            tools.append({
                "type": "function",
                "function": {
                    "name": "exec",
                    "description": "Execute a shell command to explore the codebase or run tests. Use this to verify assumptions before making changes. The command runs in a sandboxed environment.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The shell command to execute (e.g., 'ls -R', 'grep -r pattern .', 'pytest tests/')"
                            }
                        },
                        "required": ["command"]
                    }
                }
            })

        # Add screenshot tool
        tools.append({
            "type": "function",
            "function": {
                "name": "take_screenshot",
                "description": "Take a screenshot of a URL to verify UI changes or show the user the current state.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to capture (e.g., http://localhost:3000)"
                        }
                    },
                    "required": ["url"]
                }
            }
        })
        
        system_prompt = """You are an expert software engineer. Analyze the GitHub issue and suggest code changes.

You have specific tools for making changes.

TOOLS:
1. **patch_file** - For TARGETED changes (PREFERRED):
   - Use :[hole_name] syntax to match any expression
   - Example: 'print(:[arg])' → 'logging.info(:[arg])' replaces print calls
   - Example: 'def old_name(:[args])' → 'def new_name(:[args])' renames functions
   - Preserves surrounding code automatically
   - Use for: renaming, updating function calls, changing imports, fixing patterns

2. **edit_file** - For FULL file replacement:
   - Use only for NEW files or when entire structure must change
   - Provide COMPLETE file content (never truncate)
   - Preserve exact formatting and whitespace

3. **exec** - For EXPLORATION and VERIFICATION (if available):
   - Run shell commands to check file structure, grep for patterns, or run tests.
   - Use this to gather more information if the provided context is insufficient.
   - NOTE: This runs in a sandbox.

4. **take_screenshot** - For UI VERIFICATION:
   - Capture a screenshot of the running application to verify visual changes.
   - Useful for frontend tasks to verify the UI.

Rules:
1. PREFER patch_file for targeted changes - it's safer and more precise
2. Use edit_file only when patch_file cannot express the change
3. Make minimal, focused changes that directly address the issue
4. Maintain code style and conventions from the existing codebase
5. You can use 'exec' to verify your understanding before proposing changes."""

        # Add custom rules if provided
        if custom_rules and custom_rules.strip():
            system_prompt += f"\n\nAdditional Custom Rules:\n{custom_rules}"

        user_prompt = f"""GitHub Issue: {issue_title}

Issue Description:
{issue_body}

User Comment:
{comment_body}

Available Codebase Files:
{codebase_context}

Analyze this issue and determine what code changes are needed. Use the edit_file function to specify the exact changes."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        if job_id:
            from services import db
            db.insert_job_log({
                'job_id': job_id,
                'role': 'user',
                'type': 'message',
                'content': f"**Issue Analysis Request (OpenRouter)**\n\n**Title:** {issue_title}\n\n**Body:**\n{issue_body}\n\n**Comment:**\n{comment_body}",
                'metadata': {'file_count': len(codebase_files), 'model': self.model}
            })
        
        MAX_TURNS = 5
        current_turn = 0
        
        while current_turn < MAX_TURNS:
            current_turn += 1
            logger.info("calling_llm", model=self.model, turn=current_turn, messages_count=len(messages))
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto"
                )
                
                message = response.choices[0].message
                messages.append(message)
                
                if job_id and message.content:
                    from services import db
                    db.insert_job_log({
                        'job_id': job_id,
                        'role': 'assistant',
                        'type': 'message',
                        'content': message.content,
                        'metadata': {'model': self.model, 'turn': current_turn}
                    })
                
                # Check for tool calls
                if not message.tool_calls:
                    # No tool calls, just return the analysis (thought process)
                    # But we really expect tool calls for the final result.
                    # If the model just chats, we might want to prompt it to make changes.
                    # For now, we'll treat it as "no changes needed" or just return the text.
                    logger.info("llm_response_no_tools", content_length=len(message.content) if message.content else 0)
                    return {
                        'file_changes': [],
                        'analysis': message.content or "AI provided analysis but no code changes."
                    }
                
                # Process all tool calls
                file_changes = []
                tool_outputs = []
                has_exec_call = False
                
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "exec":
                        has_exec_call = True
                        if not (code_execution_service and repo_url):
                            output = "Error: exec tool is not available in this context."
                        else:
                            try:
                                args = json.loads(tool_call.function.arguments)
                                command = args.get('command')
                                logger.info("executing_command", command=command)
                                
                                exec_result = code_execution_service.run_adhoc_command(
                                    repo_url=repo_url,
                                    command=command
                                )
                                
                                output = ""
                                if exec_result.logs:
                                    output += "\n".join(exec_result.logs[-5:]) # Last 5 lines of log
                                if exec_result.error:
                                    output += f"\nError: {exec_result.error}"
                                    
                                if not output:
                                    output = "Command completed with no output."
                                    
                            except Exception as e:
                                output = f"Failed to execute command: {str(e)}"
                        
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": "exec",
                            "content": output
                        })

                    elif tool_call.function.name == "take_screenshot":
                        try:
                            args = json.loads(tool_call.function.arguments)
                            url = args.get('url')

                            from services.screenshot_service import ScreenshotService
                            screenshot_service = ScreenshotService()

                            if not screenshot_service.is_available():
                                output = "Error: Screenshot service is not available (missing dependencies or config)."
                            else:
                                screenshot_url = screenshot_service.take_screenshot(url)
                                if screenshot_url:
                                    output = f"Screenshot taken: {screenshot_url}"
                                    # Log to DB so frontend sees it
                                    if job_id:
                                        from services import db
                                        db.insert_job_log({
                                            'job_id': job_id,
                                            'role': 'tool',
                                            'type': 'screenshot',
                                            'content': screenshot_url,
                                            'metadata': {'url': url}
                                        })
                                else:
                                    output = "Error: Failed to take screenshot."

                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": "take_screenshot",
                                "content": output
                            })

                        except Exception as e:
                            logger.error("tool_arg_parse_error", error=str(e))
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": "take_screenshot",
                                "content": f"Error: {str(e)}"
                            })
                        
                    elif tool_call.function.name == "edit_file":
                        # This is a final action
                        try:
                            args = json.loads(tool_call.function.arguments)
                            file_path = args.get('file_path') or args.get('path')
                            reason = args.get('reason')
                            new_content = args.get('new_content', '')
                            
                            if new_content:
                                new_content = new_content.replace('\\n', '\n').replace('\\r\\n', '\n').replace('\\r', '\n')
                            
                                file_changes.append({
                                    'type': 'edit',
                                    'file_path': file_path,
                                    'new_content': new_content,
                                    'reason': reason
                                })

                                if job_id:
                                    from services import db
                                    db.insert_job_log({
                                        'job_id': job_id,
                                        'role': 'assistant',
                                        'type': 'file_change',
                                        'content': reason or f"Editing {file_path}",
                                        'metadata': {
                                            'file_path': file_path,
                                            'new_content': new_content
                                        }
                                    })
                        except Exception as e:
                            logger.error("tool_arg_parse_error", error=str(e))
                            
                    elif tool_call.function.name == "patch_file":
                        # This is a final action
                        try:
                            args = json.loads(tool_call.function.arguments)
                            file_changes.append({
                                'type': 'patch',
                                'file_path': args.get('file_path') or args.get('path'),
                                'match_pattern': args.get('match_pattern'),
                                'replace_pattern': args.get('replace_pattern'),
                                'reason': args.get('reason')
                            })
                        except Exception as e:
                            logger.error("tool_arg_parse_error", error=str(e))
                
                # If we have tool outputs (from exec), append them and continue loop
                if tool_outputs:
                    messages.extend(tool_outputs)
                    # If we also had file changes mixed with exec, we should probably return the file changes?
                    # But usually the model will exec first, then next turn do the changes.
                    # If valid file changes are present, let's assume we are done, unless the model explicitly wants to continue.
                    # But typically 'exec' is for information gathering.
                    if not file_changes:
                        continue
                
                # If we have file changes (and maybe execs too), we are done via the "action" tools
                if file_changes:
                    return {
                        'file_changes': file_changes,
                        'analysis': message.content or "AI suggested changes."
                    }
                    
            except Exception as e:
                logger.error("llm_call_failed", error=str(e), model=self.model)
                raise
        
        # If we reached max turns without returning checks
        return {
            'file_changes': [],
            'analysis': "Reached maximum conversation turns without final changes."
        }


    def analyze_pr_comment(self, pr_title, pr_body, comment_body, codebase_files, custom_rules=None, job_id=None):
        logger.info(
            "analyzing_pr_comment",
            pr_title=pr_title,
            comment_length=len(comment_body),
            codebase_files_count=len(codebase_files)
        )
        
        # Check cache first
        cache_key = self._get_cache_key(
            'analyze_pr', pr_title, pr_body, comment_body,
            [(f['path'], f['content'][:500]) for f in codebase_files]
        )
        cached = self._get_cached_response(cache_key)
        if cached:
            return cached
        
        # Build codebase context with truncation warnings for large files
        MAX_FILE_CHARS = 2000
        context_parts = []
        truncated_files = []
        
        for file in codebase_files:
            content = file['content']
            is_truncated = len(content) > MAX_FILE_CHARS
            
            if is_truncated:
                truncated_files.append({
                    'path': file['path'],
                    'original_size': len(content),
                    'shown_size': MAX_FILE_CHARS
                })
                context_parts.append(
                    f"File: {file['path']} [TRUNCATED - showing {MAX_FILE_CHARS}/{len(content)} chars]\\n```\\n{content[:MAX_FILE_CHARS]}\\n```"
                )
            else:
                context_parts.append(
                    f"File: {file['path']}\\n```\\n{content}\\n```"
                )
        
        codebase_context = "\\n\\n".join(context_parts)
        
        # Log warning if files were truncated
        if truncated_files:
            logger.warning(
                "files_truncated_for_context",
                truncated_count=len(truncated_files),
                files=[f['path'] for f in truncated_files]
            )
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Replace entire file content. Use for new files or when the whole file structure needs to change.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file to edit"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Explanation of why this change is needed"
                            },
                            "new_content": {
                                "type": "string",
                                "description": "The complete new content for the file"
                            }
                        },
                        "required": ["file_path", "reason", "new_content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "patch_file",
                    "description": "Apply a targeted structural transformation using pattern matching. Use for renaming, updating calls, or changing specific code patterns without replacing the entire file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file to modify"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Explanation of the transformation"
                            },
                            "match_pattern": {
                                "type": "string",
                                "description": "Pattern to match using :[hole] syntax for wildcards. Example: 'print(:[arg])' matches any print call."
                            },
                            "replace_pattern": {
                                "type": "string",
                                "description": "Replacement pattern using the same :[hole] names. Example: 'logging.info(:[arg])'"
                            }
                        },
                        "required": ["file_path", "reason", "match_pattern", "replace_pattern"]
                    }
                }
            }
        ]
        
        system_prompt = """You are an expert software engineer addressing feedback on a Pull Request.
The user has reviewed the code and requested changes.

You have TWO tools for making changes:

1. **patch_file** - For TARGETED changes (PREFERRED):
   - Use :[hole_name] syntax to match any expression
   - Example: 'print(:[arg])' → 'logging.info(:[arg])' replaces print calls
   - Example: 'def old_name(:[args])' → 'def new_name(:[args])' renames functions
   - Preserves surrounding code automatically
   - Use for: renaming, updating function calls, changing imports, fixing patterns

2. **edit_file** - For FULL file replacement:
   - Use only for NEW files or when entire structure must change
   - Provide COMPLETE file content (never truncate)
   - Preserve exact formatting and whitespace

Rules:
1. Address the user's comments directly.
2. PREFER patch_file for targeted changes - it's safer and more precise.
3. Use edit_file only when patch_file cannot express the change.
4. Make minimal, focused changes that directly address the feedback.
5. Maintain code style and conventions from the existing codebase."""

        # Add custom rules if provided
        if custom_rules and custom_rules.strip():
            system_prompt += f"\\n\\nAdditional Custom Rules:\\n{custom_rules}"

        user_prompt = f"""PR Title: {pr_title}
PR Description:
{pr_body}

User Comment on PR:
{comment_body}

Current File Contents:
{codebase_context}

Analyze the comment and update the code to address the feedback. Use the available tools to make changes."""

        logger.info("calling_llm_pr_feedback", model=self.model, prompt_length=len(user_prompt))
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                tools=tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            if job_id and message.content:
                from services import db
                db.insert_job_log({
                    'job_id': job_id,
                    'role': 'assistant',
                    'type': 'message',
                    'content': message.content,
                    'metadata': {'model': self.model, 'action': 'pr_feedback'}
                })

            file_changes = []
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "edit_file":
                        try:
                            args = json.loads(tool_call.function.arguments)
                            new_content = args.get('new_content', '')
                            # Normalize newlines
                            if new_content:
                                new_content = new_content.replace('\\\\n', '\\n').replace('\\\\r\\\\n', '\\n').replace('\\\\r', '\\n')
                            
                            file_changes.append({
                                'type': 'edit',
                                'file_path': args.get('file_path') or args.get('path'),
                                'new_content': new_content,
                                'reason': args.get('reason')
                            })
                        except Exception:
                            logger.error("tool_arg_parse_error", function="edit_file")
                    elif tool_call.function.name == "patch_file":
                        try:
                            args = json.loads(tool_call.function.arguments)
                            file_changes.append({
                                'type': 'patch',
                                'file_path': args.get('file_path') or args.get('path'),
                                'match_pattern': args.get('match_pattern'),
                                'replace_pattern': args.get('replace_pattern'),
                                'reason': args.get('reason')
                            })
                        except Exception:
                            logger.error("tool_arg_parse_error", function="patch_file")
            
            result = {
                'file_changes': file_changes,
                'analysis': message.content or "AI addressed PR feedback via tool calls"
            }
            
            self._save_to_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error("llm_call_failed", error=str(e))
            raise
    
    def fix_test_failures(self, original_changes, error_logs, codebase_files=None, job_id=None):
        """Analyze test failures and suggest fixes."""
        logger.info(
            "fixing_test_failures",
            original_changes_count=len(original_changes),
            error_logs_length=len(error_logs)
        )
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Edit a file to fix the test failures",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file to edit"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Explanation of the fix"
                            },
                            "new_content": {
                                "type": "string",
                                "description": "The complete new content for the file"
                            }
                        },
                        "required": ["file_path", "reason", "new_content"]
                    }
                }
            }
        ]
        
        changes_context = "\n\n".join([
            f"File: {c['file_path']}\n```\n{c['new_content'][:1500]}\n```"
            for c in original_changes
        ])
        
        system_prompt = """You are an expert at debugging test failures. Analyze the error logs and fix the code.

Rules:
1. Focus on the actual error, not unrelated changes
2. Maintain the original intent of the changes
3. Provide COMPLETE file content in new_content - include the ENTIRE file from start to end
4. NEVER minify, condense, summarize, or truncate the file content
5. Preserve EXACT formatting: indentation, line breaks, whitespace, and structure
6. Do NOT compress JSON, YAML, or any structured files into single lines
7. The new_content must be a drop-in replacement for the entire original file"""

        user_prompt = f"""The following code changes were made, but tests failed.

Original Changes:
{changes_context}

Test Error Logs:
{error_logs[-3000:]}

Analyze the errors and provide fixed versions of the files using edit_file."""

        logger.info("calling_llm_for_fix", model=self.model, prompt_length=len(user_prompt))
        logger.debug("fix_user_prompt", prompt=user_prompt[:3000])

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                tools=tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            logger.info(
                "fix_llm_response",
                has_tool_calls=bool(message.tool_calls),
                tool_calls_count=len(message.tool_calls) if message.tool_calls else 0
            )
            
            if message.content:
                logger.debug("fix_llm_content", content=message.content[:1000])
            
            file_changes = []
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    logger.debug(
                        "fix_tool_call_raw",
                        function_name=tool_call.function.name,
                        args_preview=tool_call.function.arguments[:500] if tool_call.function.arguments else None
                    )
                    
                    if tool_call.function.name == "edit_file":
                        try:
                            args = json.loads(tool_call.function.arguments)
                            # Some models use 'path' instead of 'file_path'
                            file_path = args.get('file_path') or args.get('path')
                            reason = args.get('reason', 'Fix test failure')
                            new_content = args.get('new_content', '')
                            
                            # Normalize newlines - some models return escaped newlines
                            if new_content:
                                new_content = new_content.replace('\\n', '\n')
                                new_content = new_content.replace('\\r\\n', '\n')
                                new_content = new_content.replace('\\r', '\n')
                            
                            logger.info("fix_parsed", file_path=file_path, reason=reason)
                            
                            file_changes.append({
                                'file_path': file_path,
                                'new_content': new_content,
                                'reason': reason
                            })
                        except json.JSONDecodeError as e:
                            logger.error("fix_parse_error", error=str(e))
            
            if file_changes:
                logger.info("fixes_complete", fixes_count=len(file_changes))
                return file_changes
            else:
                logger.warning("no_fixes_suggested", returning_original=True)
                return original_changes
                
        except Exception as e:
            logger.error("fix_call_failed", error=str(e))
            raise
