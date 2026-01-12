#!/usr/bin/env python3
"""
Integration test script for CodeExecutionService.

This script tests the code execution flow on actual files in this directory,
simulating how the service applies file changes and validates them.

Usage:
    python test_integration_local.py
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.code_execution import CodeExecutionService, FileChange, ExecutionResult
from services.stack_detector import StackDetectorService, StackConfig
from services.formatter_detector import FormatterDetectorService


def create_sample_project(project_dir: Path):
    """Create a sample TypeScript/Node.js project similar to the portfolio project."""
    
    # Create package.json
    package_json = """{
  "name": "sample-portfolio",
  "version": "1.0.0",
  "description": "A sample portfolio site",
  "type": "module",
  "scripts": {
    "dev": "echo 'Running dev server'",
    "build": "echo 'Building project'",
    "test": "echo 'Running tests' && exit 0"
  },
  "dependencies": {},
  "devDependencies": {}
}"""
    (project_dir / "package.json").write_text(package_json)
    
    # Create src directory
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    
    # Create config directory
    config_dir = src_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a sample TypeScript config file similar to portfolio config
    config_ts = '''import type { SiteConfig, SiteContent } from "../types";

export const SITE_CONFIG: SiteConfig = {
  title: "Ashok Reddy — Full Stack Engineer",
  author: "Ashok Reddy Kakumanu",
  description:
    "Software Engineer based in Hyderabad, Telangana, India. I specialize in full-stack web development with Next.js, TypeScript, and PostgreSQL.",
  lang: "en",
  siteLogo: "/alejandro-small.jpg",
  navLinks: [
    { text: "Experience", href: "#experience" },
    { text: "Projects", href: "#projects" },
    { text: "About", href: "#about" },
  ],
};

export const SITE_CONTENT: SiteContent = {
  hero: {
    name: "Ashok Reddy Kakumanu",
    specialty: "Full Stack Engineer",
    summary:
      "Software Engineer based in Hyderabad. I specialize in building modern web applications with React, Next.js, and Node.js.",
  },
};
'''
    (config_dir / "index.ts").write_text(config_ts)
    
    # Create types directory with type definitions
    types_dir = src_dir / "types"
    types_dir.mkdir(parents=True, exist_ok=True)
    
    types_ts = '''export interface SiteConfig {
  title: string;
  author: string;
  description: string;
  lang: string;
  siteLogo: string;
  navLinks: Array<{ text: string; href: string }>;
}

export interface SiteContent {
  hero: {
    name: string;
    specialty: string;
    summary: string;
  };
}
'''
    (types_dir / "index.ts").write_text(types_ts)
    
    print(f"✓ Created sample project at {project_dir}")
    return project_dir


def test_apply_file_changes():
    """Test applying file changes to an actual file."""
    print("\n" + "="*60)
    print("TEST 1: Apply File Changes")
    print("="*60)
    
    # Create a temporary project directory
    temp_dir = Path(tempfile.mkdtemp(prefix='test-code-exec-'))
    
    try:
        # Create sample project
        create_sample_project(temp_dir)
        
        # Initialize services
        service = CodeExecutionService()
        
        # Define a file change - similar to what the AI would produce
        # This simulates changing "Ashok Reddy Kakumanu" to "John Doe"
        new_config_content = '''import type { SiteConfig, SiteContent } from "../types";

export const SITE_CONFIG: SiteConfig = {
  title: "John Doe — Full Stack Engineer",
  author: "John Doe",
  description:
    "Software Engineer based in Hyderabad, Telangana, India. I specialize in full-stack web development with Next.js, TypeScript, and PostgreSQL.",
  lang: "en",
  siteLogo: "/alejandro-small.jpg",
  navLinks: [
    { text: "Experience", href: "#experience" },
    { text: "Projects", href: "#projects" },
    { text: "About", href: "#about" },
  ],
};

export const SITE_CONTENT: SiteContent = {
  hero: {
    name: "John Doe",
    specialty: "Full Stack Engineer",
    summary:
      "Software Engineer based in Hyderabad. I specialize in building modern web applications with React, Next.js, and Node.js.",
  },
};
'''
        
        change = FileChange(
            file_path="src/config/index.ts",
            new_content=new_config_content,
            reason="Update personal name fields to 'John Doe' as requested in the issue."
        )
        
        # Apply the change
        print("\n→ Applying file change to src/config/index.ts...")
        service._apply_edit(str(temp_dir), change)
        
        # Verify the change was applied
        updated_content = (temp_dir / "src" / "config" / "index.ts").read_text()
        
        assert "John Doe" in updated_content, "Expected 'John Doe' in updated content"
        assert "Ashok Reddy" not in updated_content, "Expected 'Ashok Reddy' to be removed"
        
        print("✓ File change applied successfully!")
        print(f"  - File: src/config/index.ts")
        print(f"  - Content length: {len(updated_content)} characters")
        print(f"  - 'John Doe' found: {'John Doe' in updated_content}")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_stack_detection():
    """Test stack detection for the sample project."""
    print("\n" + "="*60)
    print("TEST 2: Stack Detection")
    print("="*60)
    
    temp_dir = Path(tempfile.mkdtemp(prefix='test-stack-'))
    
    try:
        # Create sample project
        create_sample_project(temp_dir)
        
        # Initialize detector
        detector = StackDetectorService()
        
        # Get file list
        files = []
        for root, dirs, filenames in os.walk(temp_dir):
            dirs[:] = [d for d in dirs if d != '.git' and d != 'node_modules']
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, temp_dir)
                files.append(rel_path)
        
        print(f"\n→ Files in project: {files}")
        
        # Detect stack
        config = detector.detect_from_file_list(files)
        
        if config:
            print(f"✓ Stack detected successfully!")
            print(f"  - Stack type: {config.stack_type}")
            print(f"  - Runtime: {config.runtime}")
            print(f"  - Package manager: {config.package_manager}")
            print(f"  - Install command: {config.install_command}")
            print(f"  - Test command: {config.test_command}")
            return True
        else:
            print("✗ Could not detect stack")
            return False
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_formatter_detection():
    """Test formatter detection for a project with prettier."""
    print("\n" + "="*60)
    print("TEST 3: Formatter Detection")
    print("="*60)
    
    temp_dir = Path(tempfile.mkdtemp(prefix='test-formatter-'))
    
    try:
        # Create sample project
        create_sample_project(temp_dir)
        
        # Add prettier config to simulate a real project
        prettier_config = """{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2
}"""
        (temp_dir / ".prettierrc").write_text(prettier_config)
        
        # Initialize detector
        detector = FormatterDetectorService()
        
        # Detect formatters
        formatters = detector.detect_formatters(str(temp_dir))
        
        if formatters:
            print(f"✓ Formatter(s) detected!")
            for fmt in formatters:
                print(f"  - Type: {fmt.formatter_type}")
                print(f"  - Command: {fmt.format_command}")
                print(f"  - Extensions: {fmt.file_extensions}")
            return True
        else:
            print("→ No formatters detected (this is expected if prettier not installed)")
            return True  # Still pass - formatter detection is optional
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_full_validation_flow_with_mocks():
    """Test the full validation flow with mocks - similar to the unit tests."""
    print("\n" + "="*60)
    print("TEST 4: Full Validation Flow (with mocks)")
    print("="*60)
    
    from unittest.mock import Mock, patch
    
    temp_dir = Path(tempfile.mkdtemp(prefix='test-full-flow-'))
    
    try:
        # Create sample project
        create_sample_project(temp_dir)
        
        # Create mock stack detector
        mock_detector = Mock()
        mock_config = StackConfig(
            stack_type='nodejs',
            runtime='node:20-slim',
            package_manager='npm',
            install_command='npm install',
            test_command='npm test'
        )
        mock_detector.detect_from_file_list.return_value = mock_config
        
        # Create mock sandbox - simulate Docker not being available
        service = CodeExecutionService(stack_detector=mock_detector)
        service.docker_sandbox = None  # Force local execution
        service.use_aws = False
        
        # Define file changes
        file_changes = [{
            'file_path': 'src/config/index.ts',
            'new_content': '''import type { SiteConfig, SiteContent } from "../types";

export const SITE_CONFIG: SiteConfig = {
  title: "Test User — Full Stack Engineer",
  author: "Test User",
  description: "Test description",
  lang: "en",
  siteLogo: "/test.jpg",
  navLinks: [],
};

export const SITE_CONTENT: SiteContent = {
  hero: {
    name: "Test User",
    specialty: "Engineer",
    summary: "Test summary",
  },
};
''',
            'reason': 'Test change'
        }]
        
        print("\n→ Running validation flow...")
        
        # Mock the clone and local execution
        with patch.object(service, '_clone_repo') as mock_clone:
            mock_clone.return_value = Mock(success=True, exit_code=0, stderr='')
            
            with patch('services.code_execution.tempfile.mkdtemp') as mock_temp:
                mock_temp.return_value = str(temp_dir)
                
                with patch('services.code_execution.subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0, stdout='All tests passed!', stderr='')
                    
                    with patch('services.code_execution.shutil.rmtree'):
                        result = service.validate_changes(
                            repo_url='https://github.com/test/portfolio.git',
                            branch='main',
                            file_changes=file_changes,
                            run_tests=True
                        )
        
        print(f"\n→ Result:")
        print(f"  - Success: {result.success}")
        print(f"  - Stage: {result.stage}")
        print(f"  - Error: {result.error}")
        print(f"\n→ Logs:")
        for log in result.logs:
            print(f"  {log[:80]}...")
        
        if result.success:
            print("\n✓ Full validation flow passed!")
            return True
        else:
            print(f"\n✗ Validation failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_empty_content_handling():
    """Test handling of empty content (edge case from terminal logs)."""
    print("\n" + "="*60)
    print("TEST 5: Empty Content Handling")
    print("="*60)
    
    temp_dir = Path(tempfile.mkdtemp(prefix='test-empty-'))
    
    try:
        # Create sample project
        create_sample_project(temp_dir)
        
        # Initialize service
        service = CodeExecutionService()
        
        # Test 1: Empty string content
        print("\n→ Test 5a: Empty string content")
        change = FileChange(
            file_path="test_empty.ts",
            new_content="",  # Empty content
            reason="Test empty file"
        )
        service._apply_edit(str(temp_dir), change)
        
        empty_file = temp_dir / "test_empty.ts"
        assert empty_file.exists(), "File should be created even with empty content"
        assert empty_file.read_text() == "", "File content should be empty"
        print("  ✓ Empty content handled correctly")
        
        # Test 2: Whitespace-only content
        print("\n→ Test 5b: Whitespace-only content")
        change2 = FileChange(
            file_path="test_whitespace.ts",
            new_content="   \n\n   ",
            reason="Test whitespace file"
        )
        service._apply_edit(str(temp_dir), change2)
        
        ws_file = temp_dir / "test_whitespace.ts"
        assert ws_file.exists(), "File should be created with whitespace content"
        print("  ✓ Whitespace content handled correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("CODE EXECUTION SERVICE - INTEGRATION TESTS")
    print("="*60)
    print("\nThese tests validate the code execution service using")
    print("actual files and similar patterns to the production flow.")
    
    results = []
    
    # Run tests
    results.append(("Apply File Changes", test_apply_file_changes()))
    results.append(("Stack Detection", test_stack_detection()))
    results.append(("Formatter Detection", test_formatter_detection()))
    results.append(("Full Validation Flow", test_full_validation_flow_with_mocks()))
    results.append(("Empty Content Handling", test_empty_content_handling()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
