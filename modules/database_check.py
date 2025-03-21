import os
from pathlib import Path
import sqlite3
import hashlib
from tqdm import tqdm
import datetime
import csv
import json
import time
import utils  # Import from root directory
from colorama import Fore, Style, init

# Initialize colorama for colored output
init(autoreset=True)

def print_logo():
    """Print ASCII logo for the DBCheck module."""
    logo = f"""
{Fore.BLUE}    ╔════════════════════╗
    ║   DBCHECK MODULE   ║
    ║  Integrity Check   ║
    ║   Database Tool    ║
    ╚════════════════════╝{Style.RESET_ALL}
    """
    print(logo)

def calculate_file_hash(file_path: str) -> str:
    """Calculate the MD5 hash of a file."""
    md5 = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                md5.update(chunk)
        return md5.hexdigest()
    except (FileNotFoundError, PermissionError):
        return None

def check_database_exists(db_path: Path) -> bool:
    """Check if the database file exists."""
    return db_path.exists()

def get_database_summary(db_path: Path) -> tuple:
    """Get a summary of the database contents."""
    if not check_database_exists(db_path):
        return 0, 0, "Database not found"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM passed_files")
    passed_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM failed_files")
    failed_count = cursor.fetchone()[0]

    conn.close()
    return passed_count, failed_count, None

