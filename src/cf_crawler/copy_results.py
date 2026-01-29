"""
Utility for copying competition result files while preserving directory structure.

This module copies individual result files from the "Results" directory to a sample
directory ("Results_sample") while maintaining the original folder hierarchy.

Main Function:
- copy_results_file_with_structure(): Copies a file and recreates its directory structure

Usage:
    python copy_results.py Results/{Competition_Name}/{Year}/results.csv
"""

import sys
import os
import shutil

def copy_results_file_with_structure(source_path: str, base_destination_dir: str, source_base_dir: str = "Results"):
    """
    Copy a result file to destination directory while preserving folder hierarchy.
    
    Copies file from source_path to base_destination_dir, recreating the relative
    directory structure from source_base_dir. For example:
        Results/{Competition_Name}/{Year}/results.csv -> Results_sample/{Competition_Name}/{Year}/results.csv
    
    Args:
        source_path: Path to source file (e.g., "Results/{Competition_Name}/{Year}/results.csv")
        base_destination_dir: Base directory for destination (e.g., "Results_sample")
        source_base_dir: Base directory to calculate relative path from (default: "Results")
        
    Raises:
        SystemExit: If source file doesn't exist or path validation fails
    """
    if not os.path.exists(source_path):
        print(f"Error: Source file not found at '{source_path}'")
        sys.exit(1)

    if not os.path.isfile(source_path):
        print(f"Error: Source path '{source_path}' is not a file.")
        sys.exit(1)

    try:
        # Normalize paths to handle different path separators (\ vs /)
        normalized_source_path = os.path.normpath(source_path)
        normalized_source_base = os.path.normpath(source_base_dir)

        # Calculate relative path from source_base_dir to source file
        if not normalized_source_path.startswith(normalized_source_base + os.sep):
             print(f"Error: Source path '{source_path}' does not start with base '{source_base_dir}{os.sep}'")
             sys.exit(1)

        relative_path = os.path.relpath(normalized_source_path, normalized_source_base)

        # Build full destination path with preserved directory structure
        destination_path = os.path.join(base_destination_dir, relative_path)
        destination_subdir = os.path.dirname(destination_path)

        # Create destination subdirectories
        os.makedirs(destination_subdir, exist_ok=True)

        # Copy file with metadata preservation
        shutil.copy2(source_path, destination_path)
        print(f"Successfully copied '{source_path}' to '{destination_path}'")

    except ValueError as ve:
        print(f"Error processing paths: {ve}")
        print(f"Ensure source path '{source_path}' is relative to '{source_base_dir}'.")
        sys.exit(1)
    except Exception as e:
        print(f"Error copying file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # CLI entry point - validate arguments and execute copy operation
    if len(sys.argv) != 2:
        print("Usage: python copy_results.py <path/to/results.csv>")
        print("Example: python copy_results.py Results/EJOI/2024/results.csv")
        sys.exit(1)

    source_file_path = sys.argv[1]
    destination_directory = "Results_sample"  # Target directory for copies
    source_base = "Results"  # Base directory for structure calculation

    copy_results_file_with_structure(source_file_path, destination_directory, source_base)
