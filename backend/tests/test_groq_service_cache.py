import pytest
import json
from unittest.mock import Mock, patch
from services.groq_service import GroqService

class TestGroqServiceCache:
    @pytest.fixture
    def mock_groq(self):
        with patch('services.groq_service.Groq') as mock:
            yield mock

    def test_cache_key_consistency(self, mock_groq):
        service = GroqService(api_key="test")
        key1 = service._get_cache_key("test_method", a=1, b=2)
        key2 = service._get_cache_key("test_method", b=2, a=1)
        assert key1 == key2

    def test_generate_branch_name_caching(self, mock_groq):
        mock_client = mock_groq.return_value
        mock_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="42-test-branch"))]
        )
        
        service = GroqService(api_key="test")
        
        # First call - cache miss
        res1 = service.generate_branch_name(42, "Title", "Body")
        assert res1 == "42-test-branch"
        assert mock_client.chat.completions.create.call_count == 1
        
        # Second call - cache hit
        res2 = service.generate_branch_name(42, "Title", "Body")
        assert res2 == "42-test-branch"
        assert mock_client.chat.completions.create.call_count == 1  # Still 1
        
        # Multi-call with different params
        service.generate_branch_name(43, "Title", "Body")
        assert mock_client.chat.completions.create.call_count == 2

    def test_analyze_issue_caching(self, mock_groq):
        mock_client = mock_groq.return_value
        
        # Mock tool call response
        mock_tool_call = Mock()
        mock_tool_call.function.name = 'edit_file'
        mock_tool_call.function.arguments = json.dumps({
            "file_path": "test.py",
            "new_content": "print('cached')",
            "reason": "testing"
        })
        
        mock_message = Mock()
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = "Analysis"
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_response
        
        service = GroqService(api_key="test")
        
        # First call
        res1 = service.analyze_issue_and_plan_changes("Title", "Body", "Comment", [])
        assert len(res1['file_changes']) == 1
        assert mock_client.chat.completions.create.call_count == 1
        
        # Second call
        res2 = service.analyze_issue_and_plan_changes("Title", "Body", "Comment", [])
        assert res2 == res1
        assert mock_client.chat.completions.create.call_count == 1

    def test_fix_test_failures_caching(self, mock_groq):
        mock_client = mock_groq.return_value
        
        mock_message = Mock()
        mock_message.tool_calls = None
        mock_message.content = "No fix needed"
        
        mock_response = Mock()
        mock_response.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_response
        
        service = GroqService(api_key="test")
        
        original_changes = [{'file_path': 'test.py', 'new_content': 'code', 'reason': 'initial'}]
        
        # First call
        res1 = service.fix_test_failures(original_changes, "Error logs")
        assert res1 == original_changes
        assert mock_client.chat.completions.create.call_count == 1
        
        # Second call
        res2 = service.fix_test_failures(original_changes, "Error logs")
        assert res2 == original_changes
        assert mock_client.chat.completions.create.call_count == 1