def update_database_schema(db_path: Path):
    """Update the database schema to include new columns if necessary, with a progress bar."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check and update 'passed_files' table
    cursor.execute("PRAGMA table_info(passed_files)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'mtime' not in columns:
        print(f"{Fore.YELLOW}Adding 'mtime' column to passed_files...{Style.RESET_ALL}")
        cursor.execute("ALTER TABLE passed_files ADD COLUMN mtime REAL")
        cursor.execute("SELECT file_path FROM passed_files")
        file_paths = [row[0] for row in cursor.fetchall()]
        with tqdm(total=len(file_paths), desc="Updating mtime in passed_files") as pbar:
            for file_path in file_paths:
                try:
                    mtime = os.path.getmtime(file_path)
                    cursor.execute("UPDATE passed_files SET mtime = ? WHERE file_path = ?", (mtime, file_path))
                except (FileNotFoundError, OSError):
                    pass
                pbar.update(1)

    # Check and update 'failed_files' table
    cursor.execute("PRAGMA table_info(failed_files)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'mtime' not in columns:
        print(f"{Fore.YELLOW}Adding 'mtime' column to failed_files...{Style.RESET_ALL}")
        cursor.execute("ALTER TABLE failed_files ADD COLUMN mtime REAL")
        cursor.execute("SELECT file_path FROM failed_files")
        file_paths = [row[0] for row in cursor.fetchall()]
        with tqdm(total=len(file_paths), desc="Updating mtime in failed_files") as pbar:
            for file_path in file_paths:
                try:
                    mtime = os.path.getmtime(file_path)
                    cursor.execute("UPDATE failed_files SET mtime = ? WHERE file_path = ?", (mtime, file_path))
                except (FileNotFoundError, OSError):
                    pass
                pbar.update(1)

    conn.commit()
    conn.close()
    print(f"{Fore.GREEN}Database schema updated successfully.{Style.RESET_ALL}")

def list_database_entries(db_path: Path, verbose: bool = False, verify: bool = False, export_csv: str = None, export_json: str = None, filter_status: str = "all"):
    """List database entries, optionally verifying files, exporting to CSV/JSON, and filtering by status."""
    if not check_database_exists(db_path):
        print(f"{Fore.RED}Error: Database '{db_path}' not found.{Style.RESET_ALL}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = {'passed_files': 'PASSED', 'failed_files': 'FAILED'}
    all_entries = []

    for table, status in tables.items():
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        mtime_col = 'mtime' if 'mtime' in columns else 'NULL AS mtime'
        cursor.execute(f"SELECT file_path, file_hash, last_checked, {mtime_col} FROM {table}")
        rows = cursor.fetchall()
        for file_path, stored_hash, last_checked, mtime in rows:
            entry_status = status
            message = ""
            if verify:
                if not os.path.exists(file_path):
                    entry_status = "MISSING"
                    message = "File no longer exists"
                else:
                    current_hash = calculate_file_hash(file_path)
                    if current_hash != stored_hash:
                        entry_status = "CHANGED"
                        message = "Hash mismatch"
                    elif current_hash is None:
                        entry_status = "ERROR"
                        message = "Unable to read file"
            all_entries.append((entry_status, file_path, stored_hash, last_checked, message, mtime))

    conn.close()

    if filter_status == "passed":
        filtered_entries = [entry for entry in all_entries if entry[0] == "PASSED"]
    elif filter_status == "failed":
        filtered_entries = [entry for entry in all_entries if entry[0] in ["FAILED", "MISSING", "CHANGED", "ERROR"]]
    else:
        filtered_entries = all_entries

    if export_csv:
        with open(export_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Status", "File Path", "Hash", "Last Checked", "Message", "Mtime"])
            for status, file_path, stored_hash, last_checked, message, mtime in filtered_entries:
                writer.writerow([status, file_path, stored_hash, last_checked, message, mtime])
        print(f"{Fore.GREEN}Exported to CSV: {export_csv}{Style.RESET_ALL}")

    if export_json:
        json_data = [
            {"status": status, "file_path": file_path, "hash": stored_hash, "last_checked": last_checked, "message": message, "mtime": mtime}
            for status, file_path, stored_hash, last_checked, message, mtime in filtered_entries
        ]
        with open(export_json, 'w', encoding='utf-8') as jsonfile:
            json.dump(json_data, jsonfile, indent=4)
        print(f"{Fore.GREEN}Exported to JSON: {export_json}{Style.RESET_ALL}")

    if verbose:
        for status, file_path, stored_hash, last_checked, message, mtime in all_entries:
            color = Fore.GREEN if status == "PASSED" else Fore.RED if status in ["FAILED", "MISSING", "CHANGED", "ERROR"] else Fore.WHITE
            line = f"{color}{status} {file_path} (Hash: {stored_hash}, Last Checked: {last_checked}, Mtime: {mtime}){Style.RESET_ALL}"
            if message:
                line += f": {message}"
            print(line)

    passed_count = sum(1 for e in all_entries if e[0] == "PASSED")
    failed_count = sum(1 for e in all_entries if e[0] == "FAILED")
    missing_count = sum(1 for e in all_entries if e[0] == "MISSING")
    changed_count = sum(1 for e in all_entries if e[0] == "CHANGED")
    error_count = sum(1 for e in all_entries if e[0] == "ERROR")

    print(f"\n{Fore.CYAN}Database Summary:{Style.RESET_ALL}")
    print(f"Total entries: {len(all_entries)}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")
    if verify:
        print(f"Missing: {missing_count}")
        print(f"Changed: {changed_count}")
        print(f"Errors: {error_count}")

def watch_database(db_path: Path, interval: int = 5):
    """Watch the database for changes in real-time."""
    if not check_database_exists(db_path):
        print(f"{Fore.RED}Error: Database '{db_path}' not found.{Style.RESET_ALL}")
        return

    print(f"{Fore.CYAN}Watching database at: {db_path}{Style.RESET_ALL}")
    print(f"Checking for updates every {interval} seconds (Ctrl+C to stop)")

    last_passed, last_failed, _ = get_database_summary(db_path)
    print(f"Initial count - Passed: {last_passed}, Failed: {last_failed}")

    try:
        while True:
            current_passed, current_failed, error = get_database_summary(db_path)
            if error:
                print(f"{Fore.RED}{error}{Style.RESET_ALL}")
                return

            if current_passed != last_passed or current_failed != last_failed:
                print(f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {Fore.YELLOW}Database updated:{Style.RESET_ALL}")
                print(f"Passed: {last_passed} → {current_passed}")
                print(f"Failed: {last_failed} → {current_failed}")
                last_passed, last_failed = current_passed, current_failed

            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n{Fore.GREEN}Stopped watching database.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error while watching database: {e}{Style.RESET_ALL}")

def quick_check_database(db_path: Path):
    """Quick check of database entries and their status."""
    if not check_database_exists(db_path):
        print(f"{Fore.RED}Error: Database '{db_path}' not found.{Style.RESET_ALL}")
        return

    passed_count, failed_count, error = get_database_summary(db_path)
    if error:
        print(f"{Fore.RED}{error}{Style.RESET_ALL}")
        return

    total = passed_count + failed_count
    print(f"{Fore.CYAN}Database Quick Check ({db_path}):{Style.RESET_ALL}")
    print(f"Total entries: {total}")
    print(f"Passed: {passed_count} ({(passed_count/total)*100:.1f}% if total > 0 else 0)")
    print(f"Failed: {failed_count} ({(failed_count/total)*100:.1f}% if total > 0 else 0)")

def check_database(args):
    """Handle the 'dbcheck' command to inspect the database."""
    print_logo()
    config = utils.load_config()
    cache_folder = Path(config.get("cache_folder", "cache log"))
    db_path = cache_folder / "integrity_check.db"

    verbose = getattr(args, 'verbose', False)
    verify = getattr(args, 'verify', False)
    export_csv = getattr(args, 'csv', False)
    export_json = getattr(args, 'json', False)
    filter_status = getattr(args, 'filter', 'all')
    update_db = getattr(args, 'update', False)
    watch = getattr(args, 'watch', False)
    quick_check = getattr(args, 'check', False)

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    csv_file = f"dbcheck-{filter_status}-{timestamp}.csv" if export_csv else None
    json_file = f"dbcheck-{filter_status}-{timestamp}.json" if export_json else None

    print(f"{Fore.CYAN}Checking database at: {db_path}{Style.RESET_ALL}")
    if not check_database_exists(db_path):
        print(f"{Fore.RED}Error: Database '{db_path}' does not exist.{Style.RESET_ALL}")
        return

    if watch:
        watch_database(db_path)
        return

    if quick_check:
        quick_check_database(db_path)
        return

    if update_db:
        update_database_schema(db_path)

    passed_count, failed_count, error = get_database_summary(db_path)
    if error:
        print(f"{Fore.RED}{error}{Style.RESET_ALL}")
        return

    print(f"Initial summary - Passed: {passed_count}, Failed: {failed_count}")
    list_database_entries(db_path, verbose=verbose, verify=verify, export_csv=csv_file, export_json=json_file, filter_status=filter_status)
    print(f"{Fore.GREEN}Database check complete.{Style.RESET_ALL}")

def register_command(subparsers):
    """Register the 'dbcheck' command with the subparsers."""
    dbcheck_parser = subparsers.add_parser("dbcheck", help="Inspect and manage the integrity database")
    dbcheck_parser.add_argument("--verbose", action="store_true", help="List all database entries with details")
    dbcheck_parser.add_argument("--verify", action="store_true", help="Verify file existence and hashes")
    dbcheck_parser.add_argument("--csv", action="store_true", help="Export results to a CSV file")
    dbcheck_parser.add_argument("--json", action="store_true", help="Export results to a JSON file")
    dbcheck_parser.add_argument("--filter", choices=['all', 'passed', 'failed'], default='all',
                                help="Filter export: 'all' (default), 'passed', or 'failed'")
    dbcheck_parser.add_argument("--update", action="store_true", help="Update database schema for compatibility")
    dbcheck_parser.add_argument("--watch", action="store_true", help="Monitor database for real-time updates")
    dbcheck_parser.add_argument("--check", action="store_true", help="Perform a quick check of database counts")
    dbcheck_parser.set_defaults(func=check_database)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Database integrity checker")
    subparsers = parser.add_subparsers()
    register_command(subparsers)
    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()