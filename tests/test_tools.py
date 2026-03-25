import pytest
import os
from tokenwaster.tools import edit_file, read_files, list_files

def test_edit_file_security():
    # Attempt to write outside the TokenWaster Comment folder
    res = edit_file.execute("d:/secret_file.txt", "hacked")
    assert "SECURITY ERROR" in res

def test_list_files_invalid_path():
    res = list_files.execute("d:/nonexistent_folder_xyz_123")
    assert "Error: Path not found" in res
