"""
MIT License

Copyright (c) 2024 Valtteri Rajalainen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional, Tuple


# Configuration
MAX_RECURSION_DEPTH = 3
DEFAULT_ENCODING = "utf-8"

# File markers
FILE_BEGIN_MARKER = "// BEGIN FILE: {}"
FILE_END_MARKER = "// END FILE"
DIR_MARKER = "(DIR)"

# CLI messages
MSG_NOT_GIT_REPO = "Error: Not a git repository!"
MSG_DIR_NOT_EXIST = "Error: Directory {} does not exist!"
MSG_NO_TRACKED_FILES = "No Git-tracked files found in the directory."
MSG_TRACKED_ITEMS_HEADER = f"{os.linesep}Git-tracked items in directory:"
MSG_INPUT_PROMPT = f"{os.linesep}Enter item numbers separated by commas, or press Ctrl+C to exit:{os.linesep} > "
MSG_EMPTY_INPUT = "Please enter some numbers or press Ctrl+C to exit."
MSG_INVALID_NUMBER = "Invalid number: {}"
MSG_OPERATION_CANCELLED = f"{os.linesep}Operation cancelled."
MSG_FILE_READ_ERROR = "Error reading file: {}"


def get_git_root() -> Path:
    try:
        git_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], universal_newlines=True).strip()
        return Path(git_root)
    except subprocess.CalledProcessError:
        print(MSG_NOT_GIT_REPO)
        sys.exit(1)


def get_tracked_items(directory: Path, recursive: bool = False) -> List[str]:
    git_root = get_git_root()

    abs_directory = directory.resolve()

    try:
        rel_directory = abs_directory.relative_to(git_root)
        prefix = str(rel_directory) + "/" if str(rel_directory) != "." else ""
    except ValueError:
        print(MSG_DIR_NOT_EXIST.format(directory))
        sys.exit(1)

    cmd = ["git", "ls-files", "--full-name"]
    output = subprocess.check_output(cmd, cwd=git_root, universal_newlines=True).strip()

    if not output:
        return []

    items = output.split("\n")
    directory_items = []

    for item in items:
        if not item.startswith(prefix):
            continue

        relative_item = item[len(prefix):] if prefix else item

        if not recursive:
            parts = Path(relative_item).parts
            if parts:
                directory_items.append(parts[0])
        else:
            directory_items.append(item)

    return sorted(list(set(directory_items)))


def sort_items(items: List[str]) -> Tuple[List[str], List[str]]:
    directories = []
    files = []

    for item in items:
        if Path(item).suffix:
            files.append(item)
        else:
            directories.append(item)

    return sorted(directories), sorted(files)


def get_file_content(file_path: Path, git_root: Path) -> Optional[str]:
    try:
        full_path = git_root / file_path
        if full_path.is_file():
            with open(full_path, "r", encoding=DEFAULT_ENCODING) as f:
                return f.read()
    except Exception as e:
        return MSG_FILE_READ_ERROR.format(str(e))
    return None


def process_files(target_dir: Path, all_files: List[str], git_root: Path) -> str:
    output = []
    for file in all_files:
        output.append(f"{os.linesep}{FILE_BEGIN_MARKER.format(file)}")
        content = get_file_content(file, git_root)
        if content is not None:
            output.append(content)
        output.append(f"{FILE_END_MARKER}{os.linesep}{os.linesep}")
    return "\n".join(output)


def get_all_files(selected_items: List[str], target_dir: Path, git_root: Path) -> List[str]:
    all_files = []
    for item in selected_items:
        item_path = Path(target_dir) / item
        rel_path = item_path.resolve().relative_to(git_root.resolve())

        if item_path.suffix:
            all_files.append(str(rel_path))
        else:
            files = get_tracked_items(item_path, recursive=True)
            for file in files:
                if len(Path(file).parts) <= MAX_RECURSION_DEPTH + 1:
                    all_files.append(file)
    return all_files


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="A tool to combine content from multiple Git-tracked files in a single output stream.",
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
    parser.add_argument('directory', nargs='?', default='.',
                       help='Target directory (default: current directory)')
    parser.add_argument('-o', '--output',
                       help='Output file path (default: print to stdout)')
    parser.add_argument('-p', '--path', action='store_true',
                       help='Process entire directory without interactive selection')
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    target_dir = Path(args.directory)

    if not target_dir.exists():
        print(MSG_DIR_NOT_EXIST.format(target_dir))
        sys.exit(1)

    items = get_tracked_items(target_dir)
    if not items:
        print(MSG_NO_TRACKED_FILES)
        sys.exit(0)

    git_root = get_git_root()
    directories, files = sort_items(items)
    sorted_items = directories + files

    if args.path:
        # Non-interactive mode: process all items
        all_files = get_all_files(sorted_items, target_dir, git_root)
        output = process_files(target_dir, all_files, git_root)
    else:
        # Interactive mode
        print(MSG_TRACKED_ITEMS_HEADER)
        for idx, item in enumerate(sorted_items, 1):
            prefix = f"{DIR_MARKER} " if item in directories else ""
            print(f"{idx}. {prefix}{item}")

        while True:
            try:
                selection = input(MSG_INPUT_PROMPT).strip()
                if not selection:
                    print(MSG_EMPTY_INPUT)
                    continue

                numbers = []
                for part in selection.replace(",", " ").replace(";", " ").split():
                    try:
                        num = int(part)
                        if 1 <= num <= len(sorted_items):
                            numbers.append(num - 1)
                        else:
                            raise ValueError
                    except ValueError:
                        print(MSG_INVALID_NUMBER.format(part))
                        break
                else:
                    selected_items = [sorted_items[i] for i in numbers]
                    all_files = get_all_files(selected_items, target_dir, git_root)
                    output = process_files(target_dir, all_files, git_root)
                    break

            except KeyboardInterrupt:
                print(MSG_OPERATION_CANCELLED)
                sys.exit(0)

    if args.output:
        with open(args.output, 'w', encoding=DEFAULT_ENCODING) as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()