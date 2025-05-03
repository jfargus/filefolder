from pathlib import Path
from dataclasses import dataclass, field, asdict, is_dataclass
from shutil import copy2, move
from datetime import datetime
import datefinder
from hashlib import sha256
import platform
import pandas as pd
import re

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
    system_path: str = field(init=False)
    _hash: str = field(init=False, default=None)
    _datestamp: datetime = field(init=False, default=None)

    def __post_init__(self):
        self.file = Path(self.file_path)
        self.file_name = self.file.stem
        self.file_extension = self.file.suffix[1:]
        self.metadata = self.get_file_metadata()
        self.system_path = str(self.file.resolve())

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
    recursive: bool = False
    folder: Path = field(init=False)
    folder_name: str = field(init=False)
    folders: list = field(default_factory=list)
    files: list = field(default_factory=list)
    system_path: str = field(init=False)

    def __post_init__(self):
        self.folder = Path(self.folder_path)
        self.folders = self.get_folders_in_folder()
        self.files = self.get_files_in_folder()
        self.folder_name = self.folder.name
        self.system_path = str(self.folder.resolve())

    def get_folders_in_folder(self):
        folder = self.folder
        return [Folder(str(f)) for f in folder.iterdir() if f.is_dir()]

    def get_files_in_folder(self):
        try:
            folder = self.folder
            if self.recursive:
                return [File(str(f)) for f in folder.rglob("*") if f.is_file()]
            else:
                return [File(str(f)) for f in folder.iterdir() if f.is_file()]
        except Exception:
            return []

    def to_pandas(self, include_calulated_fields=False):
        import pandas as pd
        from dataclasses import asdict

        if not self.files:
            return pd.DataFrame()

        folder_data = asdict(self)
        folder_data.pop("files", None)
        folder_data.pop("folders", None)

        folder_prefixed = {f"folder.{k}": v for k, v in folder_data.items()}
        folder_prefixed["folder.folders"] = [f.folder_name for f in self.folders]

        rows = []
        for f in self.files:
            file_data = asdict(f)
            file_data["hash"] = f.hash if include_calulated_fields else None
            file_data["datestamp"] = f.datestamp if include_calulated_fields else None
            file_prefixed = {f"file.{k}": v for k, v in file_data.items()}
            row = {**file_prefixed, **folder_prefixed}
            rows.append(row)

        return pd.json_normalize(rows, sep=".")
