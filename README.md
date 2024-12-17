# combine-files
A command-line tool that helps you view and combine content from multiple Git-tracked files in a single output stream.
Useful for picking the relevant files to the LLM of your choice.

## Usage

1. Run the script in the current directory:
```bash
python combine_files.py
```

Or specify a target directory:
```bash
python combine_files.py /path/to/directory
```

To write output to a file instead of stdout:
```bash
python combine_files.py -o output.txt
```

Or combine both:
```bash
python combine_files.py /path/to/directory -o output.txt
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

If no output file is specified, the content will be printed to stdout. To capture this output to a text file, you can use the `-o` option:
```
python combine_files.py -o output.txt
```