#!/bin/bash

REPO_ROOT=$(git rev-parse --show-toplevel)

# Path to your Python virtual environment if you're using one
# Uncomment and modify if needed:
# VENV_PATH="$REPO_ROOT/venv/bin/python"
# PYTHON_CMD="$VENV_PATH"
PYTHON_CMD="python"

# Change the output path as needed
OUTPUT_FILE="$REPO_ROOT/combined_files.txt"

echo "Running combine_files.py after successful commit..."
$PYTHON_CMD "$REPO_ROOT/combine_files.py" -p -o "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo "Successfully generated combined files at: $OUTPUT_FILE"
else
    echo "Error: Failed to generate combined files"
fi