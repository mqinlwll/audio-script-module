import os
import shutil
import subprocess
import concurrent.futures
from tqdm import tqdm
import datetime
from pathlib import Path
import sqlite3
import hashlib  # Using hashlib for MD5
import threading
import utils  # Import from root directory

def calculate_file_hash(file_path: str) -> str:
    """Calculate the MD5 hash of a file.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: MD5 hash as a hexadecimal string.
    """
    hasher = hashlib.md5()  # Initialize MD5 hash object
    with open(file_path, 'rb') as f:  # Open file in binary read mode
        while chunk := f.read(8192):  # Read file in 8KB chunks
            hasher.update(chunk)  # Update hash with each chunk
    return hasher.hexdigest()  # Return the final hash as a hex string

def initialize_database(db_path: Path):
    """Initialize the SQLite database with tables for passed and failed files, including mtime."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS passed_files (
                file_path TEXT PRIMARY KEY,
                file_hash TEXT,  -- Now stores MD5 hash
                mtime REAL,
                status TEXT,
                last_checked TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failed_files (
                file_path TEXT PRIMARY KEY,
                file_hash TEXT,  -- Now stores MD5 hash
                mtime REAL,
                status TEXT,
                last_checked TEXT
            )
        ''')
        conn.commit()
        print(f"Database successfully initialized at: {db_path}")
    except sqlite3.OperationalError as e:
        print(f"Error initializing database at '{db_path}': {e}")
        raise
    finally:
        conn.close()

def determine_action(db_path: Path, file_path: str, force_recheck: bool = False) -> tuple:
    """Determine the action for a file based on database and file stats."""
    if force_recheck:
        try:
            current_mtime = os.path.getmtime(file_path)
            current_hash = calculate_file_hash(file_path)  # Use MD5
            return 'RUN_FFMPEG', None, current_hash, current_mtime
        except FileNotFoundError:
            return 'FILE_NOT_FOUND', None, None, None

    try:
        current_mtime = os.path.getmtime(file_path)
    except FileNotFoundError:
        return 'FILE_NOT_FOUND', None, None, None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for table in ['passed_files', 'failed_files']:
        cursor.execute(f"SELECT status, file_hash, mtime FROM {table} WHERE file_path = ?", (file_path,))
        result = cursor.fetchone()
        if result:
            stored_status, stored_hash, stored_mtime = result
            if stored_mtime == current_mtime:
                conn.close()
                return 'USE_CACHED', stored_status, None, current_mtime
            else:
                current_hash = calculate_file_hash(file_path)  # Use MD5
                if stored_hash == current_hash:
                    conn.close()
                    return 'UPDATE_MTIME', stored_status, current_hash, current_mtime
                else:
                    conn.close()
                    return 'RUN_FFMPEG', None, current_hash, current_mtime
    conn.close()
    current_hash = calculate_file_hash(file_path)  # Use MD5
    return 'RUN_FFMPEG', None, current_hash, current_mtime

def check_single_file(file_path: str) -> tuple:
    """Check the integrity of a single audio file using FFmpeg."""
    try:
        result = subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', file_path, '-f', 'null', '-'],
            capture_output=True, text=True
        )
        status = "PASSED" if not result.stderr else "FAILED"
        message = "" if not result.stderr else result.stderr.strip()
        return status, message, file_path
    except Exception as e:
        return "FAILED", str(e), file_path

def process_file(db_path: Path, file_path: str, force_recheck: bool = False) -> tuple:
    """Process a file: determine action and perform checks if needed."""
    action, stored_status, current_hash, current_mtime = determine_action(db_path, file_path, force_recheck)
    if action == 'USE_CACHED':
        return ('USE_CACHED', stored_status, "Cached result", file_path, None)
    elif action == 'UPDATE_MTIME':
        return ('UPDATE_MTIME', stored_status, "Cached result (hash matches)", file_path, current_mtime)
    elif action == 'RUN_FFMPEG':
        status, message, _ = check_single_file(file_path)
        update_info = (file_path, current_hash, current_mtime, status)
        return ('RUN_FFMPEG', status, message, file_path, update_info)
    else:
        return ('ERROR', "Unknown action", file_path, None)

def cleanup_database(db_path: Path):
    """Remove database entries for files that no longer exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for table in ['passed_files', 'failed_files']:
        cursor.execute(f"SELECT file_path FROM {table}")
        for (file_path,) in cursor.fetchall():
            if not os.path.exists(file_path):
                cursor.execute(f"DELETE FROM {table} WHERE file_path = ?", (file_path,))
    conn.commit()
    conn.close()

