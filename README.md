# combine-files
A command-line tool that helps you view and combine content from multiple Git-tracked files in a single output stream.
Useful for picking the relevant files to feed into an LLM or other text processing tools.

## Basic Usage

1. Run the script in the current directory:
```bash
python combine_files.py
```

Or specify a target directory:
```bash
python combine_files.py /path/to/directory
```

2. The script will display a numbered list of Git-tracked items in the specified directory:
   ```
   Git-tracked items in directory:
   1. (DIR) src
   2. (DIR) tests
   3. LICENSE
   4. README.md
   ```

3. Enter the numbers of items you want to process, separated by spaces, commas, or semicolons:
   ```
   > 1,2,3
   ```

4. The script will output the content of all selected files, or recursively process files within selected folders:
   ```
   // BEGIN FILE: src/main.py
   [file content here]
   // END FILE

   // BEGIN FILE: tests/file.py
   [file content here]
   // END FILE

   // BEGIN FILE: LICENSE
   [file content here]
   // END FILE
   ```

## Command Line Arguments

```
usage: combine_files.py [-h] [-o OUTPUT] [-p] [directory]

A tool to combine content from multiple Git-tracked files in a single output stream.

positional arguments:
  directory             Target directory (default: current directory)

options:
  -h, --help           Show this help message and exit
  -o, --output OUTPUT  Output file path (default: print to stdout)
  -p, --path          Process entire directory without interactive selection

```

## Examples

1. Interactive mode in current directory:
```bash
python combine_files.py
```

2. Interactive mode in specific directory:
```bash
python combine_files.py /path/to/directory
```

3. Non-interactive mode (process all files) in current directory:
```bash
python combine_files.py -p
```

4. Non-interactive mode in specific directory:
```bash
python combine_files.py -p /path/to/directory
```

5. Save output to file:
```bash
python combine_files.py -o output.txt
```

6. Combine non-interactive mode with file output:
```bash
python combine_files.py -p -o output.txt
```

## Git Hook Installation

To automatically run this tool after every successful commit:

1. Save the hook script to your repository:
```bash
cp git_hook.sh path/to/your/repo/
cd path/to/your/repo
```

2. Setup the script as "post-commit" Git hook:
```bash
chmod +x git_hook.sh
mv git_hook.sh .git/hooks/post-commit
```

The tool will now run automatically after each commit, generating a `combined_files.txt` file in your repository root. You may want to add this file to your `.gitignore`:
```bash
echo "combined_files.txt" >> .gitignore
```

To temporarily disable the hook:
```bash
mv .git/hooks/post-commit .git/hooks/post-commit.disabled
```

## Development

1. Create and activate a virtual environment:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Unix/MacOS
python3 -m venv venv
source venv/bin/activate
```

2. Install development dependencies:

```bash
pip install -r requirements.txt
```

3. Run the test suite located in `tests`-folder with `pytest`:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_combine_files.py

# Run with coverage report
pytest --cov=combine_files tests/
```

Note: All tests create temporary Git repositories and clean them up after running. Make sure you have Git installed and accessible from the command line.