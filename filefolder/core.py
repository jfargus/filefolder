from pathlib import Path
from dataclasses import dataclass, field
from shutil import copy2, move
from datetime import datetime
import datefinder
from hashlib import sha256
import platform
import re
from tqdm import tqdm
import os

try:
    import pwd
except ImportError:
    pwd = None  # Not available on Windows


@dataclass
class File:
    file_path: str
    file: Path = field(init=False)
    file_name: str = field(init=False)
    file_extension: str = field(init=False)
    metadata: dict = field(init=False)
    _hash: str = field(init=False, default=None)
    _datestamp: datetime = field(init=False, default=None)

    def __post_init__(self):
        self.file = Path(self.file_path)
        self.file_name = self.file.stem
        self.file_extension = self.file.suffix[1:]
        self.metadata = self.get_file_metadata()

    def move(self, target_path):
        if not self.file.exists():
            raise FileNotFoundError(f"File {self.file_path} does not exist.")
        target = Path(target_path)
        move(self.file, target)
        self.file = target

    def copy(self, target_path):
        if not self.file.exists():
            raise FileNotFoundError(f"File {self.file_path} does not exist.")
        target = Path(target_path)
        copy2(self.file, target)
        return target

    def get_file_metadata(self) -> dict:
        path = self.file
        stat = path.stat()
        metadata = {
            "file_size_bytes": stat.st_size,
            "created_time": datetime.fromtimestamp(stat.st_ctime),
            "modified_time": datetime.fromtimestamp(stat.st_mtime),
            "accessed_time": datetime.fromtimestamp(stat.st_atime),
        }
        if platform.system() == "Windows":
            import ctypes
            import ctypes.wintypes
            def get_windows_file_owner(p: Path):
                import win32security
                sd = win32security.GetFileSecurity(str(p), win32security.OWNER_SECURITY_INFORMATION)
                owner_sid = sd.GetSecurityDescriptorOwner()
                name, domain, _ = win32security.LookupAccountSid(None, owner_sid)
                return f"{domain}\\{name}"
            try:
                metadata["owner"] = get_windows_file_owner(path)
            except Exception as e:
                metadata["owner"] = f"Unknown (Windows): {e}"
        else:
            try:
                metadata["owner"] = pwd.getpwuid(stat.st_uid).pw_name
            except Exception as e:
                metadata["owner"] = f"Unknown (Unix): {e}"
        return metadata
    
    def extract_date_strings(self, text):
        # Find any sequences that look like numbers separated by allowed delimiters
        rough_matches = re.findall(r"(\d{1,4}[./\-\s]\d{1,2}[./\-\s]\d{1,4})", text)
        clean_dates = []

        for match in rough_matches:
            parts = re.split(r"[./\-\s]", match)
            if len(parts) >= 3:
                # Rebuild date from only the first three components
                clean_date = f"{parts[0]}.{parts[1]}.{parts[2]}"
                clean_dates.append(clean_date)

        return clean_dates

    @property
    def datestamp(self):
        if not self._datestamp:
            filename = self.file.name
            filename_clean = self.extract_date_strings(filename)
            filename_clean = filename_clean[0] if filename_clean else filename
            matches = list(datefinder.find_dates(filename_clean))
            self._datestamp = datetime(2000, 1, 1) if not matches else matches[0]
        return self._datestamp

    @property
    def hash(self):
        if not self._hash:
            with open(self.file, "rb") as f:
                self._hash = sha256(f.read()).hexdigest()
        return self._hash


@dataclass
class Folder:
    folder_path: str
    folder: Path = field(init=False)
    folder_name: str = field(init=False)
    folders: list = field(default_factory=list)
    files: list = field(default_factory=list)

    def __post_init__(self):
        self.folder = Path(self.folder_path)
        self.folder_name = self.folder.name

    def get_contents(self):
        """
        Return a list of all immediate subfolders in the given folder, with progress bar.
        Uses os.scandir() for performance on network drives.
        """
        folder_path = self.folder
        subfolders = []

        try:
            with os.scandir(folder_path) as entries:
                entries = list(entries)  # Materialize for tqdm
                for entry in tqdm(entries, desc="Scanning files for folders..."):
                    if entry.is_dir(follow_symlinks=False):
                        subfolders.append(Folder(str(entry.path)))
        except Exception:
            pass  # Optional: log or raise

        self.folders = subfolders
        self.get_files(recursive=False)

    def get_files(self, recursive=False):
        """
        Return a list of File objects from the folder, optionally recursive.
        Streams file paths as they're discovered via scandir.
        """
        try:
            folder = self.folder
            file_objs = []

            if recursive:
                for path in self._scandir_recursive(folder):
                    file_objs.append(File(str(path)))
            else:
                with os.scandir(folder) as entries:
                    for entry in entries:
                        if entry.is_file(follow_symlinks=False):
                            file_objs.append(File(str(entry.path)))

            self.files = file_objs
            return file_objs

        except Exception:
            return []
    
    def _scandir_recursive(self, path):
        """
        Generator: Recursively yield Path objects for all files under the given directory using os.scandir().
        """
        stack = [Path(path)]

        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as it:
                    for entry in it:
                        entry_path = Path(entry.path)
                        if entry.is_file(follow_symlinks=False):
                            yield entry_path
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(entry_path)
            except Exception:
                continue  # Optionally log or handle inaccessible directories