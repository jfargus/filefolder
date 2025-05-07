from filefolder import File, Folder
from pathlib import Path
import tempfile
import os

def test_file_metadata_and_hash():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp:
        temp.write(b"hello world")
        temp.flush()
        temp_path = temp.name

    f = File(temp_path)

    assert f.file_name == Path(temp_path).stem
    assert f.file_extension == "txt"
    assert f.metadata["file_size_bytes"] == 11
    assert isinstance(f.hash, str)
    assert isinstance(f.datestamp.year, int)

    os.remove(temp_path)