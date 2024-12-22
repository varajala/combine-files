import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional, Tuple, Union

PathLike = Union[str, Path]
GitCommandResult = Tuple[bool, Union[str, List[str]]]
ProcessingResult = Tuple[bool, str]

CONFIG = {
    'max_recursion_depth': 3,
    'encoding': 'utf-8',
    'file_begin_marker': '// BEGIN FILE: {}',
    'file_end_marker': '// END FILE',
    'dir_marker': '(DIR)'
}

MESSAGES = {
    'not_git_repo': 'Error: Not a git repository!',
    'dir_not_exist': 'Error: Directory {} does not exist!',
    'no_tracked_files': 'No Git-tracked files found in the directory.',
    'tracked_items_header': f"{os.linesep}Git-tracked items in directory:",
    'input_prompt': f"{os.linesep}Enter item numbers separated by commas, or press Ctrl+C to exit:{os.linesep} > ",
    'empty_input': 'Please enter some numbers or press Ctrl+C to exit.',
    'invalid_number': 'Invalid number: {}',
    'operation_cancelled': f"{os.linesep}Operation cancelled.",
    'file_read_error': 'Error reading file: {}'
}

def normalize_git_path(path: PathLike) -> str:
    """
    Normalize a path to use forward slashes for Git compatibility.

    Args:
        path: Path-like object to normalize

    Returns:
        Normalized path string using forward slashes
    """
    return str(path).replace('\\', '/')


def run_git_command(args: List[str], cwd: Optional[Path] = None) -> GitCommandResult:
    """
    Run a Git command and return the result.

    Args:
        args: List of command arguments
        cwd: Working directory for command execution

    Returns:
        Tuple of (success, result) where result is either output string or error message
    """
    try:
        output = subprocess.check_output(['git'] + args, cwd=cwd, universal_newlines=True)
        return True, output.strip()
    except subprocess.CalledProcessError:
        return False, MESSAGES['not_git_repo']


def get_git_root() -> Optional[Path]:
    """
    Get the root directory of the current Git repository.

    Returns:
        Path to Git root directory or None if not in a repository
    """
    success, result = run_git_command(['rev-parse', '--show-toplevel'])
    if success:
        return Path(result)
    return None


def remove_path_prefix(path: str, prefix: str) -> str:
    """
    Remove the specified path prefix if present.

    Args:
        path: The original file path.
        prefix: The prefix to be removed.

    Returns:
        The relative path without the prefix.
    """
    return path[len(prefix):] if prefix else path


def try_parse_number(input: str, min_value: int, max_value: int) -> Tuple[bool, int]:
    """
    Try parsing a number in the range [min_value, max_value].

    Args:
        input: The string to be parsed.
        min_value: The minimum allowed value for the integer.
        max_value: The maximum allowed value for the integer.

    Returns:
        A tuple of (success, result) where:
        - success is True if the operation was successful, False otherwise.
        - result is the parsed number.
    """
    try:
        num = int(input)
        if num >= min_value and num <= max_value:
            return True, num
        return False, 0
    except ValueError:
        return False, 0


def get_tracked_paths(directory: Path, recursive: bool = False) -> GitCommandResult:
    """
    Get list of Git-tracked paths in specified directory.

    Args:
        directory: Target directory to scan
        recursive: Whether to include files in subdirectories

    Returns:
        Tuple of (success, result) where result is list of paths or error message
    """
    git_root = get_git_root()
    if not git_root:
        return False, MESSAGES['not_git_repo']

    try:
        abs_directory = directory.resolve()
        rel_directory = abs_directory.relative_to(git_root)
        git_prefix = normalize_git_path(rel_directory)
        git_prefix = f"{git_prefix}/" if git_prefix != "." else ""
    except ValueError:
        return False, MESSAGES['dir_not_exist'].format(directory)

    success, output = run_git_command(['ls-files', '--full-name'], git_root)
    if not success:
        return False, output

    if not output:
        return True, []

    tracked_paths = [normalize_git_path(p) for p in output.split("\n")]
    filtered_paths = []

    for path in tracked_paths:
        if git_prefix and not path.startswith(git_prefix):
            continue

        relative_path = remove_path_prefix(path, git_prefix)
        if recursive:
            filtered_paths.append(path)
            continue

        top_level = Path(relative_path).parts[0]
        filtered_paths.append(normalize_git_path(top_level))

    # Remove duplicates while preserving order
    unique_paths = list(dict.fromkeys(filtered_paths))
    return True, unique_paths


def read_file_content(file_path: Path, git_root: Path) -> ProcessingResult:
    """
    Read content from a file with error handling.

    Args:
        file_path: Path to file relative to git root
        git_root: Git repository root directory

    Returns:
        Tuple of (success, content) where content is file content or error message
    """
    full_path = git_root.joinpath(file_path)
    if not full_path.is_file():
        return False, f"File not found: {file_path}"

    try:
        with open(full_path, "r", encoding=CONFIG['encoding']) as file:
            file_content = file.read()
            return True, file_content
    except Exception as e:
        return False, MESSAGES['file_read_error'].format(str(e))


def partition_by_file_type(paths: List[str], base_dir: Path) -> Tuple[List[str], List[str]]:
    """
    Separate paths into directories and files.

    Args:
        paths: List of paths to partition
        base_dir: Base directory for resolving paths

    Returns:
        Tuple of (directories, files) lists
    """
    directories = []
    files = []

    for path in paths:
        full_path = base_dir.joinpath(path)
        if full_path.is_dir():
            directories.append(path)
        else:
            files.append(path)

    return sorted(directories), sorted(files)


