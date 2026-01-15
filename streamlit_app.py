import streamlit as st
import streamlit.components.v1 as components
import json
import os
import subprocess
import time
import sys
import atexit
import signal

BASE_DIR = os.path.dirname(__file__)
PID_FILE = os.path.join(BASE_DIR, ".flask_pid")


def kill_process_on_port(port):
    """Kill any process listening on the given port"""
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["powershell", "-Command", f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
        except:
            pass


def cleanup_flask_server():
    """Clean up Flask server process on exit"""
    # Try to kill using PID file
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F", "/T"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
            else:
                try:
                    os.kill(pid, signal.SIGTERM)
                except:
                    pass
            
            print(f"✓ Flask server (PID: {pid}) stopped")
        except Exception as e:
            print(f"Error stopping Flask server: {e}")
        finally:
            try:
                os.remove(PID_FILE)
            except:
                pass
    
    # Aggressive fallback: kill anything on port 8080
    kill_process_on_port(8080)


# Register cleanup function to run when script exits (fallback)
atexit.register(cleanup_flask_server)


@st.cache_resource
def start_flask_server():
    """Start the Flask server in the background if not already running"""
    import socket
    
    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('localhost', port))
            return result == 0
    
    # Check if server is already running
    if is_port_in_use(8080):
        st.info("ℹ️ Flask server already running on port 8080")
        return
    
    try:
        # Start Flask server as a subprocess with proper environment
        env = os.environ.copy()
        
        log_file = os.path.join(BASE_DIR, "flask_server.log")
        
        with open(log_file, "w") as log:
            process = subprocess.Popen(
                [sys.executable, os.path.join(BASE_DIR, "app.py")],
                cwd=BASE_DIR,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            )
        
        # Save PID to file for cleanup on exit
        with open(PID_FILE, "w") as f:
            f.write(str(process.pid))
        
        print(f"[Streamlit] Started Flask server with PID: {process.pid}")
        
        # Create a placeholder for status updates
        status_placeholder = st.empty()
        
        # Poll for server startup with status updates
        max_wait_time = 30  # Maximum 30 seconds to wait
        check_interval = 0.5  # Check every 0.5 seconds
        elapsed = 0
        
        while elapsed < max_wait_time:
            if is_port_in_use(8080):
                status_placeholder.success("✅ Flask server started on port 8080!")
                print(f"[Streamlit] Flask server ready after {elapsed:.1f}s")
                return
            
            # Show waiting status with elapsed time
            status_placeholder.info(f"⏳ Flask server starting... ({elapsed:.1f}s)")
            
            time.sleep(check_interval)
            elapsed += check_interval
        
        # If we get here, server didn't start in time
        try:
            with open(log_file, "r") as f:
                log_content = f.read()
            status_placeholder.error(f"⚠️ Flask server startup timeout. Logs:\n{log_content}")
        except:
            status_placeholder.error(f"⚠️ Flask server didn't start within {max_wait_time}s. Please check the logs.")
            
    except Exception as e:
        st.error(f"❌ Failed to start Flask server: {str(e)}")


def ensure_storage():
    path = os.path.join(BASE_DIR, "appointments.json")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)
    return path


def save_appointment(data):
    path = ensure_storage()
    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)
    items.append(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)


def load_appointments():
    path = ensure_storage()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_chatbot_html(api_url="http://localhost:8080/get"):
    """Load the floating chatbot HTML from chat.html with API URL parameter"""
    chat_html_path = os.path.join(BASE_DIR, "templates", "chat.html")
    with open(chat_html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    # Replace the placeholders with actual URLs
    html_content = html_content.replace('url: "%API_URL%"', f'url: "{api_url}"')
    return html_content


def main():
    
    st.set_page_config(page_title="Medical Assistant", layout="wide", initial_sidebar_state="collapsed")

    st.title("Medical Assistant")
    
    # Start Flask server on app startup
    start_flask_server()
    
    # Add JavaScript to cleanup Flask server when page closes
    st.markdown("""
    <script>
    window.addEventListener('beforeunload', function() {
        // Notify that the app is closing
        fetch('/stop_flask', {method: 'POST'}).catch(() => {});
    });
    </script>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📅 Book an Appointment")
        with st.form("appointment_form"):
            name = st.text_input("Full name", key="name")
            email = st.text_input("Email", key="email")
            phone = st.text_input("Phone", key="phone")
            date = st.date_input("Date")
            time = st.time_input("Time")
            reason = st.text_area("Reason for visit")
            submitted = st.form_submit_button("Book appointment")
            if submitted:
                if name and email and phone:
                    appt = {
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "date": date.isoformat(),
                        "time": time.isoformat(),
                        "reason": reason,
                    }
                    save_appointment(appt)
                    st.success("✅ Appointment booked successfully!")
                else:
                    st.error("Please fill in all required fields.")

        st.markdown("---")
        st.subheader("📋 Upcoming Appointments")
        items = load_appointments()
        if items:
            st.dataframe(items, use_container_width=True)
        else:
            st.info("No appointments yet.")

    with col2:
        st.header("💬 Medical Chatbot")
        st.markdown("Click the chat icon in the bottom-right corner to start chatting!")
        
        # Display some info or instructions
        # st.info("💡 **Chatbot Features:**\n\n"
        #         "- Ask about clinic hours\n"
        #         "- Get information about appointments\n"
        #         "- Emergency guidance\n"
        #         "- General health questions")
        
        # # FAQ Section
        # with st.expander("❓ Frequently Asked Questions"):
        #     st.markdown("""
        #     **Q: How do I book an appointment?**
            
        #     A: Use the appointment form on the left side. Fill in your details, select your preferred date and time, and click "Book appointment".
            
        #     ---
            
        #     **Q: What are your clinic hours?**
            
        #     A: Our clinic is open Monday-Friday, 9 AM to 5 PM. We are closed on weekends and public holidays.
            
        #     ---
            
        #     **Q: Is this a medical emergency?**
            
        #     A: If you're experiencing a medical emergency, please call 911 or visit your nearest emergency room immediately. Do not wait for online assistance.
            
        #     ---
            
        #     **Q: Can I cancel or reschedule my appointment?**
            
        #     A: Yes, you can cancel or reschedule by calling our office at least 24 hours in advance. Please contact us at (555) 123-4567.
            
        #     ---
            
        #     **Q: Do you accept insurance?**
            
        #     A: Yes, we accept most major insurance plans. Please bring your insurance card to your appointment.
        #     """)
        
        # Render the floating chatbot within the column
        api_url = "http://localhost:8080/get"  # You can make this configurable
        components.html(get_chatbot_html(api_url), height=850, scrolling=False)



if __name__ == "__main__":
    main()