# ESP32 Magic the Printering

An Arduino project for the [Adafruit Feather ESP32-S3 TFT](https://www.adafruit.com/product/5483) that connects to a WiFi network and triggers card prints by pressing the boot button.

## Requirements

- [PlatformIO](https://platformio.org/) (VS Code extension or CLI)
- Adafruit Feather ESP32-S3 TFT board

## Setup

### 1. Configure WiFi credentials

Copy the example secrets file and fill in your WiFi credentials:

```bash
cp include/secrets.h.example include/secrets.h
```

Edit `include/secrets.h` and replace the placeholder values:

```cpp
#define WIFI_SSID "your_wifi_ssid"
#define WIFI_PASSWORD "your_wifi_password"
```

`secrets.h` is listed in `.gitignore` and will **not** be committed to version control.

### 2. Build and upload

Open the `ESP32/` folder in VS Code with the PlatformIO extension installed, then click **Upload** in the PlatformIO toolbar, or run:

```bash
pio run --target upload
```

## Monitoring WiFi connectivity over Serial

After uploading the firmware, you can watch WiFi connection status in real time using the PlatformIO serial monitor.

### Using PlatformIO

```bash
pio device monitor
```

The baud rate is set to `115200` in `platformio.ini`. You should see output like:

```
Connecting to WiFi...
SSID: your_wifi_ssid
....
WiFi connected!
IP address: 192.168.1.42
Signal strength (RSSI): -55 dBm
```

### Using Arduino IDE

1. Open **Tools → Port** and select the port for your ESP32 (e.g. `COM3` on Windows, `/dev/ttyUSB0` or `/dev/cu.usbmodem*` on macOS/Linux).
2. Open **Tools → Serial Monitor** (or press `Ctrl+Shift+M`).
3. Set the baud rate to **115200** in the bottom-right dropdown of the Serial Monitor.

### Finding the serial port

| OS | Typical port name |
|----|-------------------|
| Windows | `COM3`, `COM4`, … |
| macOS | `/dev/cu.usbmodem*` or `/dev/cu.SLAB_USBtoUART` |
| Linux | `/dev/ttyUSB0` or `/dev/ttyACM0` |

To list available ports on Linux/macOS:

```bash
ls /dev/tty*
```

On Windows, open **Device Manager → Ports (COM & LPT)** to find the port.

### Connection status messages

| Message | Meaning |
|---------|---------|
| `Connecting to WiFi...` | Board is starting the connection attempt |
| `....` (dots) | Each dot is a 500 ms wait; up to 20 attempts are made |
| `WiFi connected!` | Connection succeeded; IP address and signal strength follow |
| `Failed to connect to WiFi. Check your credentials in secrets.h.` | Connection timed out; verify SSID and password in `secrets.h` |
| `WiFi disconnected. Reconnecting...` | Board lost its connection and is attempting to reconnect |
