## Part 1: Setup and Usage of the Audio Tool Project

### Overview
The **Audio Tool** project is a versatile command-line interface (CLI) tool designed for managing and analyzing audio files. It offers a suite of commands to perform tasks such as audio metadata analysis, integrity checking, database management, cover art manipulation, and fetching song links from online services. The tool leverages external utilities like `ffmpeg` and `ffprobe` for audio processing and supports parallelism for efficient handling of large datasets. The project is modular, with each feature encapsulated in separate Python modules under the `modules` directory, orchestrated by a central script, `audio_tool.py`.

### Prerequisites
To use the Audio Tool, you need to install several dependencies and ensure the system environment is properly configured. Below are the setup instructions for Linux, Windows, and macOS.

#### General Dependencies
- **Python 3.8+**: The tool is written in Python and requires a modern version.
- **FFmpeg**: Required for audio integrity checking and metadata analysis.
- **FFprobe**: Part of FFmpeg, used for detailed audio file analysis.
- **pip**: Python package manager for installing Python dependencies.

#### Installing Dependencies
1. **Python Installation**
   - **Linux**: Most distributions (e.g., Ubuntu, Fedora) come with Python pre-installed. Verify with `python3 --version`. If not installed, use:
     ```bash
     sudo apt install python3 python3-pip  # Ubuntu/Debian
     sudo dnf install python3 python3-pip  # Fedora
     ```
   - **Windows**: Download from [python.org](https://www.python.org/downloads/) and install, ensuring "Add Python to PATH" is checked during installation.
   - **macOS**: Install via Homebrew: `brew install python3` or download from [python.org](https://www.python.org/downloads/).

2. **FFmpeg and FFprobe Installation**
   - **Linux**:
     ```bash
     sudo apt install ffmpeg  # Ubuntu/Debian
     sudo dnf install ffmpeg  # Fedora
     ```
   - **Windows**: Download from [FFmpeg website](https://ffmpeg.org/download.html) or install via Chocolatey:
     ```powershell
     choco install ffmpeg
     ```
     Add FFmpeg’s `bin` directory to your system PATH.
   - **macOS**:
     ```bash
     brew install ffmpeg
     ```

3. **Python Dependencies**
   Install required Python packages listed in the code (e.g., `mutagen`, `tqdm`, `requests`, `colorama`, `sqlite3`). Assuming a `requirements.txt` exists or can be inferred:
   ```bash
   pip3 install mutagen tqdm requests colorama
   ```
   If additional packages are needed (e.g., for specific modules), they’ll be noted below.

#### Project Setup
1. **Clone or Download the Project**
   - If hosted on a repository (e.g., GitHub), clone it:
     ```bash
     git clone https://github.com/mqinlwll/audio-script-module audio-script-module
     cd audio-script-module
     ```
   - Otherwise, extract the provided directory structure:
     ```
     .
     ├── audio_tool.py
     ├── modules
     │   ├── __init__.py
     │   ├── audio_analysis.py
     │   ├── cover_art.py
     │   ├── database_check.py
     │   ├── integrity_check.py
     │   └── songlink.py
     └── utils.py
     ```

2. **Verify Directory Structure**
   Ensure all files are present as shown above. The `modules` directory contains the command implementations, `utils.py` provides shared utilities, and `audio_tool.py` is the entry point.

3. **Run the Tool**
   - From the project root, execute:
     ```bash
     python3 audio_tool.py --help
     ```
   - On Windows, you might use:
     ```cmd
     python audio_tool.py --help
     ```
   - This displays the ASCII logo and available commands if setup is correct.

### Commands and Usage
The Audio Tool provides multiple commands, each implemented as a module in the `modules` directory. Below is a detailed breakdown of each command, its sub-commands/options, usage syntax, and practical use cases.

#### Global Option: `--workers`
- **Description**: Specifies the number of worker processes for parallel execution. Defaults to the CPU core count (e.g., 4).
- **Syntax**: `--workers <number>`
- **Example**: `python3 audio_tool.py info /path/to/audio --workers 8`

#### 1. `info` (audio_analysis.py)
- **Purpose**: Analyzes metadata of audio files using `ffprobe`, reporting bitrate, sample rate, bit depth, channels, and codec.
- **Dependencies**: `ffprobe`, `tqdm`
- **Sub-commands/Options**:
  - `path`: Path to a file or directory (required).
    - Syntax: `<file-or-directory>`
  - `-o/--output`: Output file for results (default: `audio_analysis_<date>.txt`).
    - Syntax: `--output <filename>`
  - `--verbose`: Prints results to console instead of a file, disabling parallelism.
    - Syntax: `--verbose`
- **Usage**:
  - Analyze a single file:
    ```bash
    python3 audio_tool.py info song.mp3 --output analysis.txt
    ```
  - Analyze a directory (parallel):
    ```bash
    python3 audio_tool.py info /music --workers 4
    ```
  - Verbose output:
    ```bash
    python3 audio_tool.py info /music --verbose
    ```
- **Use Case**:
  - **Quality Assessment**: Check if audio files meet a minimum quality standard (e.g., 16-bit depth, 44.1 kHz sample rate).
  - **Format Detection**: Identify codecs (e.g., AAC vs. ALAC in `.m4a` files) for library organization.

#### 2. `count` (audio_analysis.py)
- **Purpose**: Counts albums, songs, or calculates total size per codec across directories.
- **Dependencies**: `ffprobe`, `mutagen`, `tqdm`
- **Sub-commands/Options**:
  - `option`: Choose what to count (`album`, `song`, `size`) (required).
    - Syntax: `album | song | size`
  - `directories`: One or more directories to process (required).
    - Syntax: `<directory> [<directory> ...]`
- **Usage**:
  - Count unique albums:
    ```bash
    python3 audio_tool.py count album /music
    ```
  - Count songs:
    ```bash
    python3 audio_tool.py count song /music /backup
    ```
  - Calculate size:
    ```bash
    python3 audio_tool.py count size /music
    ```
- **Use Case**:
  - **Library Statistics**: Summarize a music collection by codec (e.g., FLAC vs. MP3 usage).
  - **Storage Planning**: Estimate space usage for backups or migrations.

#### 3. `check` (integrity_check.py)
- **Purpose**: Verifies audio file integrity using `ffmpeg`, caching results in an SQLite database.
- **Dependencies**: `ffmpeg`, `tqdm`, `sqlite3`
- **Sub-commands/Options**:
  - `path`: File or directory to check (required).
    - Syntax: `<file-or-directory>`
  - `--verbose`: Prints detailed results sequentially.
    - Syntax: `--verbose`
  - `--summary`: Shows progress and summary only.
    - Syntax: `--summary`
  - `--save-log`: Saves results to log files.
    - Syntax: `--save-log`
  - `--recheck`: Forces rechecking all files, ignoring cache.
    - Syntax: `--recheck`
- **Usage**:
  - Check a directory:
    ```bash
    python3 audio_tool.py check /music
    ```
  - Verbose output:
    ```bash
    python3 audio_tool.py check /music --verbose
    ```
  - Recheck with logs:
    ```bash
    python3 audio_tool.py check /music --recheck --save-log
    ```
- **Use Case**:
  - **Corruption Detection**: Identify damaged audio files after a disk failure.
  - **Batch Verification**: Validate a large collection before archiving.

#### 4. `songlink` (songlink.py)
- **Purpose**: Fetches streaming/download links for songs using the Odesli API.
- **Dependencies**: `requests`, `colorama`
- **Sub-commands/Options**:
  - `--url`: Single song URL (exclusive with `--file`).
    - Syntax: `--url <url>`
  - `--file`: File with URLs (exclusive with `--url`).
    - Syntax: `--file <filename>`
  - `--country`: Country code for localized links.
    - Syntax: `--country <code>`
  - `--songIfSingle`: Treat singles as songs.
    - Syntax: `--songIfSingle`
  - `-s/--select`: Filter services (e.g., `spotify tidal`).
    - Syntax: `--select <service> [<service> ...]`
  - `-o/--output`: Output file for links.
    - Syntax: `--output <filename>`
- **Usage**:
  - Fetch links for a URL:
    ```bash
    python3 audio_tool.py songlink --url "https://open.spotify.com/track/123"
    ```
  - From a file with selected services:
    ```bash
    python3 audio_tool.py songlink --file urls.txt --select spotify youtube
    ```
- **Use Case**:
  - **Cross-Platform Sharing**: Generate links for a song across multiple platforms.
  - **Cataloging**: Build a database of streaming URLs for a playlist.

#### 5. `cover-art` (cover_art.py)
- **Purpose**: Hides or shows cover art files by adding/removing a dot prefix.
- **Dependencies**: `tqdm`
- **Sub-commands/Options**:
  - `--hide`: Hide cover art (exclusive with `--show`).
    - Syntax: `--hide`
  - `--show`: Show hidden cover art (exclusive with `--hide`).
    - Syntax: `--show`
  - `path`: Directory to process (required).
    - Syntax: `<directory>`
- **Usage**:
  - Hide cover art:
    ```bash
    python3 audio_tool.py cover-art --hide /music
    ```
  - Show cover art:
    ```bash
    python3 audio_tool.py cover-art --show /music
    ```
- **Use Case**:
  - **Media Player Cleanup**: Hide cover art to prevent clutter in file explorers.
  - **Restoration**: Restore hidden cover art for display.

#### 6. `dbcheck` (database_check.py)
- **Purpose**: Inspects and manages the integrity check database.
- **Dependencies**: `sqlite3`, `tqdm`
- **Sub-commands/Options**:
  - `--verbose`: Lists all entries.
    - Syntax: `--verbose`
  - `--verify`: Verifies file existence and hashes.
    - Syntax: `--verify`
  - `--csv`: Exports to CSV.
    - Syntax: `--csv`
  - `--json`: Exports to JSON.
    - Syntax: `--json`
  - `--filter`: Filters by status (`all`, `passed`, `failed`).
    - Syntax: `--filter <status>`
  - `--update`: Updates database schema.
    - Syntax: `--update`
  - `--watch`: Watches for real-time updates.
    - Syntax: `--watch`
  - `--check`: Quick status summary.
    - Syntax: `--check`
- **Usage**:
  - Quick check:
    ```bash
    python3 audio_tool.py dbcheck --check
    ```
  - Export failed entries:
    ```bash
    python3 audio_tool.py dbcheck --csv --filter failed
    ```
  - Watch database:
    ```bash
    python3 audio_tool.py dbcheck --watch
    ```
- **Use Case**:
  - **Database Maintenance**: Monitor or update the integrity database.
  - **Audit**: Export verification results for analysis.

### Practical Notes
- **Error Handling**: Commands check for `ffmpeg`/`ffprobe` availability and exit gracefully if missing.
- **Performance**: Use `--workers` to optimize for your hardware, especially with large datasets.
- **Cross-Platform**: The tool is portable but ensure paths use appropriate separators (e.g., `\` on Windows).

---

## Part 2: Code Structure and Implementation Details

### Project Structure
The Audio Tool is organized as follows:
```
.
├── audio_tool.py       # Main CLI entry point
├── modules             # Directory for command modules
│   ├── __init__.py     # Empty, marks directory as a package
│   ├── audio_analysis.py  # 'info' and 'count' commands
│   ├── cover_art.py    # 'cover-art' command
│   ├── database_check.py  # 'dbcheck' command
│   ├── integrity_check.py  # 'check' command
│   └── songlink.py     # 'songlink' command
└── utils.py            # Shared utility functions
```

### File-by-File Breakdown

#### `audio_tool.py`
- **Purpose**: The central script that sets up the CLI, dynamically loads modules, and dispatches commands.
- **Key Functions**:
  - `print_logo()`: Displays an ASCII logo when no arguments are provided or on help request.
  - `main()`: 
    - Initializes an `ArgumentParser` with a `--workers` global option.
    - Dynamically imports modules from `modules/` and calls their `register_command()` functions to register sub-commands.
    - Parses arguments and executes the corresponding command function.
- **Implementation Details**:
  - Uses `importlib` for dynamic module loading, allowing extensibility without modifying the main script.
  - Handles `KeyboardInterrupt` for graceful exit.

#### `utils.py`
- **Purpose**: Provides shared utility functions and constants.
- **Key Components**:
  - `AUDIO_EXTENSIONS`: List of supported audio file extensions.
  - `load_config()`: Loads or creates a JSON config file (`audio-script-config.json`) with defaults (e.g., log folder).
  - `get_audio_files(directory)`: Recursively finds audio files in a directory.
  - `is_ffmpeg_installed()` and `is_ffprobe_installed()`: Check for external tool availability.
  - `directory_path()` and `path_type()`: Custom `argparse` types for path validation.
- **Details**: Centralizes common functionality, reducing code duplication across modules.

#### `modules/audio_analysis.py`
- **Purpose**: Implements `info` and `count` commands for audio metadata analysis.
- **Key Functions**:
  - `analyze_single_file(file_path)`: Uses `ffprobe` to extract metadata (bitrate, sample rate, etc.) and formats a detailed report.
  - `analyze_audio(args)`: Handles the `info` command, supporting single files or directories with optional parallelism.
  - `get_codec(file_path)` and `get_album_metadata(file_path)`: Extract codec and metadata using `ffprobe` and `mutagen`.
  - `count_albums()`, `count_songs()`, `calculate_size()`: Process directories to count albums, songs, or sizes by codec.
  - `count_command(args)`: Dispatches to the appropriate counting function.
  - `register_command(subparsers)`: Registers `info` and `count` with the CLI.
- **Details**:
  - Leverages `concurrent.futures` for parallelism in non-verbose mode.
  - Includes warnings for low quality (e.g., bit depth < 16).

#### `modules/integrity_check.py`
- **Purpose**: Implements the `check` command for audio file integrity verification.
- **Key Functions**:
  - `calculate_file_hash(file_path)`: Computes MD5 hash for file uniqueness.
  - `initialize_database(db_path)`: Sets up SQLite tables (`passed_files`, `failed_files`) with hash and mtime tracking.
  - `determine_action(db_path, file_path, force_recheck)`: Decides whether to use cached results, update mtime, or re-run `ffmpeg`.
  - `check_single_file(file_path)`: Runs `ffmpeg` to test file integrity.
  - `process_file(db_path, file_path, force_recheck)`: Coordinates action determination and checking.
  - `check_integrity(args)`: Main command handler with verbose, summary, and parallel modes.
- **Details**:
  - Uses SQLite for caching to avoid redundant checks.
  - Supports batch database updates every 100 files in parallel mode for efficiency.

#### `modules/songlink.py`
- **Purpose**: Implements the `songlink` command to fetch song links via the Odesli API.
- **Key Functions**:
  - `fetch_links(url, country, song_if_single)`: Queries the Odesli API and normalizes service names.
  - `print_links(url, links, selected_services)`: Displays links with colored formatting.
  - `songlink_command(args)`: Handles URL/file input and output options.
- **Details**:
  - Uses `colorama` for visually distinct service names in the console.
  - Supports bulk processing from a file of URLs.

#### `modules/cover_art.py`
- **Purpose**: Implements the `cover-art` command to hide/show cover art files.
- **Key Functions**:
  - `rename_file(src, dst)`: Performs file renaming.
  - `get_files_to_rename(path, hide)`: Identifies cover art files to process.
  - `process_cover_art(args)`: Executes renaming in parallel.
- **Details**:
  - Recognizes standard cover art filenames (e.g., `cover.jpg`).
  - Uses dot-prefixing for hiding (e.g., `.cover.jpg`).

#### `modules/database_check.py`
- **Purpose**: Implements the `dbcheck` command to inspect and manage the integrity database.
- **Key Functions**:
  - `calculate_file_hash(file_path)`: Reused MD5 hash function.
  - `update_database_schema(db_path)`: Adds `mtime` column if missing, with progress tracking.
  - `list_database_entries(db_path, ...)`: Lists, verifies, and exports database entries.
  - `watch_database(db_path, interval)`: Monitors database changes in real-time.
  - `check_database(args)`: Main command handler.
- **Details**:
  - Supports CSV/JSON exports and real-time watching.
  - Verifies file existence and hash consistency with `--verify`.

### Code Design Principles
- **Modularity**: Each command is self-contained in a module, registered dynamically.
- **Parallelism**: Uses `concurrent.futures` for efficient multi-core processing.
- **Caching**: SQLite database optimizes integrity checks by storing results.
- **Extensibility**: New commands can be added by dropping a module into `modules/`.
- **Error Handling**: Robust checks for external tools and file access.

### Technical Notes
- **Dependencies**: Relies on external tools (`ffmpeg`, `ffprobe`) and Python libraries (`mutagen`, `requests`, etc.).
- **Performance**: Parallelism is adjustable via `--workers`, with fallbacks for sequential execution.
- **Portability**: Cross-platform compatible, though path handling assumes POSIX-style separators in some cases.
