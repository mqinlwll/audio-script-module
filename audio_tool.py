import argparse
import importlib
from pathlib import Path
import sys
from colorama import Fore, Style, init

# Initialize colorama for colored output
init(autoreset=True)

def print_logo():
    """Print ASCII logo for AUDIO TOOL."""
    logo = f"""
{Fore.YELLOW}    █████╗ ██╗   ██╗██████╗ ██╗ ██████╗     ████████╗ ██████╗  ██████╗ ██╗
    ██╔══██╗██║   ██║██╔══██╗██║██╔═══██╗    ╚══██╔══╝██╔═══██╗██╔═══██╗██║
    ███████║██║   ██║██║  ██║██║██║   ██║       ██║   ██║   ██║██║   ██║██║
    ██╔══██║██║   ██║██║  ██║██║██║   ██║       ██║   ██║   ██║██║   ██║██║
    ██║  ██║╚██████╔╝██████╔╝██║╚██████╔╝       ██║   ╚██████╔╝╚██████╔╝███████╗
    ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝        ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝{Style.RESET_ALL}
    """
    print(logo)

def main():
    """Set up CLI and dynamically register commands from modules."""
    parser = argparse.ArgumentParser(
        description="A versatile tool for managing and analyzing audio files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--workers", type=int, help="Number of worker processes for parallel tasks")
    subparsers = parser.add_subparsers(dest="command", help="Available commands (use '<command> --help' for details)")

    modules_dir = Path(__file__).parent / 'modules'
    for py_file in modules_dir.glob('*.py'):
        if py_file.name != '__init__.py':
            module_name = f"modules.{py_file.stem}"
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, 'register_command'):
                    module.register_command(subparsers)
                else:
                    print(f"{Fore.YELLOW}Warning: Module {module_name} does not have a 'register_command' function.{Style.RESET_ALL}")
            except ImportError as e:
                print(f"{Fore.RED}Error importing module {module_name}: {e}{Style.RESET_ALL}")

    if len(sys.argv) == 1:
        print_logo()
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if not hasattr(args, 'func'):
        print_logo()
        parser.print_help()
        sys.exit(1)

    args.func(args)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"{Fore.YELLOW}Quitting job...{Style.RESET_ALL}")