import json
from openai import OpenAI

class AIService:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        
    def analyze_issue_and_plan_changes(self, issue_title, issue_body, comment_body, codebase_files):
        codebase_context = "\n\n".join([
            f"File: {file['path']}\n```\n{file['content'][:2000]}\n```"
            for file in codebase_files
        ])
        
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
            }
        ]
        
        system_prompt = """You are an expert software engineer. Analyze the GitHub issue and suggest code changes by calling the edit_file function.
        
Rules:
1. Only suggest changes that directly address the issue
2. Maintain code style and conventions from the existing codebase
3. Make minimal, focused changes
4. Provide complete file content in new_content, not just diffs
5. Call edit_file for each file that needs to be changed"""

        user_prompt = f"""GitHub Issue: {issue_title}

Issue Description:
{issue_body}

User Comment:
{comment_body}

Available Codebase Files:
{codebase_context}

Analyze this issue and determine what code changes are needed. Use the edit_file function to specify the exact changes."""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            tools=tools,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        
        file_changes = []
        if message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.function.name == "edit_file":
                    args = json.loads(tool_call.function.arguments)
                    file_changes.append({
                        'file_path': args.get('file_path'),
                        'new_content': args.get('new_content'),
                        'reason': args.get('reason')
                    })
        
        return {
            'file_changes': file_changes,
            'analysis': message.content or "AI suggested file changes via tool calls"
        }
