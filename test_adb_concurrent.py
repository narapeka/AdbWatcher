#!/usr/bin/env python3
import sys
import time
import os
import threading
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.exceptions import AdbTimeoutError, AdbConnectionError, DeviceAuthError, TcpTimeoutException

# --- Configuration (Copy from previous test) ---
DEVICE_IP = '192.168.1.88' 
DEVICE_PORT = 5555
ADB_KEY_PATH = os.path.expanduser('~/.android/adbkey') 
CONNECTION_TIMEOUT_S = 5 
LOGCAT_BUFFER = "system"
LOGCAT_TAGS = "ActivityTaskManager:I"
LOGCAT_PATTERN = "com.doopoodigital.dpplayer.app"
# Use a long read timeout for the logcat stream itself to keep it active
LOGCAT_READ_TIMEOUT_S = 60 

logcat_cmd_parts = ["logcat", f"--buffer={LOGCAT_BUFFER}"]
if LOGCAT_TAGS:
    logcat_cmd_parts.extend([LOGCAT_TAGS, "*:S"])
if LOGCAT_PATTERN:
    logcat_cmd_parts.extend(["-e", LOGCAT_PATTERN])
logcat_cmd_parts.append("-v time")
LOGCAT_COMMAND = ' '.join(logcat_cmd_parts)
# --- End Configuration ---

def load_adb_key(key_path):
    """Loads the private ADB key."""
    if not os.path.exists(key_path):
        print(f"[Main] Error: ADB key file not found at {key_path}", file=sys.stderr)
        return None
    try:
        with open(key_path, 'r') as f:
            priv_key = f.read()
        return PythonRSASigner('', priv_key) 
    except Exception as e:
        print(f"[Main] Error loading ADB key from {key_path}: {e}", file=sys.stderr)
        return None

def logcat_reader_thread(device, stop_event):
    """Target function for the background thread to read logcat."""
    stream_generator = None
    print("[Thread] Logcat reader thread started.")
    try:
        print(f"[Thread] Starting streaming shell: '{LOGCAT_COMMAND}'")
        stream_generator = device.streaming_shell(
            LOGCAT_COMMAND,
            transport_timeout_s=None, # No timeout on transport writes
            read_timeout_s=LOGCAT_READ_TIMEOUT_S # Long timeout for reading logs
        )
        
        print("[Thread] Iterating over logcat stream...")
        for line in stream_generator:
            if stop_event.is_set():
                print("[Thread] Stop event received, exiting logcat loop.")
                break
            if line is None:
                print("[Thread] Logcat stream ended (None received).")
                break
            print(f"[Logcat] {line.strip()}")
            # Add a small sleep to prevent tight loop if logs are rapid & simulate work
            # time.sleep(0.01)

    except TcpTimeoutException:
        print(f"[Thread] Logcat stream timed out after {LOGCAT_READ_TIMEOUT_S}s.")
    except AdbConnectionError as e:
         print(f"[Thread] Connection error during logcat streaming: {e}", file=sys.stderr)
    except Exception as e:
        import traceback
        print(f"[Thread] Unexpected error during logcat streaming: {e}", file=sys.stderr)
        traceback.print_exc()
    finally:
        print("[Thread] Logcat reader thread finished.")
        # Note: Don't close the main device connection from the thread

def main():
    """Connects, starts logcat reader, runs echo test, cleans up."""
    print(f"[Main] Attempting to load ADB key from: {ADB_KEY_PATH}")
    signer = load_adb_key(ADB_KEY_PATH)
    if not signer:
        return 1

    print(f"[Main] Creating AdbDeviceTcp for {DEVICE_IP}:{DEVICE_PORT}")
    # Use None default timeout to prevent low-level socket timeouts interfering
    device = AdbDeviceTcp(DEVICE_IP, DEVICE_PORT, default_transport_timeout_s=None) 
    logcat_thread = None
    stop_event = threading.Event()

    try:
        print("[Main] Connecting to device...")
        device.connect(rsa_keys=[signer], auth_timeout_s=CONNECTION_TIMEOUT_S)
        print("[Main] Connection successful!")

        print("[Main] Starting logcat reader thread...")
        logcat_thread = threading.Thread(
            target=logcat_reader_thread, 
            args=(device, stop_event),
            daemon=True # Allow main thread to exit even if this thread hangs (optional)
        )
        logcat_thread.start()

        print("[Main] Waiting a few seconds for logcat stream to initialize...")
        time.sleep(3) # Give the thread time to start the stream

        print("[Main] Attempting to execute 'echo test' while logcat runs...")
        try:
            # Use a reasonable timeout for this short command
            response = device.shell("echo test", read_timeout_s=5, transport_timeout_s=5)
            print(f"[Main] 'echo test' command response: {response.strip()}")
        except (AdbTimeoutError, AdbConnectionError, TcpTimeoutException) as e:
            print(f"[Main] Failed to execute 'echo test': {e}", file=sys.stderr)
        except Exception as e:
            import traceback
            print(f"[Main] Unexpected error during 'echo test': {e}", file=sys.stderr)
            traceback.print_exc()
            
        print("[Main] Waiting a bit longer...")
        time.sleep(5)

    except ConnectionRefusedError:
        print(f"[Main] Error: Connection refused by {DEVICE_IP}:{DEVICE_PORT}.", file=sys.stderr)
        return 1
    except DeviceAuthError as auth_err:
         print(f"[Main] Error: Authentication failed: {auth_err}", file=sys.stderr)
         return 1
    except AdbConnectionError as conn_err:
         print(f"[Main] Error: Connection problem: {conn_err}", file=sys.stderr)
         return 1
    except Exception as e:
        import traceback
        print(f"[Main] An unexpected error occurred in main setup: {e}", file=sys.stderr)
        traceback.print_exc() 
        return 1
    except KeyboardInterrupt:
        print("[Main] Keyboard interrupt detected.")
    finally:
        print("[Main] Cleaning up...")
        if stop_event:
            print("[Main] Signaling logcat thread to stop...")
            stop_event.set()
        
        if logcat_thread and logcat_thread.is_alive():
            print("[Main] Waiting for logcat thread to join...")
            logcat_thread.join(timeout=5) # Wait max 5 seconds for thread
            if logcat_thread.is_alive():
                print("[Main] Logcat thread did not exit cleanly.", file=sys.stderr)

        if device and device.available:
            try:
                print("[Main] Closing device connection.")
                device.close()
            except Exception as e_close:
                 print(f"[Main] Error closing device: {e_close}", file=sys.stderr)

    print("[Main] Script finished.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 