# OpenClaw Windows Node

Production-ready Electron desktop node for OpenClaw Gateway on Windows 10/11.

## Implemented capabilities
- Gateway WebSocket connection with challenge handshake (`connect.challenge` -> signed `connect`)
- Device identity generation/storage (Ed25519 keypair persisted on Windows)
- Auto reconnect with exponential backoff
- Structured logging with log rotation
- Node invoke command handlers:
  - `system.run`
  - `system.which`
  - `browser.proxy`
  - `camera`
  - `screen`
  - `location`
  - `notifications`
  - `messaging`
  - `node.invoke`

## Architecture
- `src/main.ts`: Electron app entrypoint and lifecycle
- `src/core/gatewayClient.ts`: Gateway protocol transport and reconnect
- `src/core/deviceIdentity.ts`: key management and payload signatures
- `src/core/commandRouter.ts`: dispatches `node.invoke.request` commands
- `src/core/commands/system.ts`: `system.*` command implementations
- `src/electron/browserManager.ts`: browser proxy sessions
- `src/electron/desktopCapabilities.ts`: camera, screen, location, notifications, messaging

## Commands and examples

### `system.which`
Params:
```json
{ "bins": ["powershell", "cmd", "git"] }
```

### `system.run`
Params:
```json
{ "command": ["cmd.exe", "/c", "whoami"], "timeoutMs": 10000 }
```

### `browser.proxy`
- Open external browser:
```json
{ "action": "open", "url": "https://example.com" }
```
- Navigate hidden managed session:
```json
{ "action": "navigate", "sessionId": "default", "url": "https://example.com" }
```
- Capture screenshot from managed session:
```json
{ "action": "screenshot", "sessionId": "default" }
```

### `camera`
```json
{ "action": "capture", "width": 1280, "height": 720 }
```

### `screen`
```json
{ "action": "capture", "maxWidth": 1920, "maxHeight": 1080 }
```

### `location`
```json
{ "action": "get", "highAccuracy": true, "timeoutMs": 8000 }
```

### `notifications`
```json
{ "action": "send", "title": "OpenClaw", "body": "Node online" }
```

### `messaging`
```json
{ "action": "send", "event": "node.message", "payload": { "text": "hello" } }
```

### `node.invoke`
```json
{
  "command": "system.which",
  "params": { "bins": ["node"] }
}
```

## Development
```bash
npm install
npm run check
npm run test
npm run build
npm start
```

## Windows build output
See `BUILD.md` for exact Windows build commands.

## Setup and operations
See `SETUP.md` for installation, environment variables, startup, and validation.

## Testing strategy
- Linux/macOS: run unit tests for protocol and command logic
- Windows: run manual/integration validation for desktop capabilities and installer output
- Windows integration stub: `test/windows.integration.test.ts`

## Limitations
- Windows-specific capabilities (`camera`, `location`, some notification behavior) require running on Windows desktop with user permissions.
- Packaging final release installer should be done on Windows.
