import pytest
from unittest.mock import MagicMock
from services.github_service import GitHubService

def test_get_directory_structure_defaults():
    # This test verifies the default behavior (recursive, but we will soon add limits)
    # We want to ensure that with our changes, it still works, but respecting defaults.

    service = GitHubService("fake-token")
    mock_repo = MagicMock()

    # root/
    #   file1.py
    #   dir1/
    #     file2.py

    def get_contents_side_effect(path, ref):
        if path == "":
            file1 = MagicMock()
            file1.path = "file1.py"
            file1.name = "file1.py"
            file1.type = "file"
            file1.size = 100

            dir1 = MagicMock()
            dir1.path = "dir1"
            dir1.name = "dir1"
            dir1.type = "dir"
            dir1.size = 0
            return [file1, dir1]

        elif path == "dir1":
            file2 = MagicMock()
            file2.path = "dir1/file2.py"
            file2.name = "file2.py"
            file2.type = "file"
            file2.size = 100
            return [file2]
        return []

    mock_repo.get_contents.side_effect = get_contents_side_effect

    contents = service.get_directory_structure(mock_repo)

    paths = [c['path'] for c in contents]
    assert "file1.py" in paths
    assert "dir1" in paths
    assert "dir1/file2.py" in paths

def test_get_directory_structure_skip_patterns():
    service = GitHubService("fake-token")
    mock_repo = MagicMock()

    # root/
    #   node_modules/
    #     lib.js
    #   src/
    #     main.py

    def get_contents_side_effect(path, ref):
        if path == "":
            nm = MagicMock()
            nm.path = "node_modules"
            nm.name = "node_modules"
            nm.type = "dir"

            src = MagicMock()
            src.path = "src"
            src.name = "src"
            src.type = "dir"

            return [nm, src]

        elif path == "node_modules":
            lib = MagicMock()
            lib.path = "node_modules/lib.js"
            lib.name = "lib.js"
            lib.type = "file"
            return [lib]

        elif path == "src":
            main = MagicMock()
            main.path = "src/main.py"
            main.name = "main.py"
            main.type = "file"
            return [main]

        return []

    mock_repo.get_contents.side_effect = get_contents_side_effect

    # Calling with new arguments (which don't exist yet, so this test will fail if run now)
    # We will run this after modification, or modify the test to match current signature if we wanted to TDD strictly.
    # But since I can't run tests that fail with TypeError, I'll write the test assuming the signature exists.
    # To run it *now* I would need the signature to match.

    # However, I will define the test expecting the new signature.

    # Assuming default skip_patterns includes node_modules
    contents = service.get_directory_structure(mock_repo, skip_patterns=['node_modules'])

    paths = [c['path'] for c in contents]
    assert "src" in paths
    assert "src/main.py" in paths
    assert "node_modules" not in paths # Should we include the dir itself? Usually yes, but not recurse?
    # If I skip a dir, I probably shouldn't even list it if it's "skipped".
    # Or I list it but don't recurse.
    # The requirement says "Skip common large directories".
    # Usually this means ignore them completely.

    # If I modify logic to:
    # if item.name in skip_patterns: continue
    # Then it won't be in the list.

    assert "node_modules/lib.js" not in paths

def test_get_directory_structure_max_depth():
    service = GitHubService("fake-token")
    mock_repo = MagicMock()

    # root/ (depth 0)
    #   dir1/ (depth 1)
    #     dir2/ (depth 2)
    #       file3.py

    def get_contents_side_effect(path, ref):
        if path == "":
            d1 = MagicMock()
            d1.path = "dir1"
            d1.name = "dir1"
            d1.type = "dir"
            return [d1]
        elif path == "dir1":
            d2 = MagicMock()
            d2.path = "dir1/dir2"
            d2.name = "dir2"
            d2.type = "dir"
            return [d2]
        elif path == "dir1/dir2":
            f3 = MagicMock()
            f3.path = "dir1/dir2/file3.py"
            f3.name = "file3.py"
            f3.type = "file"
            return [f3]
        return []

    mock_repo.get_contents.side_effect = get_contents_side_effect

    # Max depth 1.
    # depth 0: root -> dir1
    # depth 1: dir1 -> dir2
    # depth 2: dir2 -> file3.py (should be skipped if max_depth is 1)

    # Wait, how do I define max_depth?
    # Depth of recursion.
    # Root call is depth 0?
    # content of root is depth 1 items?

    # If max_depth=1:
    # get contents of root.
    #   dir1 found. Recurse?
    #   If we recurse, we are at depth 1.
    #   If max_depth=1, we can process depth 1 items.
    #   So we get contents of dir1.
    #     dir2 found. Recurse?
    #     Next depth is 2. 2 > 1. So stop.

    contents = service.get_directory_structure(mock_repo, max_depth=1)
    paths = [c['path'] for c in contents]

    assert "dir1" in paths
    assert "dir1/dir2" in paths # It is found at depth 1.
    assert "dir1/dir2/file3.py" not in paths # Would be depth 2.
