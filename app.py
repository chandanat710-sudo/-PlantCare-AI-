import smtplib
import time
from email.mime.text import MIMEText 
from google import genai
from google.genai import types
import streamlit as st 


from prompts import SYSTEM_PROMPT,WELCOME_MESSAGE_TEMPLATE,SUMMARY_REQUEST_TEMPLATE

if "messages" not in st.session_state:
    st.session_state.messages = []

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GMAIL_ADDRESS = st.secrets["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]

@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key = GEMINI_API_KEY)

gemini_client = get_gemini_client()
MODEL_NAME = "gemini-3.5-flash-lite"

def render_messages(messages):
    with st.chat_message(messages["role"]):
        if messages["kind"] == "text":
            st.markdown(messages["content"])
        elif messages["kind"] == "image":
            st.image(messages["content"], width="stretch")

def add_message(role,kind, content):
    st.session_state.messages.append({"role": role, "kind": kind, "content": content})



def send_email(to_address, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = to_address

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_address, msg.as_string())
        return True, "Email sent successfully."
    except Exception as e:
        return False, str(e)


def ask_gemini(parts):
    for attempt in range(3):
        try:
            response = st.session_state.chat.send_message(parts)
            return response.text

        except Exception as error:
            if "503" in str(error) or "UNAVAILABLE" in str(error):
                if attempt < 2:
                    time.sleep(2)
                    continue

            return f"Sorry, something went wrong: {error}"

if 'onboarded' not in st.session_state:

    st.title(" 🌱PlantCare AI !")
    st.caption("Your AI-powered plant health assistant. Upload a clear photo of a plant or leaf, and I’ll help you identify possible plant diseases, pests, nutrient deficiencies, and suggest practical treatment and prevention steps.")
    with st.form("onboarding_form"):
        st.write("Please provide some information:")
        user_name = st.text_input("user_name")
        user_email = st.text_input("user_email")
        plant_type = st.selectbox("Plant Type", ["Flowering Plant", "Vegetable", "Fruit Tree", "Herb", "Other"])

        submit_button = st.form_submit_button(label="Submit")

    if submit_button:
       if not user_name.strip() or not user_email.strip():
           st.error("Please enter your name and email address.")
       else: 
          st.session_state['user_name'] = user_name
          st.session_state['user_email'] = user_email
          st.session_state['plant_type'] = plant_type     
          
          st.session_state.chat = gemini_client.chats.create(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT),
        )
          st.session_state.messages = []
          st.session_state.onboarded = True   
          st.rerun()
    st.stop()

header_col,button_col = st.columns([5,2],vertical_alignment="center")

with header_col:
    st.title(" 🌱PlantCare AI !")
    
with button_col:
    send_disabled = len(st.session_state.messages) <=1
    if st.button("send to Email",disabled=send_disabled,width="stretch"):
        with st.spinner("Summarizing the conversation for Email..."):
            summary = ask_gemini([SUMMARY_REQUEST_TEMPLATE])
            success,info = send_email(st.session_state.user_email,"Plantcare AI-Plant Health summary",summary)
            if success:
                st.success("Summary sent to Email successfully!")

            else:
                st.error(f"Failed to send summary to Email: {info}")

st.caption(
    f"Hello {st.session_state.get('user_name', 'User')}, "
    f"you are analyzing a {st.session_state.get('plant_type', 'plant')}. "
    "Upload a clear image of your plant or leaf for analysis."
)

if not st.session_state.messages:
    welcome_message= WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.get("user_name", "User"))
    add_message("assistant", "text", welcome_message)

for message in st.session_state.messages:
    render_messages(message)    

user_input = st.chat_input("Ask a question or upload an image of your plant for analysis.",
accept_file=True,
file_type=["jpg", "jpeg", "png", "bmp", "gif"]
)

if user_input:
    photo = user_input.files[0] if user_input.files else None
    text = user_input.text 
    parts = []

    if photo is not None:
        photo_bytes = photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))
    if text:
        add_message("user", "text", text)
        parts.append((text))
    elif photo is None:
        parts.append("Please analyze the uploaded plant image and provide a diagnosis, visible symptoms, and recommended actions.")


    with st.spinner("Analyzing question..."):
        answer= ask_gemini(parts)
    add_message("assistant", "text", answer)

    st.rerun()







