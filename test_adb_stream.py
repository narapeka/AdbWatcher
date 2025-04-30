#!/usr/bin/env python3
import sys
import time
import os
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
# Add necessary exception types
from adb_shell.exceptions import AdbTimeoutError, AdbConnectionError, DeviceAuthError, TcpTimeoutException

# --- Configuration ---
# Replace with the actual IP address of your Android device
DEVICE_IP = '192.168.1.88' 
# Replace with the standard ADB port or the one your device uses
DEVICE_PORT = 5555
# Replace with the path to your adbkey file (not the .pub file)
# Common locations:
# - Linux/macOS: ~/.android/adbkey
# - Windows: %USERPROFILE%\.android\adbkey
ADB_KEY_PATH = os.path.expanduser('~/.android/adbkey') 
# Timeout for initial connection attempts (seconds) - Can be different from stream read timeout
CONNECTION_TIMEOUT_S = 5 

# Logcat Filtering Options (Read from backend/config/config.yaml)
LOGCAT_BUFFER = "system"  # From config.yaml
LOGCAT_TAGS = "ActivityTaskManager:I" # From config.yaml
LOGCAT_PATTERN = "com.doopoodigital.dpplayer.app" # From config.yaml

# Timeout for reading from the logcat stream (seconds)
# Set reasonably high to avoid false positives if logs are sparse, but low enough to detect disconnects
LOGCAT_READ_TIMEOUT_S = 30 

# Construct the Logcat command with filters
logcat_cmd_parts = ["logcat", f"--buffer={LOGCAT_BUFFER}"]
if LOGCAT_TAGS:
    # Add tags and silence others
    logcat_cmd_parts.extend([LOGCAT_TAGS, "*:S"])
if LOGCAT_PATTERN:
    # Add regex filter pattern - Ensure proper escaping if needed for shell
    # Note: adb shell might handle regex differently than Python re
    # Simple patterns are usually fine. Complex ones might need shell escaping.
    logcat_cmd_parts.extend(["-e", LOGCAT_PATTERN])
# Add format specifier (optional, could be part of tags/pattern logic too)
logcat_cmd_parts.append("-v time")

LOGCAT_COMMAND = ' '.join(logcat_cmd_parts)
# --- End Configuration ---

def load_adb_key(key_path):
    """Loads the private ADB key."""
    if not os.path.exists(key_path):
        print(f"Error: ADB key file not found at {key_path}", file=sys.stderr)
        print("Please ensure ADB is set up and the path is correct.", file=sys.stderr)
        return None
    try:
        with open(key_path, 'r') as f:
            priv_key = f.read()
        # Public key is usually key_path + '.pub', but signer only needs private
        # If .pub exists, we could load it, but PythonRSASigner only uses priv
        # pub_key_path = key_path + '.pub'
        # if os.path.exists(pub_key_path):
        #     with open(pub_key_path, 'r') as f:
        #         pub_key = f.read()
        # else:
        #     pub_key = '' # Or handle error if public key is strictly needed later

        # PythonRSASigner primarily uses the private key for signing challenges
        return PythonRSASigner('', priv_key) 
    except Exception as e:
        print(f"Error loading ADB key from {key_path}: {e}", file=sys.stderr)
        return None

def main():
    """Connects to the device and streams logcat."""
    print(f"Attempting to load ADB key from: {ADB_KEY_PATH}")
    signer = load_adb_key(ADB_KEY_PATH)
    if not signer:
        return 1

    print(f"Creating AdbDeviceTcp for {DEVICE_IP}:{DEVICE_PORT}")
    # Initialize with default_transport_timeout_s=None to avoid low-level read timeouts during stream
    device = AdbDeviceTcp(DEVICE_IP, DEVICE_PORT, default_transport_timeout_s=None) 
    stream_generator = None

    try:
        print("Connecting to device...")
        # Note: connect() handles the authentication handshake using the signer
        device.connect(rsa_keys=[signer], auth_timeout_s=CONNECTION_TIMEOUT_S)
        print("Connection successful!")

        print(f"Starting streaming shell command: '{LOGCAT_COMMAND}' (Read Timeout: {LOGCAT_READ_TIMEOUT_S}s)")
        # Set transport_timeout_s=None (for writes within the stream), but use a specific read_timeout_s
        stream_generator = device.streaming_shell(
            LOGCAT_COMMAND, 
            transport_timeout_s=None, # Timeout for writes/transport packets within stream
            read_timeout_s=LOGCAT_READ_TIMEOUT_S # Timeout for receiving data from the stream
        )
        
        print("Streaming logcat output... Press Ctrl+C to stop.")
        
        # Loop to handle potential read timeouts
        while True: 
            try:
                # Iterate directly over the generator yielding decoded strings
                for line in stream_generator:
                    print("Performing parallel check...")
                    device.shell('echo test', read_timeout_s=2, transport_timeout_s=2) 
                    print("Connection check successful. Continuing logcat stream...")
                    if line is None: 
                         print("\nLogcat stream ended (None received).")
                         raise StopIteration 
                    print(line.strip()) 
                
                print("\nLogcat stream finished normally.")
                break 

            except TcpTimeoutException: # Catch the specific transport timeout
                # This block is hit if no data arrives within LOGCAT_READ_TIMEOUT_S
                print(f"\nWarning: TCP Read timeout ({LOGCAT_READ_TIMEOUT_S}s) reached.")
                # Perform connection check
                try:
                    print("Performing quick connection check...")
                    device.shell('echo test', read_timeout_s=2, transport_timeout_s=2) 
                    print("Connection check successful. Continuing logcat stream...")
                    continue 
                except (AdbTimeoutError, AdbConnectionError, ConnectionRefusedError, BrokenPipeError, TcpTimeoutException) as check_err: # Include TcpTimeoutException here too
                     print(f"Connection check failed: {check_err}. Assuming device disconnected.")
                     break 
                except Exception as general_check_err:
                     print(f"Unexpected error during connection check: {general_check_err}")
                     break 

            except StopIteration:
                print("Stream iteration stopped.")
                break 

    except ConnectionRefusedError:
        print(f"\nError: Connection refused by {DEVICE_IP}:{DEVICE_PORT}.", file=sys.stderr)
        print("Ensure ADB debugging is enabled on the device and network connection is allowed.", file=sys.stderr)
        return 1
    except DeviceAuthError as auth_err:
         print(f"\nError: Authentication failed: {auth_err}", file=sys.stderr)
         print("Ensure the computer is authorized on the device (check for prompt on device screen).", file=sys.stderr)
         return 1
    except AdbConnectionError as conn_err:
         print(f"\nError: Connection problem: {conn_err}", file=sys.stderr)
         return 1
    except Exception as e:
        # Log the full traceback for unexpected errors
        import traceback
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        traceback.print_exc() 
        return 1
    except KeyboardInterrupt:
        print("\nStopping logcat stream (KeyboardInterrupt)...")
    finally:
        # Ensure the main device connection is closed
        # The generator should handle its own cleanup when iteration stops
        # or when it goes out of scope / is garbage collected, but closing device is good practice.
        if device and device.available:
            try:
                print("Closing device connection.")
                device.close()
            except Exception as e_close:
                 print(f"Error closing device: {e_close}", file=sys.stderr)

    print("Script finished.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 