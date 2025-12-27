"""
Comprehensive tests for AI Service function calling with mocked responses.

These tests verify the function calling logic without making real API calls.
Run with: pytest tests/test_function_calling.py -v
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock


class TestFunctionCallingParsing:
    """Tests for parsing tool calls from AI responses."""

    def test_parse_multiple_tool_calls(self):
        """Should correctly parse multiple edit_file tool calls."""
        with patch('services.ai_service.OpenAI') as mock_openai:
            from services.ai_service import AIService
            
            # Create multiple tool calls
            tool_call_1 = Mock()
            tool_call_1.function.name = 'edit_file'
            tool_call_1.function.arguments = json.dumps({
                "file_path": "src/main.py",
                "new_content": "print('hello')",
                "reason": "Add main function"
            })
            
            tool_call_2 = Mock()
            tool_call_2.function.name = 'edit_file'
            tool_call_2.function.arguments = json.dumps({
                "file_path": "src/utils.py",
                "new_content": "def helper(): pass",
                "reason": "Add helper"
            })
            
            tool_call_3 = Mock()
            tool_call_3.function.name = 'edit_file'
            tool_call_3.function.arguments = json.dumps({
                "file_path": "tests/test_main.py",
                "new_content": "def test_main(): assert True",
                "reason": "Add test"
            })
            
            mock_message = Mock()
            mock_message.tool_calls = [tool_call_1, tool_call_2, tool_call_3]
            mock_message.content = "Made 3 changes"
            
            mock_response = Mock()
            mock_response.choices = [Mock(message=mock_message)]
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            service = AIService(api_key='test-key')
            result = service.analyze_issue_and_plan_changes(
                issue_title='Add features',
                issue_body='Need to add main, utils, and tests',
                comment_body='@bot implement this',
                codebase_files=[{'path': 'README.md', 'content': '# Project'}]
            )
            
            assert len(result['file_changes']) == 3
            assert result['file_changes'][0]['file_path'] == 'src/main.py'
            assert result['file_changes'][1]['file_path'] == 'src/utils.py'
            assert result['file_changes'][2]['file_path'] == 'tests/test_main.py'

    def test_parse_malformed_json_in_tool_call(self):
        """Should handle malformed JSON in tool call arguments gracefully."""
        with patch('services.ai_service.OpenAI') as mock_openai:
            from services.ai_service import AIService
            
            # One valid and one malformed tool call
            valid_call = Mock()
            valid_call.function.name = 'edit_file'
            valid_call.function.arguments = json.dumps({
                "file_path": "valid.py",
                "new_content": "content",
                "reason": "valid"
            })
            
            malformed_call = Mock()
            malformed_call.function.name = 'edit_file'
            malformed_call.function.arguments = '{invalid json: "missing quotes}'
            
            mock_message = Mock()
            mock_message.tool_calls = [valid_call, malformed_call]
            mock_message.content = "Analysis"
            
            mock_response = Mock()
            mock_response.choices = [Mock(message=mock_message)]
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            service = AIService(api_key='test-key')
            result = service.analyze_issue_and_plan_changes(
                issue_title='Test',
                issue_body='Body',
                comment_body='Comment',
                codebase_files=[]
            )
            
            # Should have parsed the valid one, skipped the malformed
            assert len(result['file_changes']) == 1
            assert result['file_changes'][0]['file_path'] == 'valid.py'

    def test_handle_unknown_function_names(self):
        """Should skip unknown function names and only process edit_file."""
        with patch('services.ai_service.OpenAI') as mock_openai:
            from services.ai_service import AIService
            
            edit_call = Mock()
            edit_call.function.name = 'edit_file'
            edit_call.function.arguments = json.dumps({
                "file_path": "file.py",
                "new_content": "code",
                "reason": "change"
            })
            
            unknown_call = Mock()
            unknown_call.function.name = 'delete_file'  # Unknown function
            unknown_call.function.arguments = '{"path": "old.py"}'
            
            another_unknown = Mock()
            another_unknown.function.name = 'run_command'  # Another unknown
            another_unknown.function.arguments = '{"cmd": "ls"}'
            
            mock_message = Mock()
            mock_message.tool_calls = [unknown_call, edit_call, another_unknown]
            mock_message.content = "Mixed tools"
            
            mock_response = Mock()
            mock_response.choices = [Mock(message=mock_message)]
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            service = AIService(api_key='test-key')
            result = service.analyze_issue_and_plan_changes(
                issue_title='Test',
                issue_body='Body',
                comment_body='Comment',
                codebase_files=[]
            )
            
            # Should only have the edit_file change
            assert len(result['file_changes']) == 1
            assert result['file_changes'][0]['file_path'] == 'file.py'

    def test_handle_empty_tool_call_arguments(self):
        """Should handle empty or null arguments gracefully."""
        with patch('services.ai_service.OpenAI') as mock_openai:
            from services.ai_service import AIService
            
            empty_args_call = Mock()
            empty_args_call.function.name = 'edit_file'
            empty_args_call.function.arguments = '{}'
            
            valid_call = Mock()
            valid_call.function.name = 'edit_file'
            valid_call.function.arguments = json.dumps({
                "file_path": "file.py",
                "new_content": "code",
                "reason": "add"
            })
            
            mock_message = Mock()
            mock_message.tool_calls = [empty_args_call, valid_call]
            mock_message.content = "Done"
            
            mock_response = Mock()
            mock_response.choices = [Mock(message=mock_message)]
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            service = AIService(api_key='test-key')
            result = service.analyze_issue_and_plan_changes(
                issue_title='Test',
                issue_body='Body',
                comment_body='Comment',
                codebase_files=[]
            )
            
            # Both parse, but empty one has None values
            assert len(result['file_changes']) == 2
            # Valid one should have proper values
            assert result['file_changes'][1]['file_path'] == 'file.py'

    def test_content_fallback_when_no_tool_calls(self):
        """Should return content as analysis when no tool calls."""
        with patch('services.ai_service.OpenAI') as mock_openai:
            from services.ai_service import AIService
            
            mock_message = Mock()
            mock_message.tool_calls = None
            mock_message.content = "I cannot make changes because the issue is unclear"
            
            mock_response = Mock()
            mock_response.choices = [Mock(message=mock_message)]
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            service = AIService(api_key='test-key')
            result = service.analyze_issue_and_plan_changes(
                issue_title='Unclear issue',
                issue_body='???',
                comment_body='@bot help',
                codebase_files=[]
            )
            
            assert result['file_changes'] == []
            assert "cannot make changes" in result['analysis']


class TestFixTestFailures:
    """Tests for the fix_test_failures method."""

    def test_fix_test_failures_returns_fixes(self):
        """Should return fixed file changes when AI suggests fixes."""
        with patch('services.ai_service.OpenAI') as mock_openai:
            from services.ai_service import AIService
            
            fix_call = Mock()
            fix_call.function.name = 'edit_file'
            fix_call.function.arguments = json.dumps({
                "file_path": "src/main.py",
                "new_content": "print('fixed hello')",
                "reason": "Fixed syntax error"
            })
            
            mock_message = Mock()
            mock_message.tool_calls = [fix_call]
            mock_message.content = "Fixed the issue"
            
            mock_response = Mock()
            mock_response.choices = [Mock(message=mock_message)]
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            service = AIService(api_key='test-key')
            
            original_changes = [{
                'file_path': 'src/main.py',
                'new_content': 'print("hello)',  # Missing quote
                'reason': 'Add greeting'
            }]
            
            error_logs = """
            File "src/main.py", line 1
                print("hello)
                      ^
            SyntaxError: unterminated string literal
            """
            
            result = service.fix_test_failures(original_changes, error_logs)
            
            assert len(result) == 1
            assert result[0]['file_path'] == 'src/main.py'
            assert 'fixed' in result[0]['new_content']

    def test_fix_test_failures_returns_original_when_no_fixes(self):
        """Should return original changes if AI suggests no fixes."""
        with patch('services.ai_service.OpenAI') as mock_openai:
            from services.ai_service import AIService
            
            mock_message = Mock()
            mock_message.tool_calls = None  # No tool calls
            mock_message.content = "I couldn't find a fix"
            
            mock_response = Mock()
            mock_response.choices = [Mock(message=mock_message)]
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            service = AIService(api_key='test-key')
            
            original_changes = [{
                'file_path': 'src/main.py',
                'new_content': 'print("hello")',
                'reason': 'Add greeting'
            }]
            
            result = service.fix_test_failures(original_changes, "Some error")
            
            # Should return original when no fixes suggested
            assert result == original_changes

    def test_fix_test_failures_handles_multiple_file_fixes(self):
        """Should handle fixes across multiple files."""
        with patch('services.ai_service.OpenAI') as mock_openai:
            from services.ai_service import AIService
            
            fix_call_1 = Mock()
            fix_call_1.function.name = 'edit_file'
            fix_call_1.function.arguments = json.dumps({
                "file_path": "src/main.py",
                "new_content": "from utils import helper\nhelper()",
                "reason": "Fixed import"
            })
            
            fix_call_2 = Mock()
            fix_call_2.function.name = 'edit_file'
            fix_call_2.function.arguments = json.dumps({
                "file_path": "src/utils.py",
                "new_content": "def helper():\n    return 'working'",
                "reason": "Fixed function definition"
            })
            
            mock_message = Mock()
            mock_message.tool_calls = [fix_call_1, fix_call_2]
            mock_message.content = "Fixed both files"
            
            mock_response = Mock()
            mock_response.choices = [Mock(message=mock_message)]
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            service = AIService(api_key='test-key')
            
            original = [{'file_path': 'src/main.py', 'new_content': 'broken', 'reason': 'initial'}]
            
            result = service.fix_test_failures(original, "ImportError: utils")
            
            assert len(result) == 2
            file_paths = [r['file_path'] for r in result]
            assert 'src/main.py' in file_paths
            assert 'src/utils.py' in file_paths


class TestToolDefinition:
    """Tests verifying the tool definition structure."""

    def test_tool_definition_structure(self):
        """Verify the edit_file tool is defined correctly."""
        with patch('services.ai_service.OpenAI') as mock_openai:
            from services.ai_service import AIService
            
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            # Capture the tools argument
            mock_client.chat.completions.create.return_value = Mock(
                choices=[Mock(message=Mock(tool_calls=None, content="OK"))]
            )
            
            service = AIService(api_key='test-key')
            service.analyze_issue_and_plan_changes(
                issue_title='Test',
                issue_body='Body',
                comment_body='Comment',
                codebase_files=[]
            )
            
            # Get the call arguments
            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            
            assert 'tools' in call_kwargs
            tools = call_kwargs['tools']
            
            assert len(tools) == 1
            tool = tools[0]
            
            assert tool['type'] == 'function'
            assert tool['function']['name'] == 'edit_file'
            
            params = tool['function']['parameters']
            assert 'file_path' in params['properties']
            assert 'new_content' in params['properties']
            assert 'reason' in params['properties']
            assert params['required'] == ['file_path', 'new_content', 'reason']


class TestPromptConstruction:
    """Tests for prompt construction."""

    def test_codebase_context_truncation(self):
        """Should truncate large file contents in codebase context."""
        with patch('services.ai_service.OpenAI') as mock_openai:
            from services.ai_service import AIService
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = Mock(
                choices=[Mock(message=Mock(tool_calls=None, content="OK"))]
            )
            mock_openai.return_value = mock_client
            
            # Create a very large file content
            large_content = "x" * 10000
            
            service = AIService(api_key='test-key')
            service.analyze_issue_and_plan_changes(
                issue_title='Test',
                issue_body='Body',
                comment_body='Comment',
                codebase_files=[{'path': 'large.py', 'content': large_content}]
            )
            
            # Get the user prompt from call
            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            messages = call_kwargs['messages']
            user_message = messages[1]['content']
            
            # Content should be truncated to first 2000 chars
            assert len(user_message) < len(large_content)

    def test_multiple_files_in_context(self):
        """Should include multiple files in codebase context."""
        with patch('services.ai_service.OpenAI') as mock_openai:
            from services.ai_service import AIService
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = Mock(
                choices=[Mock(message=Mock(tool_calls=None, content="OK"))]
            )
            mock_openai.return_value = mock_client
            
            files = [
                {'path': 'main.py', 'content': 'print("main")'},
                {'path': 'utils.py', 'content': 'def util(): pass'},
                {'path': 'config.py', 'content': 'CONFIG = {}'},
            ]
            
            service = AIService(api_key='test-key')
            service.analyze_issue_and_plan_changes(
                issue_title='Test',
                issue_body='Body',
                comment_body='Comment',
                codebase_files=files
            )
            
            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            user_message = call_kwargs['messages'][1]['content']
            
            # All files should be in the context
            assert 'main.py' in user_message
            assert 'utils.py' in user_message
            assert 'config.py' in user_message
