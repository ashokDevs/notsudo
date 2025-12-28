"""
Tests for AIService with OpenRouter integration.

Run with: pytest tests/test_ai_service.py -v
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock


class TestAIServiceUnit:
    """Unit tests with mocked API calls."""

    def test_init_with_api_key(self):
        """Should initialize with API key and default model."""
        with patch('services.ai_service.OpenAI') as mock_openai:
            from services.ai_service import AIService, DEFAULT_MODEL
            
            service = AIService(api_key='test-key')
            
            mock_openai.assert_called_once()
            assert service.model == DEFAULT_MODEL

    def test_init_with_custom_model(self):
        """Should accept custom model override."""
        with patch('services.ai_service.OpenAI'):
            from services.ai_service import AIService
            
            service = AIService(api_key='test-key', model='custom/model')
            
            assert service.model == 'custom/model'

    def test_analyze_issue_parses_tool_calls(self):
        """Should parse edit_file tool calls from response."""
        with patch('services.ai_service.OpenAI') as mock_openai:
            from services.ai_service import AIService
            
            # Mock the tool call response
            mock_tool_call = Mock()
            mock_tool_call.function.name = 'edit_file'
            mock_tool_call.function.arguments = '''
            {
                "file_path": "src/main.py",
                "new_content": "print('hello')",
                "reason": "Add greeting"
            }
            '''
            
            mock_message = Mock()
            mock_message.tool_calls = [mock_tool_call]
            mock_message.content = "Analysis complete"
            
            mock_response = Mock()
            mock_response.choices = [Mock(message=mock_message)]
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            service = AIService(api_key='test-key')
            result = service.analyze_issue_and_plan_changes(
                issue_title='Test issue',
                issue_body='Fix the bug',
                comment_body='@notsudo please fix',
                codebase_files=[{'path': 'main.py', 'content': 'old code'}]
            )
            
            assert len(result['file_changes']) == 1
            assert result['file_changes'][0]['file_path'] == 'src/main.py'
            assert 'hello' in result['file_changes'][0]['new_content']

    def test_analyze_issue_no_tool_calls(self):
        """Should return empty changes if no tool calls."""
        with patch('services.ai_service.OpenAI') as mock_openai:
            from services.ai_service import AIService
            
            mock_message = Mock()
            mock_message.tool_calls = None
            mock_message.content = "No changes needed"
            
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
            
            assert result['file_changes'] == []
            assert result['analysis'] == "No changes needed"


@pytest.mark.skipif(
    not os.environ.get('OPENROUTER_API_KEY'),
    reason="OPENROUTER_API_KEY not set - skipping integration test"
)
class TestAIServiceIntegration:
    """Integration tests that make real API calls. 
    
    Run with: OPENROUTER_API_KEY=your-key pytest tests/test_ai_service.py -v -k Integration
    """

    def test_real_api_call(self):
        """Make a real API call to verify connectivity."""
        from services.ai_service import AIService
        
        service = AIService(api_key=os.environ['OPENROUTER_API_KEY'])
        
        result = service.analyze_issue_and_plan_changes(
            issue_title='Add hello world',
            issue_body='Please add a simple hello world function',
            comment_body='@notsudo add a hello() function that prints hello world',
            codebase_files=[{
                'path': 'main.py',
                'content': '# Empty file\n'
            }]
        )
        
        # Should have some response
        assert 'file_changes' in result
        assert 'analysis' in result
        print(f"\n--- AI Response ---")
        print(f"Analysis: {result['analysis']}")
        print(f"File changes: {len(result['file_changes'])}")
        for change in result['file_changes']:
            print(f"  - {change['file_path']}: {change['reason']}")
