# SpotiCMD
![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Spotify](https://img.shields.io/badge/Spotify-API-1DB954?style=for-the-badge&logo=spotify)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows)
![Rich](https://img.shields.io/badge/Rich-TUI-orange?style=for-the-badge)

**A Real-Time Spotify Visualizer for Your Terminal**

<img width="527" height="722" alt="demo" src="https://github.com/user-attachments/assets/40030c4d-8ad6-4d34-8004-169b187f84ac" />

---

## About

SpotiCMD transforms your terminal into a live Spotify visualizer. It fetches your currently playing track, renders the album artwork as high-definition TrueColor ASCII art, and provides seamless playback controls—all without leaving the command line. Built for developers who appreciate the intersection of functionality and aesthetics in terminal environments.

---

## How It Works (Under the Hood)

SpotiCMD combines several advanced techniques to deliver a smooth, visually rich terminal experience. Here's a detailed breakdown of the core technical implementations:

### 1. TrueColor ASCII Art Generation

The album art conversion process involves multiple stages of image manipulation:

**Image Processing Pipeline:**
- **Fetching & Resizing:** The script uses the `Pillow` library to download the album image from Spotify's CDN and resize it to fit the terminal dimensions while maintaining aspect ratio. The target size is calculated based on terminal columns and rows to ensure optimal display.
  
- **Grayscale Density Mapping:** Each pixel is converted to grayscale to calculate its luminance value (0-255). This value determines which ASCII character to use from a density gradient string, typically ordered from dense to sparse:
```python
  ASCII_CHARS = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
```
  Darker pixels map to denser characters (like `$` or `@`), while lighter pixels use sparse characters (like `.` or ` `).

- **TrueColor Reapplication:** After determining the character for each pixel, the script retrieves the original RGB values from the unmodified image and applies them using the `Rich` library's styling system. Each ASCII character is wrapped with ANSI escape codes that specify its exact foreground color, creating a full-color representation:
```python
  from rich.text import Text
  colored_char = Text(char, style=f"rgb({r},{g},{b})")
```

This technique preserves the visual fidelity of the original album art while conforming to the constraints of character-based rendering.

### 2. Flicker-Free UI Rendering

Early versions suffered from screen flicker caused by using `os.system('cls')` or `os.system('clear')` to refresh the display. This approach clears the entire terminal buffer, causing a visible flash and scrollback pollution.

**Solution: Rich's Live Display Context**

The `Rich` library's `Live` display manager solves this by implementing double-buffering and differential rendering:
```python
from rich.live import Live

with Live(layout, refresh_per_second=4, screen=True) as live:
    while True:
        # Update only changed components
        live.update(layout)
```

**Technical Benefits:**
- **In-Place Updates:** Only modified regions (like the progress bar or timestamp) are redrawn, leaving static elements (ASCII art, track info) untouched.
- **ANSI Cursor Control:** Uses escape sequences to reposition the cursor rather than clearing the screen.
- **Reduced Terminal Load:** Minimizes the amount of data written to stdout, improving performance on slower terminals or SSH sessions.

### 3. Precision UI Layout with Hidden Grid Tables

Terminal text alignment is notoriously difficult due to variable character widths and ANSI escape code interference with string length calculations. SpotiCMD uses a creative workaround:

**Hidden Table Grid Strategy:**
```python
from rich.table import Table

status_bar = Table.grid(padding=0, expand=True)
status_bar.add_column(justify="left", ratio=1)   # PLAYING/PAUSED
status_bar.add_column(justify="center", ratio=1) # Timestamp
status_bar.add_column(justify="right", ratio=1)  # Empty spacer

status_bar.add_row(status_text, timestamp, "")
```

The `Table.grid` method creates an invisible table without borders or cell separation. By defining column ratios and justification, we achieve:
- **Pixel-Perfect Centering:** The timestamp is mathematically centered regardless of terminal width.
- **Dynamic Spacing:** Columns automatically adjust to window resizes.
- **Clean Code:** Avoids manual padding calculations with `.ljust()` and `.rjust()`, which break when ANSI codes are present.

### 4. Non-Blocking Keyboard Input

Traditional `input()` calls block execution, freezing the visualizer until the user presses Enter. SpotiCMD requires asynchronous input detection to maintain real-time updates.

**Implementation with msvcrt (Windows):**
```python
import msvcrt

if msvcrt.kbhit():
    key = msvcrt.getch().decode('utf-8')
    if key == '5':
        sp.pause_playback() if is_playing else sp.start_playback()
    elif key == '6':
        sp.next_track()
    elif key == '4':
        sp.previous_track()
```

**How It Works:**
- **`msvcrt.kbhit()`:** Checks if a key is waiting in the input buffer without blocking.
- **`msvcrt.getch()`:** Reads a single character immediately if available.
- **Event Loop Integration:** This check runs in each iteration of the main loop, allowing smooth progress bar updates while remaining responsive to user commands.

**Cross-Platform Note:** For Linux/macOS compatibility, consider using `select` on `sys.stdin` or the `pynput` library for similar non-blocking behavior.

### 5. Robust OAuth2 Authentication Flow

Spotify's API requires OAuth2 authentication with specific permission scopes. SpotiCMD uses `spotipy` to handle the authorization flow:

**Scope Management:**
```python
scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing"
```

- **`user-read-playback-state`:** Retrieves current track, progress, and device info.
- **`user-modify-playback-state`:** Enables play/pause, skip, and previous track controls.

**Token Caching Strategy:**

`spotipy` automatically caches access tokens in a local `.cache` file after the initial authorization. This prevents repeated browser-based login prompts:
```python
auth_manager = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri="http://localhost:8888/callback",
    scope=scope,
    cache_path=".cache"
)
sp = spotipy.Spotify(auth_manager=auth_manager)
```

**Flow Breakdown:**
1. First run opens a browser for user consent.
2. Authorization code is exchanged for an access token and refresh token.
3. Tokens are serialized to `.cache`.
4. Subsequent runs load cached tokens, refreshing them transparently when expired.

**Error Handling:** The script validates credentials on startup and provides clear error messages if API keys are missing or scopes are insufficient.

### 6. Deployment via System Path Integration

For instant accessibility, SpotiCMD uses a Windows Batch launcher:

**spoticmd.bat:**
```batch
@echo off
python "C:\path\to\SpotiCMD\main.py"
```

**Setup Steps:**
1. Place `spoticmd.bat` in a directory included in your System PATH (e.g., `C:\Windows\System32` or a custom `C:\bin`).
2. Open any terminal window and type `spoticmd` to launch the visualizer instantly, regardless of your current directory.

**Alternative Deployment:**
- **Unix/Linux:** Create a bash script with `#!/usr/bin/env python3` shebang and place it in `/usr/local/bin`.
- **Python Entry Points:** Package the project with `setuptools` and define an entry point in `setup.py` for global CLI access.

---

## Features

**Visual & Interactive**
- High-definition TrueColor ASCII art rendering of album covers
- Real-time progress bar with elapsed/total time display
- Dynamic status indicators (PLAYING/PAUSED)

**Playback Controls**
- Play/Pause toggle
- Skip to next track
- Return to previous track

**Performance**
- Flicker-free rendering at 4 FPS refresh rate
- Minimal CPU usage with efficient differential updates
- Sub-second response to keyboard commands

**User Experience**
- One-time OAuth2 authentication
- Automatic token refresh
- Global command line access via system PATH

---

## Installation

### Prerequisites
- Python 3.7 or higher
- Active Spotify Premium account (required for playback control API)
- Spotify Developer application credentials

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/SpotiCMD.git
cd SpotiCMD
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

**Required packages:**
```
spotipy
python-dotenv
Pillow
rich
requests
```

### Step 3: Configure Spotify API Credentials

1. Navigate to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new application
3. Note your **Client ID** and **Client Secret**
4. Add `http://localhost:8888/callback` to the Redirect URIs in your app settings

Create a `.env` file in the project root:
```env
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
```

### Step 4: Run SpotiCMD

**Direct Execution:**
```bash
python main.py
```

**Global Access (Windows):**
1. Edit `spoticmd.bat` to point to your `main.py` file
2. Move `spoticmd.bat` to a directory in your System PATH
3. Open any terminal and run:
```cmd
   spoticmd
```

On first run, you'll be redirected to Spotify's authorization page. Grant permissions, and the token will be cached for future sessions.

---

## Controls

SpotiCMD uses numeric keypad-style controls for intuitive playback management:

| Key | Action              |
|-----|---------------------|
| `5` | Toggle Play/Pause   |
| `6` | Skip to Next Track  |
| `4` | Previous Track      |

**Note:** Keys are registered immediately without requiring Enter. Press `Ctrl+C` to exit the visualizer.

---

## Technical Requirements

- **Terminal:** Supports TrueColor (24-bit RGB) rendering. Tested on:
  - Windows Terminal
  - PowerShell 7+
  - iTerm2 (macOS)
  - GNOME Terminal (Linux)
  
- **Spotify:** Must have an active playback session (device playing or paused). The visualizer cannot start playback on an idle account.

---

## Troubleshooting

**"No active device found"**
- Ensure Spotify is open and a device is selected (Desktop, Mobile, Web Player)
- Start playing any track before launching SpotiCMD

**Colors appear incorrect or missing**
- Verify your terminal supports TrueColor (`echo $COLORTERM` should return `truecolor`)
- Use a modern terminal emulator

**Authentication errors**
- Delete `.cache` file and re-authorize
- Verify `.env` credentials match your Spotify Developer Dashboard
- Ensure redirect URI is exactly `http://localhost:8888/callback`

---

## Contributing

Contributions are welcome. Please open an issue to discuss proposed changes before submitting pull requests.

**Development Setup:**
```bash
git checkout -b feature/your-feature-name
# Make changes
pytest tests/  # Run tests if available
git commit -m "Add: feature description"
```

---

## License

This project is licensed under the MIT License. See `LICENSE` file for details.

---

## Acknowledgments

Built with:
- [spotipy](https://spotipy.readthedocs.io/) - Spotify Web API wrapper
- [Rich](https://rich.readthedocs.io/) - Terminal rendering library
- [Pillow](https://pillow.readthedocs.io/) - Image processing

