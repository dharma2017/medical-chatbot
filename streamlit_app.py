import streamlit as st
import streamlit.components.v1 as components
import json
import os
from dotenv import load_dotenv

# MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(page_title="Medical Assistant", layout="wide", initial_sidebar_state="collapsed")

BASE_DIR = os.path.dirname(__file__)

# Load environment variables
load_dotenv()

# Initialize embeddings and chatbot on first run
@st.cache_resource
def initialize_chatbot():
    """Initialize LangChain chatbot components"""
    try:
        from src.helper import download_hugging_face_embeddings
        from src.prompt import system_prompt
        from langchain_pinecone import PineconeVectorStore
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.runnables import RunnablePassthrough
        
        PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
        OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
        
        if not PINECONE_API_KEY or not OPENAI_API_KEY:
            st.error("❌ Missing API keys. Please set PINECONE_API_KEY and OPENAI_API_KEY in your environment.")
            return None
        
        os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
        
        embeddings = download_hugging_face_embeddings()
        index_name = "medical-chatbot"
        docsearch = PineconeVectorStore.from_existing_index(
            index_name=index_name,
            embedding=embeddings
        )
        
        retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        chatModel = ChatOpenAI(model="gpt-4o")
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])
        
        rag_chain = (
            {"context": retriever, "input": RunnablePassthrough()}
            | prompt
            | chatModel
        )
        
        return rag_chain
    except Exception as e:
        st.error(f"❌ Error initializing chatbot: {e}")
        return None

# Initialize session state for chat history
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

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

def get_chatbot_response(message, rag_chain):
    """Get response from the chatbot"""
    if rag_chain is None:
        return "Sorry, the chatbot is not available. Please check API configurations."
    
    try:
        response = rag_chain.invoke(message)
        return response.content
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    # Initialize chatbot (after set_page_config)
    rag_chain = initialize_chatbot()
    
    st.title("Medical Assistant")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📅 Book an Appointment")
        with st.form("appointment_form"):
            name = st.text_input("Full name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
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
        
        # Chat container
        chat_container = st.container()
        
        # Display chat history
        with chat_container:
            if not st.session_state.chat_history:
                with st.chat_message("assistant"):
                    st.write("Hello! I'm your medical assistant. How can I help you today?")
            
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.write(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Type your message..."):
            # Add user message to chat history
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            
            # Display user message
            with chat_container:
                with st.chat_message("user"):
                    st.write(prompt)
            
            # Get bot response
            with st.spinner("Thinking..."):
                response = get_chatbot_response(prompt, rag_chain)
            
            # Add assistant response to chat history
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
            # Display assistant response
            with chat_container:
                with st.chat_message("assistant"):
                    st.write(response)
            
            # Rerun to update the display
            st.rerun()

if __name__ == "__main__":
    main()