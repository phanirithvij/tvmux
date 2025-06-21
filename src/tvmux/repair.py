#!/usr/bin/env python3
"""
Asciinema cast file repair utilities.

Simple functions to detect and repair corrupted asciinema cast files.
Handles large files by streaming instead of loading into RAM.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_cast_file(cast_path: Path) -> bool:
    """
    Validate that an asciinema cast file is properly formatted.
    Only reads header and tail to avoid loading large files into RAM.

    Args:
        cast_path: Path to the cast file

    Returns:
        True if file is valid, False otherwise
    """
    if not cast_path.exists() or cast_path.stat().st_size == 0:
        return False

    try:
        with open(cast_path, 'r', encoding='utf-8') as f:
            # Check header
            first_line = f.readline()
            if not first_line:
                return False

            try:
                json.loads(first_line.rstrip())
            except json.JSONDecodeError:
                return False

            # Check if there's more content
            second_line = f.readline()
            if not second_line:
                return True  # Just header, that's valid

            # Check last line by seeking to end and reading backwards
            f.seek(0, 2)  # Seek to end
            file_size = f.tell()

            if file_size < 100:
                # Small file, just read it all
                f.seek(0)
                content = f.read()
                last_line = content.strip().split('\n')[-1]
            else:
                # Read last chunk to find last line
                chunk_size = min(1024, file_size)
                f.seek(file_size - chunk_size)
                chunk = f.read()
                last_line = chunk.strip().split('\n')[-1]

            # Last line should end with ']' if it's an event
            return not last_line or last_line.endswith(']')

    except (IOError, UnicodeDecodeError):
        return False


def repair_cast_file(cast_path: Path, backup: bool = True) -> bool:
    """
    Repair a corrupted asciinema cast file.

    Streams the file to avoid memory issues with large files.
    Fixes incomplete JSON arrays due to asciinema termination during write.

    Args:
        cast_path: Path to the cast file to repair
        backup: Whether to create a backup before repair

    Returns:
        True if repair was successful or unnecessary, False on failure
    """
    if not cast_path.exists():
        return False

    # Check if repair is needed
    if validate_cast_file(cast_path):
        return True

    try:
        # Create backup if requested
        if backup:
            backup_path = cast_path.with_suffix(cast_path.suffix + '.backup')
            with open(cast_path, 'rb') as src, open(backup_path, 'wb') as dst:
                while chunk := src.read(8192):
                    dst.write(chunk)

        # Stream repair using temporary file
        temp_path = cast_path.with_suffix('.tmp')

        with open(cast_path, 'r', encoding='utf-8') as src, \
             open(temp_path, 'w', encoding='utf-8') as dst:

            # Validate and copy header
            first_line = src.readline()
            if not first_line:
                return False

            try:
                json.loads(first_line.rstrip())
                dst.write(first_line)
            except json.JSONDecodeError:
                return False

            # Stream process remaining lines
            for line in src:
                line = line.rstrip()
                if not line:
                    continue

                try:
                    # Try to parse as JSON array
                    json.loads(line)
                    dst.write(line + '\n')
                except json.JSONDecodeError:
                    # Skip corrupted line
                    continue

        # Replace original with repaired file
        temp_path.replace(cast_path)
        return True

    except (IOError, UnicodeDecodeError):
        # Clean up temp file if it exists
        if 'temp_path' in locals():
            temp_path.unlink(missing_ok=True)
        return False
