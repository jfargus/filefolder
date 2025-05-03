# filefolder Package

A lightweight Python package that treats files and folders as structured dataclass objects, allowing introspection of metadata and transformation into flat `pandas` DataFrames for analysis.

## Installation

### Local Install

Clone or download the package and install with:

```bash
pip install -e .
```

## Overview

### Key Features

- Object-oriented access to file and folder metadata
- Cross-platform support for file ownership and timestamps
- Automatic hashing and datestamp extraction
- Flattened tabular export via `.to_pandas()`
- Optional recursive folder scan

## Usage

### Basic Example

```python
from filefolder import Folder

folder = Folder("/path/to/data", recursive=True)
df = folder.to_pandas(include_calulated_fields=True)

print(df.head())
```

## Class Reference

### class File

Represents a file on disk with useful metadata and utilities.

#### Parameters

- `file_path` *(str)*: Path to the file

#### Properties

- `file_name`: Stem of the file (without extension)
- `file_extension`: Extension without dot
- `system_path`: Absolute resolved file path
- `metadata` *(dict)*: Includes size, timestamps, and owner
- `hash` *(str)*: SHA256 hash of the file (lazy evaluated)
- `datestamp` *(datetime)*: Extracted date from filename, or default

#### Methods

- `copy(target_path)`: Copies file to new location
- `move(target_path)`: Moves file to new location

### class Folder

Represents a folder and optionally its recursive contents.

#### Parameters

- `folder_path` *(str)*: Path to the folder
- `recursive` *(bool)*: Whether to scan subdirectories

#### Attributes

- `folder_name`: Just the folder name
- `system_path`: Resolved absolute folder path
- `files`: List of `File` objects
- `folders`: List of sub-`Folder` objects (if any)

#### Methods

- `get_files_in_folder()`: Returns list of `File` objects
- `get_folders_in_folder()`: Returns list of subfolders as `Folder` objects
- `to_pandas(include_calulated_fields=False)`:  
  Returns a flat `pandas.DataFrame` with all `File` and `Folder` fields.

## Output from `.to_pandas()`

Each row corresponds to a file, with columns like:

| Column                       | Description                               |
|-----------------------------|-------------------------------------------|
| `file.file_path`            | Original file path                        |
| `file.file_name`            | File stem                                 |
| `file.file_extension`       | Extension (no dot)                        |
| `file.system_path`          | Full resolved path                        |
| `file.metadata.created_time`| File creation time                        |
| `file.hash`                 | SHA256 hash (if enabled)                  |
| `file.datestamp`            | Date extracted from filename              |
| `folder.folder_path`        | Parent folder path                        |
| `folder.folder_name`        | Folder name                               |
| `folder.folders`            | List of subfolder names                   |

## Testing

You can run tests with `pytest`:

```bash
pytest tests/
```