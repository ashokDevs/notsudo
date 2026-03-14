import json
import os
import hashlib
from groq import Groq
from utils.logger import get_logger
from services import db

DEFAULT_GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
MAX_FILE_CHARS = 2_000

logger = get_logger(__name__)


class GroqService:
    def __init__(self, api_key=None, model=None):
        self.client = Groq(api_key=api_key)
        self.model = model or DEFAULT_GROQ_MODEL
        self._cache = {}
        logger.info("groq_service_initialized", model=self.model)

    def _get_cache_key(self, method_name, **kwargs):
        serialized_args = json.dumps(kwargs, sort_keys=True)
        key_content = f"{method_name}:{serialized_args}"
        return hashlib.md5(key_content.encode()).hexdigest()

    def generate_branch_name(self, issue_number=None, issue_title=None, issue_body=None):
        logger.info("generating_branch_name", issue_number=issue_number)

        cache_key = self._get_cache_key("generate_branch_name", 
                                       issue_number=issue_number, 
                                       issue_title=issue_title, 
                                       issue_body=issue_body)
        if cache_key in self._cache:
            logger.info("cache_hit", method="generate_branch_name", key=cache_key)
            return self._cache[cache_key]

        logger.info("cache_miss", method="generate_branch_name", key=cache_key)

        system_prompt = """You are a git expert. Generate a short git branch name (3-5 words) for the given task.
Rules:
- Format: issue_number-short-description (if issue number is provided)
- Format: short-description (if no issue number is provided)
- Example with issue: 42-fix-login-validation
- Example without issue: add-readme-file
- Content: Lowercase, alphanumeric and hyphens only.
- Output: Return ONLY the branch name string."""

        prefix = f"Issue #{issue_number}: " if issue_number else ""
        user_prompt = f"{prefix}{issue_title}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Lower temperature for better formatting
                max_tokens=100
            )
            
            branch_name = response.choices[0].message.content.strip()
            # If the model is verbose, take only the first line/word
            if branch_name:
                branch_name = branch_name.split("\n")[0].split(" ")[0].strip()
            
            logger.debug("raw_branch_name_response", content=branch_name)
            
            # Sanitization logic
            import re
            
            def slugify(text):
                text = text.lower()
                text = re.sub(r'[^a-z0-9\-/_]', '', text.replace(" ", "-"))
                return text.strip("-")

            if not branch_name:
                # Fallback to title if AI response is empty or too short
                topic = slugify(issue_title)
                # Keep only first 5 words of topic for brevity
                topic = "-".join(topic.split("-")[:5])
                branch_name = f"{issue_number}-{topic}" if issue_number else topic
            else:
                branch_name = slugify(branch_name)
                # Ensure it starts with the issue number if provided
                if issue_number and not branch_name.startswith(str(issue_number)):
                    branch_name = f"{issue_number}-{branch_name}"
            
            logger.info("branch_name_generated", branch=branch_name)
            # Store in cache
            self._cache[cache_key] = branch_name
            return branch_name
            
        except Exception as e:
            logger.error("branch_name_generation_failed", error=str(e))
            return f"{issue_number}-ai-fix"

    def analyze_issue_and_plan_changes(self, issue_title, issue_body, comment_body, codebase_files, codebase_memory=None, custom_rules=None, repo_url=None, code_execution_service=None, job_id=None):
        logger.info(
            "analyzing_issue",
            issue_title=issue_title,
            comment_length=len(comment_body),
            codebase_files_count=len(codebase_files)
        )

        cache_key = self._get_cache_key("analyze_issue_and_plan_changes",
                                       issue_title=issue_title,
                                       issue_body=issue_body,
                                       comment_body=comment_body,
                                       codebase_files=codebase_files,
                                       codebase_memory=codebase_memory,
                                       custom_rules=custom_rules,
                                       repo_url=repo_url)
        if cache_key in self._cache:
            logger.info("cache_hit", method="analyze_issue_and_plan_changes", key=cache_key)
            return self._cache[cache_key]

        logger.info("cache_miss", method="analyze_issue_and_plan_changes", key=cache_key)

        codebase_context = "\n\n".join([
            f"File: {file['path']}\n```\n{file['content'][:MAX_FILE_CHARS]}\n```"
            for file in codebase_files
        ])
        
        logger.debug("codebase_context_built", context_length=len(codebase_context))

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Edit a file in the codebase with new content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file to edit"
                            },
                            "new_content": {
                                "type": "string",
                                "description": "The complete new content for the file"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Explanation of why this change is needed"
                            }
                        },
                        "required": ["file_path", "new_content", "reason"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List files in a directory to understand the project structure",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "The directory path to list files from (use empty string for root)"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "exec",
                    "description": "Execute a shell command to inspect the project or run diagnostics",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cmd": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Command and arguments as an array, e.g. ['ls', '-la']"
                            }
                        },
                        "required": ["cmd"]
                    }
                }
            }
        ]
        
        system_prompt = """You are an expert software engineer. Your task is to analyze the GitHub issue and suggest code changes.

IMPORTANT: You MUST use the edit_file tool to specify your changes. Do NOT output code in plain text.

Rules for using the edit_file tool:
1. Only suggest changes that directly address the issue
2. Maintain code style and conventions from the existing codebase
3. Make minimal, focused changes
4. Provide COMPLETE file content in new_content - include the ENTIRE file from start to end
5. Call edit_file for each file that needs to be changed
6. NEVER minify, condense, summarize, or truncate the file content
7. Preserve EXACT formatting: indentation, line breaks, whitespace, and structure
8. Do NOT compress JSON, YAML, or any structured files into single lines
9. The new_content must be a drop-in replacement for the entire original file

Always respond by calling the edit_file tool."""

        if codebase_memory:
            system_prompt += f"\n\nRepository Context & Memory:\n{json.dumps(codebase_memory, indent=2)}"

        if custom_rules and custom_rules.strip():
            system_prompt += f"\n\nAdditional Custom Rules:\n{custom_rules}"

        user_prompt = f"""GitHub Issue: {issue_title}

Issue Description:
{issue_body}

User Comment:
{comment_body}

Available Codebase Files:
{codebase_context}

Analyze this issue and determine what code changes are needed. Use the edit_file function to specify the exact changes.\""""

        if job_id:
            db.insert_job_log({
                'job_id': job_id,
                'role': 'user',
                'type': 'message',
                'content': f"**Issue Analysis Request**\n\n**Title:** {issue_title}\n\n**Body:**\n{issue_body}\n\n**Comment:**\n{comment_body}",
                'metadata': {'file_count': len(codebase_files)}
            })

        logger.info("calling_groq_llm", model=self.model, prompt_length=len(user_prompt))
        logger.debug("system_prompt", prompt=system_prompt)
        logger.debug("user_prompt", prompt=user_prompt[:5_000])

        max_retries = 3
        temperature = 1.0
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    tools=tools,
                    tool_choice="required",  # Force proper tool calling
                    temperature=temperature,
                    parallel_tool_calls=False  # Reduce complexity for better JSON generation
                )
                
                message = response.choices[0].message

                logger.info(
                    "groq_response_received",
                    has_tool_calls=bool(message.tool_calls),
                    tool_calls_count=len(message.tool_calls) if message.tool_calls else 0,
                    content_length=len(message.content) if message.content else 0
                )

                if message.content:
                    logger.debug("groq_content", content=message.content[:MAX_FILE_CHARS])

                if message.tool_calls:
                    for i, tc in enumerate(message.tool_calls):
                        logger.info(
                            "tool_call_raw",
                            index=i,
                            function_name=tc.function.name,
                            arguments_preview=tc.function.arguments[:500] if tc.function.arguments else None
                        )

                file_changes = []
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        logger.debug(
                            "processing_tool_call",
                            function_name=tool_call.function.name,
                            raw_args=tool_call.function.arguments[:1_000] if tool_call.function.arguments else None
                        )

                        if tool_call.function.name == "edit_file":
                            try:
                                args = json.loads(tool_call.function.arguments)
                                file_path = args.get('file_path') or args.get('path')
                                reason = args.get('reason')
                                new_content = args.get('new_content', '')
                                
                                logger.info(
                                    "file_change_parsed",
                                    file_path=file_path,
                                    reason=reason,
                                    content_length=len(new_content),
                                    content_preview=new_content[:200] if new_content else None
                                )
                                
                                file_changes.append({
                                    'file_path': file_path,
                                    'new_content': new_content,
                                    'reason': reason
                                })

                                if job_id:
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
                            except json.JSONDecodeError as e:
                                logger.error(
                                    "tool_call_parse_error",
                                    error=str(e),
                                    raw_args=tool_call.function.arguments[:500]
                                )
                        elif tool_call.function.name == "exec":
                            logger.info("groq_exec_tool_called", raw_args=tool_call.function.arguments)

                        else:
                            logger.warning(
                                "unknown_tool_call",
                                function_name=tool_call.function.name
                            )

                else:
                    logger.warning("no_tool_calls_in_response", content=message.content[:500] if message.content else None)
                
                logger.info("analysis_complete", total_changes=len(file_changes))

                result = {
                    'file_changes': file_changes,
                    'analysis': message.content or "AI suggested file changes via tool calls"
                }
                
                if job_id:
                    db.insert_job_log({
                        'job_id': job_id,
                        'role': 'assistant',
                        'type': 'message',
                        'content': message.content or "Analysis complete. Suggested changes prepared.",
                        'metadata': {'changes_count': len(file_changes)}
                    })
                
                # Store in cache
                self._cache[cache_key] = result
                return result
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # Check if this is a tool call generation failure (400 error)
                is_tool_use_failed = (
                    hasattr(e, 'status_code') and e.status_code == 400 and
                    'tool_use_failed' in error_str
                )
                
                if is_tool_use_failed:
                    # Log the failed generation for debugging
                    logger.warning(
                        "tool_use_failed_retry",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        temperature=temperature,
                        error=error_str[:500]
                    )
                    
                    if attempt < max_retries - 1:
                        # Decrease temperature for next attempt (per Groq docs)
                        # Lower temperature = more deterministic = less JSON escaping issues
                        temperature = max(temperature - 0.3, 0.2)
                        logger.info(
                            "retrying_with_lower_temperature",
                            new_temperature=temperature,
                            next_attempt=attempt + 2
                        )
                        continue
                
                # Not a retryable error or out of retries
                logger.error("groq_call_failed", error=error_str, model=self.model, attempts=attempt + 1)
                raise
        
        # If we exhausted retries without success
        if last_error:
            raise last_error

    def analyze_pr_comment(self, pr_title, pr_body, comment_body, codebase_files, codebase_memory=None, custom_rules=None, job_id=None):
        logger.info("analyzing_pr_comment_groq", pr_title=pr_title)

        return self.analyze_issue_and_plan_changes(
            issue_title=f"PR: {pr_title}",
            issue_body=pr_body,
            comment_body=comment_body,
            codebase_files=codebase_files,
            codebase_memory=codebase_memory,
            custom_rules=custom_rules,
            job_id=job_id
        )

    def fix_test_failures(self, original_changes, error_logs, codebase_files=None, job_id=None):
        logger.info(
            "fixing_test_failures",
            original_changes_count=len(original_changes),
            error_logs_length=len(error_logs)
        )

        cache_key = self._get_cache_key("fix_test_failures",
                                       original_changes=original_changes,
                                       error_logs=error_logs,
                                       codebase_files=codebase_files)
        if cache_key in self._cache:
            logger.info("cache_hit", method="fix_test_failures", key=cache_key)
            return self._cache[cache_key]

        logger.info("cache_miss", method="fix_test_failures", key=cache_key)

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
                            "new_content": {
                                "type": "string",
                                "description": "The complete new content for the file"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Explanation of the fix"
                            }
                        },
                        "required": ["file_path", "new_content", "reason"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List files in a directory to understand the project structure",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "The directory path to list files from (use empty string for root)"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "exec",
                    "description": "Execute a shell command to inspect the project or run diagnostics",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cmd": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Command and arguments as an array, e.g. ['ls', '-la']"
                            }
                        },
                        "required": ["cmd"]
                    }
                }
            }
        ]
        
        changes_context = "\n\n".join([
            f"File: {c['file_path']}\n```\n{c['new_content'][:1500]}\n```"
            for c in original_changes
        ])
        
        system_prompt = """You are an expert at debugging test failures. Analyze the error logs and fix the code.

IMPORTANT: You MUST use the edit_file tool to provide fixed file content. Do NOT output code in plain text.

Rules for using the edit_file tool:
1. Focus on the actual error, not unrelated changes
2. Maintain the original intent of the changes
3. Provide COMPLETE file content in new_content - include the ENTIRE file from start to end
4. NEVER minify, condense, summarize, or truncate the file content
5. Preserve EXACT formatting: indentation, line breaks, whitespace, and structure
6. Do NOT compress JSON, YAML, or any structured files into single lines
7. The new_content must be a drop-in replacement for the entire original file

Always respond by calling the edit_file tool."""

        user_prompt = f"""The following code changes were made, but tests failed.

Original Changes:
{changes_context}

Test Error Logs:
{error_logs[-3000:]}

Analyze the errors and provide fixed versions of the files using edit_file."""

        if job_id:
            db.insert_job_log({
                'job_id': job_id,
                'role': 'user',
                'type': 'message',
                'content': f"**Fixing Test Failures**\n\nErrors:\n```\n{error_logs[-1000:]}\n```",
                'metadata': {'original_changes_count': len(original_changes)}
            })

        logger.info("calling_groq_for_fix", model=self.model, prompt_length=len(user_prompt))
        logger.debug("fix_user_prompt", prompt=user_prompt[:3_000])

        max_retries = 3
        temperature = 1.0
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    tools=tools,
                    tool_choice="required",  # Force proper tool calling
                    temperature=temperature,
                    parallel_tool_calls=False  # Reduce complexity for better JSON generation
                )
                
                message = response.choices[0].message

                logger.info(
                    "fix_groq_response",
                    has_tool_calls=bool(message.tool_calls),
                    tool_calls_count=len(message.tool_calls) if message.tool_calls else 0
                )

                if message.content:
                    logger.debug("fix_groq_content", content=message.content[:1_000])

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
                                file_path = args.get('file_path') or args.get('path')
                                reason = args.get('reason', 'Fix test failure')
                                
                                logger.info("fix_parsed", file_path=file_path, reason=reason)
                                
                                file_changes.append({
                                    'file_path': file_path,
                                    'new_content': args.get('new_content'),
                                    'reason': reason
                                })
                                
                                if job_id:
                                    db.insert_job_log({
                                        'job_id': job_id,
                                        'role': 'assistant',
                                        'type': 'file_change',
                                        'content': reason,
                                        'metadata': {
                                            'file_path': file_path,
                                            'new_content': args.get('new_content')
                                        }
                                    })
                            except json.JSONDecodeError as e:
                                logger.error("fix_parse_error", error=str(e))

                if file_changes:
                    logger.info("fixes_complete", fixes_count=len(file_changes))

                    merged_changes = []
                    original_paths = {c['file_path'] for c in original_changes}
                    fix_paths = {c['file_path'] for c in file_changes}

                    for original in original_changes:
                        if original['file_path'] in fix_paths:
                            # Find the fix for this file
                            fix = next(f for f in file_changes if f['file_path'] == original['file_path'])
                            merged_changes.append(fix)
                            logger.info("fix_merged_with_original", file=original['file_path'])
                        else:
                            merged_changes.append(original)

                    for fix in file_changes:
                        if fix['file_path'] not in original_paths:
                            merged_changes.append(fix)
                            logger.info("fix_added_new_file", file=fix['file_path'])

                    logger.info("fixes_merged", 
                               original_count=len(original_changes),
                               fix_count=len(file_changes),
                               merged_count=len(merged_changes))
                    self._cache[cache_key] = merged_changes
                    return merged_changes
                else:
                    logger.warning("no_fixes_suggested", returning_original=True)
                    self._cache[cache_key] = original_changes
                    return original_changes
                    
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # Check if this is a tool call generation failure (400 error)
                is_tool_use_failed = (
                    hasattr(e, 'status_code') and e.status_code == 400 and
                    'tool_use_failed' in error_str
                )
                
                if is_tool_use_failed:
                    logger.warning(
                        "fix_tool_use_failed_retry",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        temperature=temperature,
                        error=error_str[:500]
                    )
                    
                    if attempt < max_retries - 1:
                        temperature = max(temperature - 0.3, 0.2)
                        logger.info(
                            "fix_retrying_with_lower_temperature",
                            new_temperature=temperature,
                            next_attempt=attempt + 2
                        )
                        continue
                
                # Not a retryable error or out of retries
                logger.error("fix_groq_call_failed", error=error_str, attempts=attempt + 1)
                raise
        
        # If we exhausted retries without success
        if last_error:
            raise last_error
