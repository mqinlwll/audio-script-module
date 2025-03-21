import subprocess
import json
from pathlib import Path
import concurrent.futures
from tqdm import tqdm
import datetime
import utils  # Import from root directory
from colorama import Fore, Style, init

# Initialize colorama for colored output
init(autoreset=True)

def print_logo():
    """Print ASCII logo for the Info module."""
    logo = f"""
{Fore.CYAN}    ╔════════════════════╗
    ║     INFO MODULE    ║
    ║  Audio Metadata    ║
    ║    Analyzer        ║
    ╚════════════════════╝{Style.RESET_ALL}
    """
    print(logo)

def analyze_single_file(file_path: str) -> str:
    """Analyze metadata of a single audio file using ffprobe."""
    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]
        result = subprocess.check_output(cmd, universal_newlines=True)
        data = json.loads(result)
        stream = data["streams"][0]

        codec = stream.get("codec_name", "N/A")
        sample_rate = stream.get("sample_rate", "N/A")
        channels = stream.get("channels", "N/A")
        bit_depth = stream.get("bits_per_raw_sample", "N/A")
        bit_rate = data["format"].get("bit_rate", "N/A")

        channel_info = "Mono" if channels == 1 else "Stereo" if channels == 2 else f"{channels} channels" if channels != "N/A" else "N/A"
        analysis_text = f"{Fore.GREEN}Analyzing: {file_path}{Style.RESET_ALL}\n"
        analysis_text += f"  Bitrate: {bit_rate} bps\n" if bit_rate != "N/A" else "  Bitrate: N/A\n"
        analysis_text += f"  Sample Rate: {sample_rate} Hz\n" if sample_rate != "N/A" else "  Sample Rate: N/A\n"
        analysis_text += f"  Bit Depth: {bit_depth} bits\n" if bit_depth != "N/A" else "  Bit Depth: N/A\n"
        analysis_text += f"  Channels: {channel_info}\n"
        analysis_text += f"  Codec: {codec}\n"

        if Path(file_path).suffix.lower() == ".m4a":
            if "aac" in codec.lower():
                analysis_text += f"  {Fore.YELLOW}[INFO] AAC (lossy) codec detected.{Style.RESET_ALL}\n"
            elif "alac" in codec.lower():
                analysis_text += f"  {Fore.YELLOW}[INFO] ALAC (lossless) codec detected.{Style.RESET_ALL}\n"
            else:
                analysis_text += f"  {Fore.RED}[WARNING] Unknown codec: {codec}{Style.RESET_ALL}\n"
        elif Path(file_path).suffix.lower() in [".opus", ".mp3"]:
            analysis_text += f"  {Fore.YELLOW}[INFO] Lossy codec: {codec}{Style.RESET_ALL}\n"
        if bit_depth != "N/A" and int(bit_depth) < 16:
            analysis_text += f"  {Fore.RED}[WARNING] Low bit depth may indicate lossy encoding.{Style.RESET_ALL}\n"
        if sample_rate != "N/A" and int(sample_rate) < 44100:
            analysis_text += f"  {Fore.RED}[WARNING] Low sample rate may indicate lossy encoding.{Style.RESET_ALL}\n"
        analysis_text += "\n"
        return analysis_text
    except Exception as e:
        return f"{Fore.RED}Analyzing: {file_path}\n  [ERROR] Failed to analyze: {e}{Style.RESET_ALL}\n\n"

def analyze_audio(args):
    """Handle the 'info' command to analyze audio file metadata."""
    if not utils.is_ffprobe_installed():
        print(f"{Fore.RED}Error: ffprobe is not installed or not in your PATH.{Style.RESET_ALL}")
        return

    print_logo()
    path = args.path
    output = args.output
    verbose = args.verbose
    num_workers = args.workers if args.workers is not None else (os.cpu_count() or 4)

    # Determine files to analyze
    if os.path.isfile(path) and os.path.splitext(path)[1].lower() in utils.AUDIO_EXTENSIONS:
        audio_files = [Path(path)]
    elif os.path.isdir(path):
        audio_files = [file for ext in utils.AUDIO_EXTENSIONS for file in Path(path).rglob(f"*{ext}")]
        if not audio_files:
            print(f"{Fore.YELLOW}No audio files found in '{path}'.{Style.RESET_ALL}")
            return
    else:
        print(f"{Fore.RED}'{path}' is not a file or directory.{Style.RESET_ALL}")
        return

    if verbose:
        # Sequential analysis with console output
        print(f"{Fore.CYAN}Running in verbose mode...{Style.RESET_ALL}")
        for audio_file in audio_files:
            print(analyze_single_file(str(audio_file)))
    else:
        # Parallel analysis with file output
        output_file = f"audio_analysis_{datetime.datetime.now().strftime('%Y%m%d')}.txt" if output == "audio_analysis.txt" else output
        with open(output_file, "w") as f:
            with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(analyze_single_file, str(file)) for file in audio_files]
                for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Analyzing audio"):
                    f.write(future.result())
        print(f"{Fore.GREEN}Analysis complete. Results saved to '{output_file}'{Style.RESET_ALL}")

def register_command(subparsers):
    """Register the 'info' command with the subparsers."""
    info_parser = subparsers.add_parser("info", help="Analyze audio file metadata with ffprobe")
    info_parser.add_argument("path", type=utils.path_type, help="Path to an audio file or directory")
    info_parser.add_argument("-o", "--output", default="audio_analysis.txt", help="Output file for results (default: audio_analysis.txt)")
    info_parser.add_argument("--verbose", action="store_true", help="Display results in console (sequential mode)")
    info_parser.set_defaults(func=analyze_audio)