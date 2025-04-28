# streamlit_app.py

import streamlit as st
import time
import json
import os
from openai import OpenAI
import requests
from io import BytesIO
from PIL import Image

# Load API key securely
api_key = st.secrets["OPENAI_API_KEY"]["key"]  # or use st.text_input if you want users to enter it manually
assistant_id = "asst_Wuc1yZJpXjxRbNhgm7OFlWwK"


# Initialize OpenAI client
client = OpenAI(api_key=api_key, default_headers={"OpenAI-Beta": "assistants=v2"})


def erstelle_mood_board_und_render(user_prompt_mood_board, user_prompt_render):
    response_mood_board = client.images.generate(
        model="dall-e-3",
        prompt=user_prompt_mood_board,
        size="1792x1024",
        quality="hd",
        n=1,
    )
    response_render = client.images.generate(
        model="dall-e-3",
        prompt=user_prompt_render,
        size="1792x1024",
        quality="hd",
        n=1,
    )
    return response_mood_board.data[0].url, response_render.data[0].url


def wait_on_run(run, thread, timeout_seconds=90):
    start_time = time.time()
    while run.status in ("queued", "in_progress"):
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError("Waiting for run timed out.")
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        time.sleep(0.5)
    return run


def get_assistant_response(user_input):
    thread = client.beta.threads.create()

    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=[{"type": "text", "text": user_input}]
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
        tools=[
            {
                "type": "function",
                "function": {
                    'name': 'erstelle_mood_board_und_render',
                    'description': 'Funktion zur Erstellung von Materialkollage + Render des Innenraums! Diese Funktion MUSS ausgeführt werden!',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'user_prompt_mood_board': {
                                'type': 'string',
                                'description': 'Prompt zur Erstellung der Materialkollage.'
                            },
                            'user_prompt_render': {
                                'type': 'string',
                                'description': 'Prompt zur Erstellung des Renders des Innenraums.'
                            }
                        },
                        "required": ["user_prompt_mood_board", "user_prompt_render"]
                    }
                }
            }
        ]
    )

    run = wait_on_run(run, thread)

    assistant_text = ""

    if run.required_action:
        tool_calls = run.required_action.submit_tool_outputs.tool_calls
        print(tool_calls)
        for call in tool_calls:
            if call.function.name == "erstelle_mood_board_und_render":
                arguments = call.function.arguments
                data = json.loads(arguments)
                moodboard_url, render_url = erstelle_mood_board_und_render(
                    data['user_prompt_mood_board'],
                    data['user_prompt_render']
                )
                # moodboard_url="asdasd"
                # render_url="asfasdas"
    else:
        moodboard_url, render_url = None, None

    # Get the assistant text message
    messages = client.beta.threads.messages.list(thread_id=thread.id, order="asc", after=message.id)
    if messages.data:
        assistant_text = messages.data[0].content[0].text.value

    return assistant_text, moodboard_url, render_url


# ---- Streamlit Frontend ----












st.set_page_config(page_title="Mood Board + Interior Render Creator", page_icon="🎨", layout="wide")


# --- Password protection ---
correct_password = st.secrets["APP_PASSWORD"]["password"]

password = st.text_input("Enter password:", type="password")

if password != correct_password:
    st.error("Please enter the correct password to access the app.")
    st.stop()



st.title("🎨 Mood Board + Interior Render Creator")

user_input = st.text_input("Enter a design keyword or style:", placeholder="e.g., Scandinavian Minimalism")

if st.button("Generate"):
    if user_input:
        with st.spinner("Generating images and design idea..."):
            try:
                assistant_text, moodboard_url, render_url = get_assistant_response(user_input)
                print(moodboard_url)
                print("##################")
                print(assistant_text)
                print("##################")
                if moodboard_url and render_url:
                    st.success("Images and text generated successfully!")

                    st.subheader("📝 Assistant Response")
                    st.write(assistant_text)

                    col1, col2 = st.columns(2)

                    with col1:
                        st.header("🖼 Mood Board")
                        st.image(moodboard_url, caption="Mood Board", use_column_width=True)

                    with col2:
                        st.header("🏡 Interior Render")
                        st.image(render_url, caption="Interior Render", use_column_width=True)
                else:
                    st.error("Failed to generate images. Please try again.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        st.warning("Please enter a keyword first!")
