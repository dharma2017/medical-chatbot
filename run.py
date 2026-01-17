#!/usr/bin/env python
"""
Wrapper script to run Streamlit app and properly manage Flask server lifecycle
Handles both local and cloud environments
"""
import subprocess
import sys
import os
import signal
import time
import atexit
import socket
import platform

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(BASE_DIR, ".flask_pid")

# Detect if running in cloud environment
IS_CLOUD = os.getenv("CLOUD_ENV") == "true" or os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")
IS_WINDOWS = sys.platform == "win32"

def is_port_in_use(port):
    """Check if port is in use"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', port))
            return result == 0
    except Exception as e:
        print(f"   - Port check failed: {e}")
        return False

def kill_process_on_port(port, force=False):
    """Kill any process listening on the given port - multiple methods"""
    if not force and IS_CLOUD:
        print(f"⚠️  Running in cloud environment, skipping aggressive port cleanup")
        return
    
    print(f"🔥 Attempting to kill process on port {port}...")
    
    try:
        # Method 1: Kill by PID file
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE, "r") as f:
                    pid = int(f.read().strip())
                
                if IS_WINDOWS:
                    print(f"   - Killing PID {pid} using taskkill...")
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/F", "/T"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5
                    )
                else:
                    print(f"   - Killing PID {pid} using signal...")
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # Process already dead
                time.sleep(0.5)
            except Exception as e:
                print(f"   - PID kill failed: {e}")
        
        # Method 2: Kill by port (only on Windows with force)
        if IS_WINDOWS and force:
            try:
                print(f"   - Killing process on port {port} using netstat...")
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.split('\n'):
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        if parts:
                            pid = parts[-1]
                            try:
                                subprocess.run(
                                    ["taskkill", "/PID", pid, "/F", "/T"],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    timeout=5
                                )
                                print(f"   - Killed PID {pid}")
                            except:
                                pass
            except Exception as e:
                print(f"   - Netstat kill failed: {e}")
        
        # Method 3: Verify port is released (only check, don't force)
        if not IS_CLOUD:
            for attempt in range(5):
                if not is_port_in_use(port):
                    print(f"✓ Port {port} is now free")
                    return
                time.sleep(0.5)
        
        if is_port_in_use(port) and force:
            print(f"⚠️  Warning: Port {port} still in use after cleanup attempts")
        else:
            print(f"✓ Port cleanup completed")
    
    except Exception as e:
        print(f"⚠️  Error during port cleanup: {e}")
        if not IS_CLOUD:
            raise

def cleanup():
    """Cleanup Flask server on exit"""
    print("\n🛑 Stopping Flask server...")
    try:
        kill_process_on_port(8080, force=True)
    except Exception as e:
        print(f"Error during cleanup: {e}")
    
    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
        except:
            pass

def signal_handler(signum, frame):
    """Handle signals"""
    cleanup()
    sys.exit(0)

# Register cleanup
atexit.register(cleanup)
try:
    signal.signal(signal.SIGINT, signal_handler)
    if not IS_WINDOWS:
        signal.signal(signal.SIGTERM, signal_handler)
except:
    pass

if __name__ == "__main__":
    try:
        # Print environment info for debugging
        print(f"📌 Environment: {'Cloud' if IS_CLOUD else 'Local'}")
        print(f"📌 OS: {platform.system()}")
        print(f"📌 Python: {sys.version}")
        print()
        
        # Kill any existing process on port 8080 (only aggressively if not cloud)
        print("🔍 Checking for existing Flask servers...")
        try:
            kill_process_on_port(8080, force=not IS_CLOUD)
        except Exception as e:
            print(f"⚠️  Warning: Could not clean up existing processes: {e}")
            if not IS_CLOUD:
                raise
        
        time.sleep(1)
        
        # Start Streamlit app
        print("🚀 Starting Streamlit app...")
        print("=" * 60)
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "streamlit_app.py"],
            cwd=BASE_DIR
        )
    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print(f"❌ Error: {e}")
        cleanup()
        sys.exit(1)
