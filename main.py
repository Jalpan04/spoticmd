import os
import time
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
import msvcrt
import logging

from rich.live import Live
from rich.panel import Panel
from rich.align import Align
from rich.console import Group
from rich.text import Text
from rich.console import Console
from rich.progress_bar import ProgressBar
from rich.style import Style
from rich.table import Table

# --- SILENCE LOGS ---
logging.getLogger('spotipy').setLevel(logging.CRITICAL)
logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

# --- LOAD ENV ---
load_dotenv()

SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

# Permissions
SCOPE = "user-read-currently-playing user-modify-playback-state user-read-playback-state"

# --- ASCII SETTINGS ---
WIDTH = 70
ASCII_CHARS = r"$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "


def resize_image(image, new_width=WIDTH):
    (original_width, original_height) = image.size
    aspect_ratio = original_height / float(original_width)
    new_height = int(aspect_ratio * new_width * 0.55)
    return image.resize((new_width, new_height))


def generate_ascii_art(url):
    try:
        response = requests.get(url)
        im = Image.open(BytesIO(response.content))
        im = resize_image(im)
        if im.mode != 'RGB': im = im.convert('RGB')
        pixels = im.load()
        width, height = im.size
        ascii_text = Text()

        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                char_index = int((gray / 255) * (len(ASCII_CHARS) - 1))
                char = ASCII_CHARS[char_index]
                ascii_text.append(char, style=Style(color=f"rgb({r},{g},{b})"))
            ascii_text.append("\n")
        return ascii_text
    except Exception:
        return Text("No Image", style="red")


def format_time(ms):
    seconds = int((ms / 1000) % 60)
    minutes = int((ms / (1000 * 60)) % 60)
    return f"{minutes:02}:{seconds:02}"


def generate_layout(track_info, ascii_art, status_msg, is_playing):
    if not track_info:
        return Panel(Align.center(f"Waiting for Spotify...\n\n{status_msg}"), title="Status", style="yellow")

    art_display = Align.center(ascii_art)

    info_text = Text()
    info_text.append(f"\n{track_info['name']}\n", style="bold white")
    info_text.append(f"{track_info['artist']}\n", style="yellow")
    info_text.append(f"{track_info['album']}\n", style="dim white")

    completed = track_info['progress']
    total = track_info['duration']

    # --- UI GRID LAYOUT ---

    # 1. Left: Status (Play/Pause)
    status_str = "▶ PLAYING" if is_playing else "❚❚ PAUSED"
    status_style = "bold green" if is_playing else "bold red"
    status_text = Text(status_str, style=status_style)

    # 2. Center: Time
    time_str = f"{format_time(completed)} / {format_time(total)}"
    time_text = Text(time_str, style="white")

    # 3. Create Grid
    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=1)  # Left
    grid.add_column(justify="center", ratio=1)  # Center
    grid.add_column(justify="right", ratio=1)  # Right (Empty Balance)

    # Add the row
    grid.add_row(status_text, time_text, Text(""))

    bar = ProgressBar(total=total, completed=completed, width=WIDTH, complete_style="green", finished_style="green")

    # Controls Text (with Markup for colors)
    controls = Text.from_markup(f"\n{status_msg}")
    controls.style = "dim grey"
    controls.justify = "center"

    content = Group(
        art_display,
        Align.left(info_text),
        Align.center(bar),
        grid,  # Insert Grid
        Align.center(controls)
    )

    border_color = "green" if is_playing else "red"
    return Panel(content, title="Now Playing", border_style=border_color, expand=False)


def main():
    console = Console()
    if not SPOTIPY_CLIENT_ID:
        print("Error: .env missing")
        return

    # --- DEPLOYMENT MODE (Browser Disabled) ---
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                                   client_secret=SPOTIPY_CLIENT_SECRET,
                                                   redirect_uri=SPOTIPY_REDIRECT_URI,
                                                   scope=SCOPE,
                                                   open_browser=False))

    last_track_id = None
    cached_ascii = Text("")
    last_track_info = None
    is_playing_cache = False

    default_status = "[5] Pause/Play  |  [6] Next  |  [4] Prev"
    current_status = default_status

    console.print("Spotify Visualizer Running...", style="green")
    console.print("[dim]If 'Waiting', press Play on Spotify manually once.[/dim]")

    with Live(console=console, auto_refresh=False) as live:
        while True:
            try:
                # --- KEYBOARD CONTROLS ---
                if msvcrt.kbhit():
                    key = msvcrt.getch().lower()
                    ui_info = last_track_info if last_track_info else {}

                    try:
                        if key == b'5':
                            current_status = "[yellow]Sending Command...[/yellow]"
                            live.update(generate_layout(ui_info, cached_ascii, current_status, is_playing_cache),
                                        refresh=True)
                            current = sp.current_playback()
                            if current and current['is_playing']:
                                sp.pause_playback()
                                current_status = "[red]PAUSED[/red]"
                                is_playing_cache = False
                            else:
                                sp.start_playback()
                                current_status = "[green]PLAYING[/green]"
                                is_playing_cache = True

                        elif key == b'6':
                            current_status = "[yellow]SKIPPING >>[/yellow]"
                            live.update(generate_layout(ui_info, cached_ascii, current_status, is_playing_cache),
                                        refresh=True)
                            sp.next_track()

                        elif key == b'4':
                            current_status = "[yellow]<< PREV[/yellow]"
                            live.update(generate_layout(ui_info, cached_ascii, current_status, is_playing_cache),
                                        refresh=True)
                            sp.previous_track()

                        time.sleep(0.2)
                    except Exception as e:
                        current_status = f"[red]CMD ERROR: {str(e)}[/red]"
                else:
                    if "ERROR" not in current_status and "..." not in current_status:
                        current_status = default_status

                # --- DATA FETCHING ---
                try:
                    current_track = sp.current_user_playing_track()
                except Exception:
                    current_track = None

                if current_track and current_track['item']:
                    track_data = current_track['item']
                    track_id = track_data['id']
                    is_playing_cache = current_track['is_playing']

                    if track_id != last_track_id:
                        img_url = track_data['album']['images'][0]['url']
                        cached_ascii = generate_ascii_art(img_url)
                        last_track_id = track_id

                    last_track_info = {
                        'name': track_data['name'],
                        'artist': track_data['artists'][0]['name'],
                        'album': track_data['album']['name'],
                        'progress': current_track['progress_ms'],
                        'duration': track_data['duration_ms']
                    }

                live.update(generate_layout(last_track_info, cached_ascii, current_status, is_playing_cache),
                            refresh=True)
                time.sleep(0.5)

            except Exception as e:
                time.sleep(2)


if __name__ == "__main__":
    main()