import unittest
from unittest.mock import MagicMock, patch
import json
import sys

# Mock openai module before importing services that depend on it
sys.modules['openai'] = MagicMock()
sys.modules['docker'] = MagicMock()
sys.modules['boto3'] = MagicMock()
sys.modules['structlog'] = MagicMock()
sys.modules['flask'] = MagicMock()
sys.modules['flask_cors'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

from services.ai_service import AIService
from services.code_execution import CodeExecutionService, ExecutionResult

class TestAIExec(unittest.TestCase):
    def setUp(self):
        self.mock_client_instance = MagicMock()
        self.mock_client = MagicMock(return_value=self.mock_client_instance)
        
        # Patch OpenAI client creation in AIService
        self.patcher = patch('services.ai_service.OpenAI', self.mock_client)
        self.patcher.start()
        
        self.ai_service = AIService(api_key="fake_key", model="fake_model")
        self.ai_service.client = self.mock_client_instance # ensure usage of mock
        
        self.code_execution_service = MagicMock(spec=CodeExecutionService)

    def tearDown(self):
        self.patcher.stop()

    def test_exec_tool_usage(self):
        """Test that the AI service correctly calls the exec tool and handles the result."""
        
        # Mock responses from LLM
        # Turn 1: AI calls 'exec' tool
        message1 = MagicMock()
        message1.content = None
        
        func_mock = MagicMock()
        func_mock.name = 'exec' # accessing .name returns 'exec'
        func_mock.arguments = json.dumps({'command': 'ls -la'})
        
        tool_call = MagicMock(id='call_1')
        tool_call.function = func_mock
        
        message1.tool_calls = [tool_call]
        
        # Turn 2: AI provides final analysis after seeing exec output
        message2 = MagicMock()
        message2.content = "Analysis complete after ls -la"
        message2.tool_calls = [] # No more tools
        
        self.mock_client_instance.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=message1)]),
            MagicMock(choices=[MagicMock(message=message2)])
        ]
        
        # Mock code execution result
        exec_result = ExecutionResult(
            success=True, 
            stage='exec', 
            logs=['Output:', 'file1.py', 'file2.py']
        )
        exec_result.stdout = "file1.py\nfile2.py"
        self.code_execution_service.run_adhoc_command.return_value = exec_result
        
        repo_url = "https://github.com/fake/repo"
        
        # Call the service
        result = self.ai_service.analyze_issue_and_plan_changes(
            issue_title="Test Issue",
            issue_body="Test Body",
            comment_body="Test Comment",
            codebase_files=[{'path': 'README.md', 'content': 'Hello'}],
            repo_url=repo_url,
            code_execution_service=self.code_execution_service
        )
        
        # Assertions
        # 1. Verify run_adhoc_command was called with correct arguments
        self.code_execution_service.run_adhoc_command.assert_called_once_with(
            repo_url=repo_url,
            command='ls -la'
        )
        
        # 2. Verify LLM was called twice (once for tool call, once for final response)
        self.assertEqual(self.mock_client_instance.chat.completions.create.call_count, 2)
        
        # 3. Verify final result
        self.assertEqual(result['analysis'], "Analysis complete after ls -la")

if __name__ == '__main__':
    unittest.main()
