import pytest
import subprocess
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import combine_files
from typing import Generator, Any, List


@pytest.fixture
def git_repo(tmp_path: Path) -> Generator[Path, Any, None]:
    """Create a temporary Git repository with test files."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path)

    # Configure git
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path)

    # Create test file structure
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


def test_normalize_git_path() -> None:
    """Test path normalization for Git compatibility."""
    assert combine_files.normalize_git_path(r"path\to\file") == "path/to/file"
    assert combine_files.normalize_git_path("path/to/file") == "path/to/file"
    assert combine_files.normalize_git_path(Path("path/to/file")) == "path/to/file"


def test_run_git_command_success(git_repo: Path) -> None:
    """Test successful Git command execution."""
    success, result = combine_files.run_git_command(["rev-parse", "--git-dir"])
    assert success
    assert result == ".git"


def test_run_git_command_failure(tmp_path: Path) -> None:
    """Test Git command failure handling."""
    os.chdir(tmp_path)
    success, result = combine_files.run_git_command(["status"])
    assert not success
    assert result == combine_files.MESSAGES['not_git_repo']


def test_get_git_root(git_repo: Path) -> None:
    """Test getting Git root directory."""
    root = combine_files.get_git_root()
    assert root is not None
    assert root.resolve() == git_repo.resolve()


def test_get_git_root_not_repo(tmp_path: Path) -> None:
    """Test error when not in a Git repository."""
    os.chdir(tmp_path)
    root = combine_files.get_git_root()
    assert root is None


def test_get_tracked_paths_root(git_repo: Path) -> None:
    """Test getting tracked paths from root directory."""
    success, paths = combine_files.get_tracked_paths(git_repo)
    assert success
    assert sorted(paths) == sorted(["README.md", "src", "tests"])


def test_get_tracked_paths_subdirectory(git_repo: Path) -> None:
    """Test getting tracked paths from subdirectory."""
    success, paths = combine_files.get_tracked_paths(git_repo / "src")
    assert success
    assert sorted(paths) == sorted(["main.py", "utils.py"])


def test_get_tracked_paths_recursive(git_repo: Path) -> None:
    """Test getting tracked paths recursively."""
    success, paths = combine_files.get_tracked_paths(git_repo, recursive=True)
    assert success
    expected = [
        "README.md",
        "src/main.py",
        "src/utils.py",
        "tests/test_main.py"
    ]
    assert sorted(paths) == sorted(expected)


def test_partition_by_file_type(git_repo: Path) -> None:
    """Test separating paths into directories and files."""
    paths = ["src", "tests", "README.md"]
    directories, files = combine_files.partition_by_file_type(paths, git_repo)
    assert directories == ["src", "tests"]
    assert files == ["README.md"]


def test_read_file_content(git_repo: Path) -> None:
    """Test reading file content."""
    success, content = combine_files.read_file_content(Path("README.md"), git_repo)
    assert success
    assert content == "# Test Project\nThis is a test project."


def test_read_file_content_nonexistent(git_repo: Path) -> None:
    """Test reading nonexistent file."""
    success, content = combine_files.read_file_content(Path("nonexistent.txt"), git_repo)
    assert not success
    assert "File not found" in content


def test_format_file_contents(git_repo: Path) -> None:
    """Test formatting contents of multiple files."""
    file_paths = ["README.md", "src/main.py"]
    success, output = combine_files.format_file_contents(file_paths, git_repo)

    assert success
    assert "// BEGIN FILE: README.md" in output
    assert "# Test Project" in output
    assert "// BEGIN FILE: src/main.py" in output
    assert "def main():" in output
    assert "// END FILE" in output


def test_parse_selection_valid() -> None:
    """Test parsing valid selection input."""
    success, result = combine_files.parse_selection("1,2,3", 5)
    assert success
    assert result == [0, 1, 2]


def test_parse_selection_invalid() -> None:
    """Test parsing invalid selection input."""
    test_cases = [
        ("", (False, combine_files.MESSAGES['empty_input'])),
        ("0", (False, combine_files.MESSAGES['invalid_number'].format("0"))),
        ("6", (False, combine_files.MESSAGES['invalid_number'].format("6"))),
        ("abc", (False, combine_files.MESSAGES['invalid_number'].format("abc"))),
    ]

    for input_str, expected in test_cases:
        success, result = combine_files.parse_selection(input_str, 5)
        assert (success, result) == expected


def test_collect_all_files(git_repo: Path) -> None:
    """Test collecting all file paths from selected items."""
    selected_paths = ["src", "README.md"]
    files = combine_files.collect_all_files(selected_paths, git_repo, git_repo)
    assert sorted(files) == sorted(["README.md", "src/main.py", "src/utils.py"])


def test_write_output(tmp_path: Path) -> None:
    """Test writing output to file and stdout."""
    test_content = "Test content"
    output_file = tmp_path / "output.txt"

    # Test stdout
    with patch('builtins.print') as mock_print:
        combine_files.write_output(test_content)
        mock_print.assert_called_once_with(test_content)

    # Test file output
    combine_files.write_output(test_content, str(output_file))
    assert output_file.read_text() == test_content


@pytest.mark.parametrize("args,expected_exit_code", [
    (["-h"], 0),
    (["nonexistent_directory"], 1),
    (["-o", "output.txt", "-p", "nonexistent_directory"], 1),
])
def test_main_error_cases(args: List[str], expected_exit_code: int) -> None:
    """Test various error cases in main function."""
    with patch('sys.argv', ['combine_files.py'] + args):
        with pytest.raises(SystemExit) as exc_info:
            combine_files.main()
        assert exc_info.value.code == expected_exit_code


@patch('builtins.input')
def test_interactive_mode(mock_input: MagicMock, git_repo: Path) -> None:
    """Test interactive mode with user input."""
    mock_input.return_value = "3"  # Select README.md

    with patch('sys.argv', ['combine_files.py']):
        with patch('sys.stdout') as mock_stdout:
            combine_files.main()

            output = ''.join(call.args[0] for call in mock_stdout.write.call_args_list)
            output = output.replace('\r\n', '\n')  # Normalize line endings

            assert "Git-tracked items in directory:" in output
            assert "// BEGIN FILE: README.md" in output
            assert "# Test Project" in output


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


def test_collect_all_files_dotted_dirs(git_repo: Path) -> None:
    """Test collecting files from directories containing dots in their names."""
    # Create test files in Language.Tests directory
    lang_tests = git_repo / "Language.Tests"
    lang_tests.mkdir()
    test_files = [
        "ExpressionParsingTests.cs",
        "ScanningTests.cs",
        "StatementParsingTests.cs"
    ]
    for file in test_files:
        (lang_tests / file).write_text("test content")

    # Add regular top-level file
    (git_repo / "README.md").write_text("readme content")

    # Add and commit all files
    subprocess.run(["git", "add", "."], cwd=git_repo)
    subprocess.run(["git", "commit", "-m", "Add test files"], cwd=git_repo)

    # Verify git tracking works correctly first
    success, paths = combine_files.get_tracked_paths(git_repo)
    assert success
    assert "Language.Tests" in paths

    # Now test collect_all_files
    collected = combine_files.collect_all_files(["Language.Tests", "README.md"], git_repo, git_repo)

    # Verify all test files were collected
    expected_paths = {
        "Language.Tests/ExpressionParsingTests.cs",
        "Language.Tests/ScanningTests.cs",
        "Language.Tests/StatementParsingTests.cs",
        "README.md"
    }
    actual_paths = set(collected)

    print(f"\nExpected paths: {sorted(expected_paths)}")
    print(f"Actual paths: {sorted(actual_paths)}")

    # Test that all expected files are present
    assert actual_paths == expected_paths, \
        "Not all files from Language.Tests directory were collected"