#!/usr/bin/env python
"""
Wrapper script to run Streamlit app and properly manage Flask server lifecycle
"""
import subprocess
import sys
import os
import signal
import time
import atexit
import socket

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(BASE_DIR, ".flask_pid")

def is_port_in_use(port):
    """Check if port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex(('localhost', port))
        return result == 0

def kill_process_on_port(port):
    """Kill any process listening on the given port - multiple methods"""
    print(f"🔥 Attempting to kill process on port {port}...")
    
    # Method 1: Kill by PID file
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            
            if sys.platform == "win32":
                print(f"   - Killing PID {pid} using taskkill...")
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F", "/T"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
            else:
                print(f"   - Killing PID {pid} using signal...")
                os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)
        except Exception as e:
            print(f"   - PID kill failed: {e}")
    
    # Method 2: Kill by port (aggressive)
    if sys.platform == "win32":
        try:
            print(f"   - Killing process on port {port} using netstat...")
            # Get PID using netstat
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
    
    # Verify port is released
    for attempt in range(5):
        if not is_port_in_use(port):
            print(f"✓ Port {port} is now free")
            return
        time.sleep(0.5)
    
    if is_port_in_use(port):
        print(f"⚠️  Warning: Port {port} still in use after cleanup attempts")
    else:
        print(f"✓ Port {port} released successfully")

def cleanup():
    """Cleanup Flask server on exit"""
    print("\n🛑 Stopping Flask server...")
    kill_process_on_port(8080)
    
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
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, signal_handler)
except:
    pass

if __name__ == "__main__":
    try:
        # Kill any existing process on port 8080
        print("🔍 Checking for existing Flask servers...")
        kill_process_on_port(8080)
        time.sleep(1)
        
        # Start Streamlit app
        print("🚀 Starting Streamlit app...")
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "streamlit_app.py"],
            cwd=BASE_DIR
        )
    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print(f"Error: {e}")
        cleanup()
        sys.exit(1)
