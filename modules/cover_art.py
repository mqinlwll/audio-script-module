import os
from pathlib import Path
import concurrent.futures
from tqdm import tqdm
import utils  # Import from root directory
from colorama import Fore, Style, init

# Initialize colorama for colored output
init(autoreset=True)

def print_logo():
    """Print ASCII logo for the Cover Art module."""
    logo = f"""
{Fore.MAGENTA}    ╔════════════════════╗
    ║   COVER ART MODULE ║
    ║  Hide/Show Cover   ║
    ║      Artwork       ║
    ╚════════════════════╝{Style.RESET_ALL}
    """
    print(logo)

def rename_file(src: str, dst: str):
    """Rename a file from src to dst."""
    os.rename(src, dst)

def get_files_to_rename(path: str, hide: bool) -> list:
    """Identify cover art files to rename based on hide/show action."""
    files_to_rename = []
    for root, _, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            if hide:
                if file in BASE_COVER_NAMES:
                    new_name = os.path.join(root, "." + file)
                    if not os.path.exists(new_name):
                        files_to_rename.append((file_path, new_name))
            else:
                if file.startswith(".") and file[1:] in BASE_COVER_NAMES:
                    new_name = os.path.join(root, file[1:])
                    if not os.path.exists(new_name):
                        files_to_rename.append((file_path, new_name))
    return files_to_rename

BASE_COVER_NAMES = ['cover.jpg', 'cover.jpeg', 'cover.png', 'folder.jpg', 'folder.png']

def process_cover_art(args):
    """Handle the 'cover-art' command to hide or show cover art files."""
    print_logo()
    path = args.path
    hide = args.hide
    num_workers = args.workers if args.workers is not None else (os.cpu_count() or 4)
    files_to_rename = get_files_to_rename(path, hide)
    if not files_to_rename:
        print(f"{Fore.YELLOW}No cover art files to {'hide' if hide else 'show'} in '{path}'.{Style.RESET_ALL}")
        return
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(rename_file, src, dst) for src, dst in files_to_rename]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Processing cover art"):
            try:
                future.result()
            except Exception as e:
                print(f"{Fore.RED}Error renaming file: {e}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Cover art {'hidden' if hide else 'shown'} successfully.{Style.RESET_ALL}")

def register_command(subparsers):
    """Register the 'cover-art' command with the subparsers."""
    cover_parser = subparsers.add_parser("cover-art", help="Hide or show cover art files in directories")
    cover_group = cover_parser.add_mutually_exclusive_group(required=True)
    cover_group.add_argument("--hide", action="store_true", help="Hide cover art by adding a dot prefix")
    cover_group.add_argument("--show", action="store_true", help="Show cover art by removing dot prefix")
    cover_parser.add_argument("path", type=utils.directory_path, help="Directory containing cover art files")
    cover_parser.set_defaults(func=process_cover_art)