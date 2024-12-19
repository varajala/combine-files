import pytest
import subprocess
import os
from pathlib import Path
from unittest.mock import patch
import combine_files
from typing import Generator, Any

@pytest.fixture
def git_repo(tmp_path: Path) -> Generator[Path, Any, None]:
    """Create a temporary Git repository with some test files."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path)

    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path)

    (repo_path / "src").mkdir()
    (repo_path / "tests").mkdir()

    files = {
        "README.md": "# Test Project\nThis is a test project.",
        "src/main.py": "def main():\n    print('Hello, World!')",
        "src/utils.py": "def helper():\n    return True",
        "tests/test_main.py": "def test_main():\n    assert True",
    }

    for file_path, content in files.items():
        full_path = repo_path / file_path
        full_path.parent.mkdir(exist_ok=True)
        full_path.write_text(content)
        subprocess.run(["git", "add", file_path], cwd=repo_path)

    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path)

    original_dir = os.getcwd()
    os.chdir(repo_path)
    yield repo_path
    os.chdir(original_dir)

def test_get_git_root(git_repo: Path) -> None:
    """Test getting Git root directory."""
    root = combine_files.get_git_root()
    assert root.resolve() == git_repo.resolve()

def test_get_git_root_not_repo(tmp_path: Path) -> None:
    """Test error when not in a Git repository."""
    original_dir = os.getcwd()
    os.chdir(tmp_path)
    try:
        with pytest.raises(SystemExit) as exc_info:
            combine_files.get_git_root()
        assert exc_info.value.code == 1
    finally:
        os.chdir(original_dir)

def test_get_tracked_items_root(git_repo: Path) -> None:
    """Test getting tracked items from root directory."""
    items = combine_files.get_tracked_items(git_repo)
    assert sorted(items) == sorted(["README.md", "src", "tests"])

def test_get_tracked_items_subdirectory(git_repo: Path) -> None:
    """Test getting tracked items from subdirectory."""
    items = combine_files.get_tracked_items(git_repo / "src")
    assert sorted(items) == sorted(["main.py", "utils.py"])

def test_get_tracked_items_recursive(git_repo: Path) -> None:
    """Test getting tracked items recursively."""
    items = combine_files.get_tracked_items(git_repo, recursive=True)
    expected = [
        "README.md",
        "src/main.py",
        "src/utils.py",
        "tests/test_main.py"
    ]
    assert sorted(items) == sorted(expected)

def test_sort_items(git_repo: Path) -> None:
    """Test sorting items into directories and files."""
    items = ["src", "tests", "README.md"]
    directories, files = combine_files.sort_items(items, git_repo)
    assert directories == ["src", "tests"]
    assert files == ["README.md"]

def test_get_file_content(git_repo: Path) -> None:
    """Test reading file content."""
    content = combine_files.get_file_content(Path("README.md"), git_repo)
    assert content == "# Test Project\nThis is a test project."

def test_get_file_content_nonexistent(git_repo: Path) -> None:
    """Test reading nonexistent file."""
    content = combine_files.get_file_content(Path("nonexistent.txt"), git_repo)
    assert content is None

def test_process_files(git_repo: Path) -> None:
    """Test processing multiple files."""
    files = ["README.md", "src/main.py"]
    output = combine_files.process_files(git_repo, files, git_repo)

    assert "// BEGIN FILE: README.md" in output
    assert "# Test Project" in output
    assert "// BEGIN FILE: src/main.py" in output
    assert "def main():" in output
    assert "// END FILE" in output

@pytest.mark.parametrize("args,expected_exit_code", [
    (["-h"], 0),
    (["nonexistent_directory"], 1),
    (["-o", "output.txt", "-p", "nonexistent_directory"], 1),
])
def test_main_error_cases(git_repo: Path, args: list, expected_exit_code: int) -> None:
    """Test various error cases in main function."""
    with patch('sys.argv', ['combine_files.py'] + args):
        with pytest.raises(SystemExit) as exc_info:
            combine_files.main()
        assert exc_info.value.code == expected_exit_code

@patch('builtins.input')
def test_interactive_mode(mock_input: Any, git_repo: Path) -> None:
    """Test interactive mode with user input."""
    mock_input.return_value = "3"  # Select README.md (item #3 in the list)

    with patch('sys.argv', ['combine_files.py']):
        with patch('sys.stdout') as mock_stdout:
            combine_files.main()

            captured_output = ''.join(call.args[0] for call in mock_stdout.write.call_args_list)
            captured_output = captured_output.replace('\r\n', '\n')

            assert "Git-tracked items in directory:" in captured_output
            assert "// BEGIN FILE: README.md" in captured_output
            assert "# Test Project" in captured_output

def test_noninteractive_mode(git_repo: Path) -> None:
    """Test non-interactive mode with -p flag."""
    output_file = git_repo / "output.txt"

    with patch('sys.argv', ['combine_files.py', '-p', '-o', str(output_file)]):
        combine_files.main()

        assert output_file.exists()
        content = output_file.read_text()
        assert "// BEGIN FILE:" in content
        assert "// END FILE" in content
        assert "# Test Project" in content