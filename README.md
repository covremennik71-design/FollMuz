# FollMuz2 - Web Music Player

## Quick Start

### First Time Setup:
1. Run `install.bat` to install required dependencies
2. Run `start.vbs` to launch the server (hidden mode)
3. Browser will open automatically at http://127.0.0.1:5000

### Normal Launch:
- Double-click `start.vbs` - server runs in background, no console window

### Debug Mode:
- Run `run.bat` - shows all checks and server output in console

### Troubleshooting:
- Run `diagnose.bat` to check Python, dependencies, and server status

## Requirements:
- Python 3.8+ (tested on 3.14)
- FFmpeg (for audio editing features)
- Internet connection (for yt-dlp downloads)

## Dependencies (installed by install.bat):
- Flask
- Mutagen
- yt-dlp

## Features:
- Music library browser
- YouTube audio download
- Playlist management (folders + .m3u playlists)
- Audio editor (trim, fade, normalize, convert)
- Hash cache for temporary downloads
- Recommendations based on your library
- Web-based interface

## File Structure:
```
FollMuz2/
├── app.py              # Flask server
├── start.vbs           # Hidden launcher (recommended)
├── run.bat             # Debug launcher with console
├── install.bat         # Install dependencies
├── diagnose.bat        # Diagnostic tool
├── settings.json       # User settings (auto-created)
├── templates/
│   └── index.html      # Web interface
├── static/
│   ├── style.css       # Styles
│   └── default_cover.png
├── downloads/          # Downloaded tracks
├── hash_cache/         # Temporary cache
└── error.log           # Error log (if server fails)
```

## Stopping the Server:
- Open Task Manager (Ctrl+Shift+Esc)
- Find "pythonw.exe" process
- End it

Or run in console:
```
taskkill /IM pythonw.exe /F
```

## Common Issues:

### "Python not found"
- Install Python from https://www.python.org/
- IMPORTANT: Check "Add Python to PATH" during installation

### "Missing dependencies"
- Run `install.bat`

### "FFmpeg not found"
- Download FFmpeg from https://ffmpeg.org/download.html
- Add to PATH or place in C:\ffmpeg\bin

### "Port 5000 is busy"
- Another instance is running
- Kill pythonw.exe in Task Manager
- Or change port in app.py: `app.run(port=5001)`

### Server fails to start
- Run `diagnose.bat` to see detailed errors
- Check `error.log` for Python tracebacks
