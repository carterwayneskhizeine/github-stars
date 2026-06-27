# OpenClaw Gateway Watchdog

A Windows service monitor that automatically keeps your OpenClaw Gateway running. If the process stops or crashes, the watchdog automatically restarts it after a 3-second delay.

## Features

- 🔄 **Auto-restart**: Automatically restarts OpenClaw Gateway if it stops
- ⏱️ **Smart delay**: Waits 3 seconds before restart to prevent rapid cycling
- 🚀 **Boot startup**: Runs automatically when Windows starts
- 🔍 **Process monitoring**: Checks every 5 seconds if the gateway is running
- 📊 **Logging**: Shows timestamps and status updates
- 🪟 **Background operation**: Runs silently in the background

## Prerequisites

- Windows operating system
- PowerShell (comes with Windows)
- OpenClaw CLI installed and available in PATH
- Node.js (required for OpenClaw)

## Installation

### Quick Install

1. Clone this repository:
```bash
git clone https://github.com/YOUR_USERNAME/openclaw-watchdog.git
cd openclaw-watchdog
```

2. Run the startup configuration script:
```powershell
powershell -ExecutionPolicy Bypass -File create-startup-shortcut.ps1
```

This will:
- Set up the watchdog to run at Windows startup
- Create a shortcut in your Startup folder

### Manual Install

1. Copy all files to a location of your choice (e.g., `C:\Users\YourName\openclaw-watchdog\`)

2. Create a shortcut to `start-openclaw-watchdog.vbs` in your Windows Startup folder:
   - Press `Win+R`
   - Type `shell:startup`
   - Create a shortcut to the VBS file

3. Restart your computer or double-click `start-openclaw-watchdog.vbs` to start immediately

## Usage

### Starting the Watchdog

The watchdog starts automatically at Windows login. To start it manually:

```cmd
wscript start-openclaw-watchdog.vbs
```

Or simply double-click `start-openclaw-watchdog.vbs`

### Stopping the Watchdog

1. Open Task Manager (`Ctrl+Shift+Esc`)
2. Find the PowerShell process running the watchdog
3. End the task

### Testing the Watchdog

1. Start the watchdog
2. Find the OpenClaw Gateway window
3. Close it
4. Wait 3 seconds - the watchdog will automatically restart it!

### Disable Auto-Start

To prevent the watchdog from starting at boot:

1. Press `Win+R`
2. Type `shell:startup`
3. Delete the "OpenClaw-Watchdog" shortcut

## Files

- **`openclaw-watchdog.ps1`** - Main monitoring script that checks and restarts the process
- **`start-openclaw-watchdog.vbs`** - VBScript launcher that runs the PowerShell script hidden in background
- **`create-startup-shortcut.ps1`** - Setup script that adds the watchdog to Windows Startup

## How It Works

1. The watchdog runs in the background as a PowerShell script
2. Every 5 seconds, it checks if a Node.js process with "openclaw gateway" is running
3. If the process is not found:
   - Waits 3 seconds (configurable)
   - Starts a new instance using `openclaw gateway` command
   - Continues monitoring

## Configuration

You can modify these settings in `openclaw-watchdog.ps1`:

```powershell
$processName = "node"                    # Process to monitor
$commandLine = "openclaw gateway"        # Command to check
$restartDelay = 3                        # Seconds to wait before restart
```

Monitoring interval (default 5 seconds):
```powershell
Start-Sleep -Seconds 5  # Change this value
```

## Troubleshooting

### Watchdog doesn't start OpenClaw Gateway

- Verify that `openclaw gateway` command works in CMD
- Check if Node.js is properly installed: `node --version`
- Verify OpenClaw is installed globally: `npm list -g openclaw`

### OpenClaw Gateway keeps stopping

- Check OpenClaw Gateway logs for errors
- Verify your OpenClaw configuration is correct
- Ensure all dependencies are installed

### Watchdog not starting at boot

- Check if the shortcut exists in Startup folder: `shell:startup`
- Verify the shortcut points to the correct VBS file path
- Check Windows Event Viewer for startup errors

## Requirements

- **Windows** 7 or later
- **PowerShell** 5.0 or later (included in Windows 10+)
- **OpenClaw** installed via npm
- **Node.js** for running OpenClaw

## License

MIT License - Feel free to use and modify as needed.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you encounter issues:
1. Check the [Troubleshooting](#troubleshooting) section
2. Open an issue on GitHub with:
   - Your Windows version
   - Node.js version (`node --version`)
   - OpenClaw version
   - Error messages or logs

## Author

Created for monitoring and auto-restarting OpenClaw Gateway on Windows systems.

---

**Note**: This tool is designed specifically for Windows. For Linux/Mac, consider using systemd or launchd respectively.