def check_integrity(args):
    """Handle the 'check' command to verify audio file integrity with optimized caching."""
    if not utils.is_ffmpeg_installed():
        print("Error: FFmpeg is not installed or not in your PATH.")
        return

    path = args.path
    verbose = getattr(args, 'verbose', False)
    summary = getattr(args, 'summary', False)
    save_log = getattr(args, 'save_log', False)
    force_recheck = getattr(args, 'recheck', False)
    num_workers = args.workers if args.workers is not None else (os.cpu_count() or 4)
    use_threading = getattr(args, 'use_threading', False)
    config = utils.load_config()

    cache_folder = Path(config.get("cache_folder", "cache log"))
    cache_folder.mkdir(parents=True, exist_ok=True)
    db_path = cache_folder / "integrity_check.db"

    log_folder = Path(config.get("log_folder", "Logs"))
    log_folder.mkdir(parents=True, exist_ok=True)

    print(f"Current working directory: {os.getcwd()}")
    print(f"Attempting to initialize database at: {db_path}")

    initialize_database(db_path)

    if os.path.isfile(path) and os.path.splitext(path)[1].lower() in utils.AUDIO_EXTENSIONS:
        audio_files = [path]
    elif os.path.isdir(path):
        audio_files = utils.get_audio_files(path)
        if not audio_files:
            print(f"No audio files found in '{path}'.")
            return
    else:
        print(f"'{path}' is not a file or directory.")
        return

    create_log = save_log or (not verbose and not summary)
    if create_log:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        failed_log_filename = log_folder / f"Failed-{timestamp}.txt"
        success_log_filename = log_folder / f"Success-{timestamp}.txt"
        failed_log_file = open(failed_log_filename, 'w', encoding='utf-8')
        success_log_file = open(success_log_filename, 'w', encoding='utf-8')
    else:
        failed_log_file = None
        success_log_file = None

    total_files = len(audio_files)

    if verbose:
        # Sequential processing with immediate database updates (unchanged)
        all_results = []
        for file_path in audio_files:
            action, status, message, _, extra = process_file(db_path, file_path, force_recheck)
            if action in ['USE_CACHED', 'UPDATE_MTIME', 'RUN_FFMPEG']:
                all_results.append((status, message, file_path))
                result_line = f"{status} {file_path}" + (f": {message}" if message else "")
                print(result_line)
                if create_log:
                    (success_log_file if status == "PASSED" else failed_log_file).write(result_line + "\n")
            if action == 'UPDATE_MTIME':
                stored_status = status
                current_mtime = extra
                table = 'passed_files' if stored_status == 'PASSED' else 'failed_files'
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(f"UPDATE {table} SET mtime = ? WHERE file_path = ?", (current_mtime, file_path))
                conn.commit()
                conn.close()
            elif action == 'RUN_FFMPEG':
                update_info = extra
                file_path, file_hash, mtime, status = update_info
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                if status == 'PASSED':
                    cursor.execute("DELETE FROM failed_files WHERE file_path = ?", (file_path,))
                    table = 'passed_files'
                else:
                    cursor.execute("DELETE FROM passed_files WHERE file_path = ?", (file_path,))
                    table = 'failed_files'
                cursor.execute(f'''
                    INSERT OR REPLACE INTO {table} (file_path, file_hash, mtime, status, last_checked)
                    VALUES (?, ?, ?, ?, ?)
                ''', (file_path, file_hash, mtime, status, datetime.datetime.now().isoformat()))
                conn.commit()
                conn.close()
    else:
        # Concurrent processing with batch updates every 100 files
        all_results = []
        mtime_updates_passed = []
        mtime_updates_failed = []
        db_updates_passed = []
        db_updates_failed = []
        processed_count = 0

        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(process_file, db_path, file, force_recheck) for file in audio_files]
            with tqdm(total=len(futures), desc="Processing files") as pbar:
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    action, status, message, file_path, extra = result
                    if action == 'USE_CACHED':
                        all_results.append((status, message, file_path))
                    elif action == 'UPDATE_MTIME':
                        stored_status = status
                        current_mtime = extra
                        all_results.append((stored_status, message, file_path))
                        if stored_status == 'PASSED':
                            mtime_updates_passed.append((file_path, current_mtime))
                        else:
                            mtime_updates_failed.append((file_path, current_mtime))
                    elif action == 'RUN_FFMPEG':
                        update_info = extra
                        all_results.append((status, message, file_path))
                        if status == 'PASSED':
                            db_updates_passed.append(update_info)
                        else:
                            db_updates_failed.append(update_info)
                    pbar.update(1)
                    processed_count += 1

                    # Update database every 100 files
                    if processed_count % 100 == 0:
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        if mtime_updates_passed:
                            cursor.executemany("UPDATE passed_files SET mtime = ? WHERE file_path = ?",
                                               mtime_updates_passed)
                            mtime_updates_passed = []
                        if mtime_updates_failed:
                            cursor.executemany("UPDATE failed_files SET mtime = ? WHERE file_path = ?",
                                               mtime_updates_failed)
                            mtime_updates_failed = []
                        if db_updates_passed:
                            for file_path, _, _, _ in db_updates_passed:
                                cursor.execute("DELETE FROM failed_files WHERE file_path = ?", (file_path,))
                            cursor.executemany('''
                                INSERT OR REPLACE INTO passed_files (file_path, file_hash, mtime, status, last_checked)
                                VALUES (?, ?, ?, ?, ?)
                            ''', [(file_path, file_hash, mtime, status, datetime.datetime.now().isoformat())
                                  for file_path, file_hash, mtime, status in db_updates_passed])
                            db_updates_passed = []
                        if db_updates_failed:
                            for file_path, _, _, _ in db_updates_failed:
                                cursor.execute("DELETE FROM passed_files WHERE file_path = ?", (file_path,))
                            cursor.executemany('''
                                INSERT OR REPLACE INTO failed_files (file_path, file_hash, mtime, status, last_checked)
                                VALUES (?, ?, ?, ?, ?)
                            ''', [(file_path, file_hash, mtime, status, datetime.datetime.now().isoformat())
                                  for file_path, file_hash, mtime, status in db_updates_failed])
                            db_updates_failed = []
                        conn.commit()
                        conn.close()

        # Final update for any remaining items
        if mtime_updates_passed or mtime_updates_failed or db_updates_passed or db_updates_failed:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            if mtime_updates_passed:
                cursor.executemany("UPDATE passed_files SET mtime = ? WHERE file_path = ?",
                                   mtime_updates_passed)
            if mtime_updates_failed:
                cursor.executemany("UPDATE failed_files SET mtime = ? WHERE file_path = ?",
                                   mtime_updates_failed)
            if db_updates_passed:
                for file_path, _, _, _ in db_updates_passed:
                    cursor.execute("DELETE FROM failed_files WHERE file_path = ?", (file_path,))
                cursor.executemany('''
                    INSERT OR REPLACE INTO passed_files (file_path, file_hash, mtime, status, last_checked)
                    VALUES (?, ?, ?, ?, ?)
                ''', [(file_path, file_hash, mtime, status, datetime.datetime.now().isoformat())
                      for file_path, file_hash, mtime, status in db_updates_passed])
            if db_updates_failed:
                for file_path, _, _, _ in db_updates_failed:
                    cursor.execute("DELETE FROM passed_files WHERE file_path = ?", (file_path,))
                cursor.executemany('''
                    INSERT OR REPLACE INTO failed_files (file_path, file_hash, mtime, status, last_checked)
                    VALUES (?, ?, ?, ?, ?)
                ''', [(file_path, file_hash, mtime, status, datetime.datetime.now().isoformat())
                      for file_path, file_hash, mtime, status in db_updates_failed])
            conn.commit()
            conn.close()

    cleanup_database(db_path)

    passed_count = sum(1 for status, _, _ in all_results if status == "PASSED")
    failed_count = sum(1 for status, _, _ in all_results if status == "FAILED")

    if create_log and not verbose:
        for status, message, file_path in all_results:
            result_line = f"{status} {file_path}" + (f": {message}" if message else "")
            (success_log_file if status == "PASSED" else failed_log_file).write(result_line + "\n")

    summary_text = f"\nSummary:\nTotal files: {total_files}\nPassed: {passed_count}\nFailed: {failed_count}\n"
    if verbose or summary:
        print(summary_text)
    if create_log:
        failed_log_file.write(summary_text)
        success_log_file.write(summary_text)
        failed_log_file.close()
        success_log_file.close()
        print(f"Check complete. Logs saved to '{failed_log_filename}' and '{success_log_filename}'")
    else:
        print("Check complete.")

def register_command(subparsers):
    """Register the 'check' command with the subparsers."""
    check_parser = subparsers.add_parser("check", help="Verify audio file integrity")
    check_parser.add_argument("path", type=utils.path_type, help="File or directory to check")
    output_group = check_parser.add_mutually_exclusive_group()
    output_group.add_argument("--verbose", action="store_true", help="Print detailed results (sequential)")
    output_group.add_argument("--summary", action="store_true", help="Show progress and summary only")
    check_parser.add_argument("--save-log", action="store_true", help="Save results to log files")
    check_parser.add_argument("--recheck", action="store_true", help="Force recheck of all files, overwriting cached results")
    check_parser.add_argument("--use-threading", action="store_true", help="Unused; retained for compatibility")
    check_parser.set_defaults(func=check_integrity)
