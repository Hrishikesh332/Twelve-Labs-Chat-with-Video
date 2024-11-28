import streamlit as st
from twelvelabs import TwelveLabs
from twelvelabs.models.task import Task
import uuid
import os
from dotenv import load_dotenv


load_dotenv()

st.sidebar.title("Video Upload")

# API Key for TwelveLabs
API_KEY = os.getenv("API_KEY")
client = TwelveLabs(api_key=API_KEY)

index_name = f"Example_{uuid.uuid4().hex[:8]}"
st.sidebar.write(f"Generated Index Name: {index_name}")

uploaded_file = st.sidebar.file_uploader("Upload a Video", type=["mp4", "mov", "avi", "mkv"])

# Main page title
st.title("Twelve Labs Video Chat")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Please upload and index a video first."}]
if "task_ready" not in st.session_state:
    st.session_state.task_ready = False
if "task_video_id" not in st.session_state:
    st.session_state.task_video_id = None

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if uploaded_file:
    st.sidebar.success(f"Uploaded file: {uploaded_file.name}")
    
    if st.sidebar.button("Index Video"):
        with st.spinner("Processing video..."):
            # Create index
            engines = [
                {"name": "pegasus1.1", "options": ["visual", "conversation"]},
                {"name": "marengo2.6", "options": ["visual", "conversation", "text_in_video", "logo"]},
            ]
            index = client.index.create(name=index_name, engines=engines, addons=["thumbnail"])
            st.sidebar.write(f"Index Created: {index.name}")

            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Process the video
            task = client.task.create(index_id=index.id, file=uploaded_file.name)

            def on_task_update(task: Task):
                st.sidebar.write(f"Current Task Status: {task.status}")

            task.wait_for_done(sleep_interval=5, callback=on_task_update)

            if task.status == "ready":
                st.session_state.task_ready = True
                st.session_state.task_video_id = task.video_id
                st.sidebar.success(f"Task Completed! Video ID: {task.video_id}")

                st.session_state.messages = [
                    {"role": "assistant", "content": "Video indexing is complete! You can now ask questions about the video."}
                ]
            else:
                st.sidebar.error(f"Task failed with status: {task.status}")

if st.session_state.task_ready:
    if prompt := st.chat_input("Ask a question about the video..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            try:
                response = client.generate.text(
                    video_id=st.session_state.task_video_id,
                    prompt=prompt
                )
                video_response = response.data
                
                # Display and store the response
                st.markdown(video_response)
                st.session_state.messages.append({"role": "assistant", "content": video_response})
            
            except Exception as e:
                error_message = f"Error generating response: {str(e)}"
                st.markdown(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})
