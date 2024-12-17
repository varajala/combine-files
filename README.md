# combine-files
A command-line tool that helps you view and combine content from multiple Git-tracked files in a single output stream.
Useful for picking the relevant files to the LLM of your choice.

## Usage

1. Run the script in the current directory:
```bash
./git_file_combiner.py
```

Or specify a target directory:
```bash
./git_file_combiner.py /path/to/directory
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

4. The script will output the content of all selected files, or recursively files within a folder, with clear markers:
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

The default recursion depth is 3.

To capture this output to a text file, use piping or equivalent of your favorite shell.