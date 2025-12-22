#!/bin/bash

# Check if a directory is provided, otherwise default to the current directory
dir="${1:-.}"

# Use find to locate all __pycache__ directories and remove them
find "$dir" -type d -name '__pycache__' -exec rm -r {} +

echo "All __pycache__ directories have been removed from $dir and its subdirectories."
