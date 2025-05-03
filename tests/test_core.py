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

def test_folder_to_pandas():
    with tempfile.TemporaryDirectory() as tempdir:
        file_path = Path(tempdir) / "test.txt"
        file_path.write_text("abc123")

        folder = Folder(str(tempdir))
        df = folder.to_pandas(include_calulated_fields=True)

        assert not df.empty
        assert "file.file_name" in df.columns
        assert "file.hash" in df.columns
        assert "folder.folder_name" in df.columns