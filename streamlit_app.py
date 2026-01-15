import streamlit as st
import streamlit.components.v1 as components
import json
import os

BASE_DIR = os.path.dirname(__file__)


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