def collect_all_files(selected_paths: List[str], target_dir: Path, git_root: Path) -> List[str]:
    """
    Collect all file paths from selected items, including directory contents.

    Args:
        selected_paths: List of selected path items
        target_dir: Target directory being processed
        git_root: Git repository root directory

    Returns:
        List of all file paths to process
    """
    all_files = []

    for path in selected_paths:
        item_path = Path(target_dir).joinpath(path)
        relative_path = item_path.resolve().relative_to(git_root.resolve())

        if item_path.suffix:
            all_files.append(normalize_git_path(relative_path))
            continue

        success, files = get_tracked_paths(item_path, recursive=True)
        if not success or not isinstance(files, list):
            return

        max_depth = CONFIG['max_recursion_depth'] + 1
        for file in files:
            file_path = Path(file)
            if len(file_path.parts) <= max_depth:
                all_files.append(file)

    return all_files


def format_file_contents(file_paths: List[str], git_root: Path) -> ProcessingResult:
    """
    Format contents of multiple files with markers.

    Args:
        file_paths: List of files to process
        git_root: Git repository root directory

    Returns:
        Tuple of (success, formatted_content)
    """
    output_parts = []

    for file_path in file_paths:
        marker = CONFIG['file_begin_marker'].format(file_path)
        output_parts.append(f"{os.linesep}{marker}")

        success, content = read_file_content(Path(file_path), git_root)
        output_parts.append(content if success else content)

        output_parts.append(f"{CONFIG['file_end_marker']}{os.linesep}{os.linesep}")

    return True, "\n".join(output_parts)


def parse_selection(input_str: str, max_value: int) -> Tuple[bool, Union[List[int], str]]:
    """
    Parse user input selection string into list of valid indices.

    Args:
        input_str: Raw input string from user
        max_value: Maximum valid index value

    Returns:
        Tuple of (success, result) where result is list of indices or error message
    """
    if not input_str.strip():
        return False, MESSAGES['empty_input']

    indices = []
    parts = input_str.replace(",", " ").replace(";", " ").split()
    for part in parts:
        success, number = try_parse_number(part, 1, max_value)
        if not success:
            return False, MESSAGES['invalid_number'].format(part)
        indices.append(number - 1)

    return True, indices


def create_arg_parser() -> argparse.ArgumentParser:
    """Create and configure the command line argument parser."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                            # Interactive mode in current directory
  %(prog)s /path/to/directory         # Interactive mode in specified directory
  %(prog)s -p                         # Process all files in current directory
  %(prog)s -p /path/to/directory      # Process all files in specified directory
  %(prog)s -o output.txt              # Save output to file
        """
    )
    parser.add_argument('directory', nargs='?', default='.', help='Target directory (default: current directory)')
    parser.add_argument('-o', '--output', help='Output file path (default: print to stdout)')
    parser.add_argument('-p', '--path', action='store_true', help='Process entire directory without interactive selection')
    return parser


def write_output(content: str, output_path: Optional[str] = None) -> None:
    """
    Output content to file or stdout.

    Args:
        content: Content to output
        output_path: Optional file path for output
    """
    if not output_path:
        print(content)
        return

    with open(output_path, 'w', encoding=CONFIG['encoding']) as file:
        file.write(content)


def handle_non_interactive_mode(directories: List[str], files: List[str], target_dir: Path, git_root: Path, args: argparse.Namespace) -> None:
    """
    Handles the non-interactive mode of the application.

    Args:
        directories: List of sorted directories.
        files: List of sorted files.
        target_dir: The target directory for file collection.
        git_root: The root of the git repository.
        args: The parsed command-line arguments.
    """
    sorted_paths = directories + files
    all_files = collect_all_files(sorted_paths, target_dir, git_root)
    success, output = format_file_contents(all_files, git_root)
    if success:
        write_output(output, args.output)
        return

    print(output)
    sys.exit(1)


def handle_interactive_mode(directories: List[str], files: List[str], target_dir: Path, git_root: Path, args: argparse.Namespace) -> None:
    """
    Handles the interactive mode of the application.

    Args:
        directories: List of sorted directories.
        files: List of sorted files.
        target_dir: The target directory for file collection.
        git_root: The root of the git repository.
        args: The parsed command-line arguments.
    """
    sorted_paths = directories + files
    print(MESSAGES['tracked_items_header'])
    for idx, path in enumerate(sorted_paths, 1):
        prefix = f"{CONFIG['dir_marker']} " if path in directories else ""
        print(f"{idx}. {prefix}{path}")

    while True:
        try:
            selection = input(MESSAGES['input_prompt'])
            success, result = parse_selection(selection, len(sorted_paths))

            if not success:
                print(result)
                continue

            selected_paths = [sorted_paths[i] for i in result]
            all_files = collect_all_files(selected_paths, target_dir, git_root)
            success, output = format_file_contents(all_files, git_root)
            if success:
                write_output(output, args.output)
                break

            print(output)
            sys.exit(1)

        except KeyboardInterrupt:
            print(MESSAGES['operation_cancelled'])
            sys.exit(0)


def main() -> None:
    args = create_arg_parser().parse_args()
    target_dir = Path(args.directory)

    if not target_dir.exists():
        print(MESSAGES['dir_not_exist'].format(target_dir))
        sys.exit(1)

    git_root = get_git_root()
    if not git_root:
        print(MESSAGES['not_git_repo'])
        sys.exit(1)

    success, tracked_paths = get_tracked_paths(target_dir)
    if not success:
        print(tracked_paths)
        sys.exit(1)

    if not tracked_paths:
        print(MESSAGES['no_tracked_files'])
        sys.exit(0)

    directories, files = partition_by_file_type(tracked_paths, git_root)
    if args.path:
        handle_non_interactive_mode(directories, files, target_dir, git_root, args)
    else:
        handle_interactive_mode(directories, files, target_dir, git_root, args)


if __name__ == "__main__":
    main()