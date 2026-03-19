"""
Shared utilities and constants for CloudAgent backend services.

This module consolidates common definitions to avoid duplication across
ai_service.py and groq_service.py.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


# ======================
# Model Configuration
# ======================

DEFAULT_OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
DEFAULT_GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

AVAILABLE_MODELS = {
    'claude-3-5-sonnet': {
        'id': 'anthropic/claude-3.5-sonnet',
        'name': 'Claude 3.5 Sonnet',
        'provider': 'anthropic'
    },
}


# ======================
# Context Limits (Cost Control)
# ======================

MAX_FILE_CHARS = 2000
MAX_TOTAL_CONTEXT_CHARS = 50000  # ~12,500 tokens, prevents runaway costs
MAX_CONVERSATION_TURNS = 5
MAX_VALIDATION_RETRIES = 5  # Reduced from 10


# ======================
# Abstract Base Class
# ======================

class AIServiceBase(ABC):
    """
    Abstract base class for AI services.
    
    Both AIService (OpenRouter) and GroqService must implement these methods
    to ensure consistent behavior across different LLM providers.
    """
    
    @abstractmethod
    def generate_branch_name(self, issue_number=None, issue_title=None, issue_body=None) -> str:
        """Generate a descriptive git branch name."""
        pass
    
    @abstractmethod
    def analyze_issue_and_plan_changes(
        self, 
        issue_title: str, 
        issue_body: str, 
        comment_body: str, 
        codebase_files: List[Dict[str, str]],
        codebase_memory: Optional[Dict] = None,
        custom_rules: Optional[str] = None,
        repo_url: Optional[str] = None,
        code_execution_service: Optional[Any] = None,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze an issue and return planned file changes."""
        pass
    
    @abstractmethod
    def analyze_pr_comment(
        self,
        pr_title: str,
        pr_body: str,
        comment_body: str,
        codebase_files: List[Dict[str, str]],
        codebase_memory: Optional[Dict] = None,
        custom_rules: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze PR feedback and return planned file changes."""
        pass
    
    @abstractmethod
    def fix_test_failures(
        self,
        original_changes: List[Dict[str, Any]],
        error_logs: str,
        codebase_files: Optional[List[Dict[str, str]]] = None,
        job_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Analyze test failures and return fixed file changes."""
        pass
    
    def resolve_merge_conflicts(
        self,
        conflicted_files: List[Dict[str, str]],
        job_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Resolve merge conflicts. Optional - not all services implement this."""
        raise NotImplementedError("This AI service does not support merge conflict resolution")


# ======================
# Tool Definitions
# ======================

def get_edit_file_tool() -> Dict[str, Any]:
    """Edit file tool definition for LLM function calling."""
    return {
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
    }


def get_patch_file_tool() -> Dict[str, Any]:
    """Patch file tool for targeted structural transformations."""
    return {
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


def get_exec_tool() -> Dict[str, Any]:
    """Exec tool for shell command execution."""
    return {
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
    }


def get_screenshot_tool() -> Dict[str, Any]:
    """Screenshot tool for UI verification."""
    return {
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
    }


def get_list_files_tool() -> Dict[str, Any]:
    """List files tool for directory exploration."""
    return {
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
    }


def get_standard_tools(include_exec: bool = False, include_screenshot: bool = False) -> List[Dict[str, Any]]:
    """Get standard tool set for AI services."""
    tools = [get_edit_file_tool(), get_patch_file_tool()]
    if include_exec:
        tools.append(get_exec_tool())
    if include_screenshot:
        tools.append(get_screenshot_tool())
    return tools


# ======================
# System Prompts
# ======================

BASE_SYSTEM_PROMPT = """You are an expert software engineer. Analyze the task and suggest code changes.

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

Rules:
1. PREFER patch_file for targeted changes - it's safer and more precise
2. Use edit_file only when patch_file cannot express the change
3. Make minimal, focused changes that directly address the issue
4. Maintain code style and conventions from the existing codebase"""

ISSUE_ANALYSIS_PROMPT = BASE_SYSTEM_PROMPT + """

3. **exec** - For EXPLORATION and VERIFICATION (if available):
   - Run shell commands to check file structure, grep for patterns, or run tests.
   - Use this to gather more information if the provided context is insufficient.
   - NOTE: This runs in a sandbox.

4. **take_screenshot** - For UI VERIFICATION:
   - Capture a screenshot of the running application to verify visual changes.
   - Useful for frontend tasks to verify the UI.

5. Analyze this issue and determine what code changes are needed. Use patch_file for specific modifications and edit_file only for new files. You can use 'exec' to verify your understanding before proposing changes."""

PR_FEEDBACK_PROMPT = BASE_SYSTEM_PROMPT + """

Additional rules for PR feedback:
1. Address the user's comments directly.
2. Make minimal, focused changes that directly address the feedback."""

FIX_TEST_FAILURES_PROMPT = """You are an expert at debugging test failures. Analyze the error logs and fix the code.

Rules:
1. Focus on the actual error, not unrelated changes
2. Maintain the original intent of the changes
3. Provide COMPLETE file content in new_content - include the ENTIRE file from start to end
4. NEVER minify, condense, summarize, or truncate the file content
5. Preserve EXACT formatting: indentation, line breaks, whitespace, and structure
6. Do NOT compress JSON, YAML, or any structured files into single lines
7. The new_content must be a drop-in replacement for the entire original file"""

MERGE_CONFLICT_PROMPT = """You are an expert software engineer. Your task is to resolve git merge conflicts.
The input files contain standard git conflict markers (<<<<<<<, =======, >>>>>>>).

Rules:
1. Analyze the conflicting sections.
2. Resolve the conflicts by intelligently combining changes or choosing the correct version.
3. Remove all conflict markers.
4. Provide the COMPLETE resolved file content in new_content.
5. Preserve the formatting and structure of the file.
6. Return the full file content, not just the fixed section."""


# ======================
# Helper Functions
# ======================

def build_codebase_context(codebase_files: List[Dict[str, str]], 
                           max_file_chars: int = MAX_FILE_CHARS,
                           max_total_chars: int = MAX_TOTAL_CONTEXT_CHARS) -> str:
    """
    Build codebase context string with truncation for large files.
    
    Args:
        codebase_files: List of dicts with 'path' and 'content' keys
        max_file_chars: Max chars per file
        max_total_chars: Max total context chars (cost control)
        
    Returns:
        Formatted context string
    """
    context_parts = []
    total_chars = 0
    
    for file in codebase_files:
        content = file['content']
        is_truncated = len(content) > max_file_chars
        
        if is_truncated:
            file_context = f"File: {file['path']} [TRUNCATED - showing {max_file_chars}/{len(content)} chars]\n```\n{content[:max_file_chars]}\n```"
        else:
            file_context = f"File: {file['path']}\n```\n{content}\n```"
        
        # Check total context limit
        if total_chars + len(file_context) > max_total_chars:
            context_parts.append(f"... (remaining {len(codebase_files) - len(context_parts)} files omitted due to context limit)")
            break
            
        context_parts.append(file_context)
        total_chars += len(file_context)
    
    return "\n\n".join(context_parts)


def normalize_newlines(content: str) -> str:
    """Normalize newline characters in content from LLM."""
    if content:
        content = content.replace('\\n', '\n')
        content = content.replace('\\r\\n', '\n')
        content = content.replace('\\r', '\n')
    return content


def parse_file_path(args: Dict[str, Any]) -> Optional[str]:
    """Extract file path from tool call args (handles both 'file_path' and 'path')."""
    return args.get('file_path') or args.get('path')


def build_user_prompt_for_issue(issue_title: str, issue_body: str, comment_body: str, codebase_context: str) -> str:
    """Build the user prompt for issue analysis."""
    return f"""GitHub Issue: {issue_title}

Issue Description:
{issue_body}

User Comment:
{comment_body}

Available Codebase Files:
{codebase_context}

Analyze this issue and determine what code changes are needed. Use the available tools to specify the exact changes, preferring patch_file where possible."""


def build_user_prompt_for_pr(pr_title: str, pr_body: str, comment_body: str, codebase_context: str) -> str:
    """Build the user prompt for PR comment analysis."""
    return f"""PR Title: {pr_title}
PR Description:
{pr_body}

User Comment on PR:
{comment_body}

Current File Contents:
{codebase_context}

Analyze the comment and update the code to address the feedback. Use the available tools to make changes."""


def build_user_prompt_for_fix(changes_context: str, error_logs: str) -> str:
    """Build the user prompt for test failure fixes."""
    return f"""The following code changes were made, but tests failed.

Original Changes:
{changes_context}

Test Error Logs:
{error_logs[-3000:]}

Analyze the errors and provide fixed versions of the files using edit_file."""


def add_memory_and_rules_to_prompt(base_prompt: str, codebase_memory: Optional[Dict] = None, custom_rules: Optional[str] = None) -> str:
    """Add codebase memory and custom rules to a system prompt."""
    import json
    result = base_prompt
    
    if codebase_memory:
        result += f"\n\nRepository Context & Memory:\n{json.dumps(codebase_memory, indent=2)}"
    
    if custom_rules and custom_rules.strip():
        result += f"\n\nAdditional Custom Rules:\n{custom_rules}"
    
    return result

