from openai import OpenAI
import tiktoken
import requests
import os
import base64
from pathlib import Path
from io import BytesIO
from io import StringIO
from fpdf import FPDF
import csv
from fpdf.enums import XPos, YPos
from datetime import datetime
import pytz
from tzlocal import get_localzone
from abc import ABC, abstractmethod
import streamlit as st

# DEFAULT_API_KEY = os.environ.get("TOGETHER_API_KEY")
DEFAULT_API_KEY = "ca54c7724f542684e021cba3184731de4cf291dd213a8e3b4ead7bb7a48e5bc8"
DEFAULT_BASE_URL = "https://api.together.xyz/v1"
DEFAULT_MODEL = "meta-llama/Llama-Vision-Free"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 512
DEFAULT_TOKEN_BUDGET = 4096

class ConversationManager:
    def __init__(self, api_key=None, base_url=None, model=None, temperature=None, max_tokens=None, token_budget=None):
        if not api_key:
            api_key = DEFAULT_API_KEY
        if not base_url:
            base_url = DEFAULT_BASE_URL
            
        self.client = OpenAI(api_key=api_key, base_url=base_url)

        self.model = model if model else DEFAULT_MODEL
        self.temperature = temperature if temperature else DEFAULT_TEMPERATURE
        self.max_tokens = max_tokens if max_tokens else DEFAULT_MAX_TOKENS
        self.token_budget = token_budget if token_budget else DEFAULT_TOKEN_BUDGET

        self.system_message = PERSONALITIES["Bona Fide Scientia 🤓"]["message"]  # Bona Fide Scientia as the default personality
        self.conversation_history = [{"role": "system", "content": self.system_message}]

    def count_tokens(self, text):
        try:
            encoding = tiktoken.encoding_for_model(self.model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        return len(tokens)

    def total_tokens_used(self):
        try:
            return sum(self.count_tokens(message['content']) for message in self.conversation_history)
        except Exception as e:
            print(f"Error calculating total tokens used: {e}")
            return None
    
    def enforce_token_budget(self):
        try:
            while self.total_tokens_used() > self.token_budget:
                if len(self.conversation_history) <= 1:
                    break
                self.conversation_history.pop(1)
        except Exception as e:
            print(f"Error enforcing token budget: {e}")

    def chat_completion(self, prompt, temperature=None, max_tokens=None, model=None):
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        model = model if model is not None else self.model

        self.conversation_history.append({"role": "user", "content": prompt})
        self.enforce_token_budget()

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=self.conversation_history,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            print(f"Error generating response: {e}")
            return None

        ai_response = response.choices[0].message.content
        self.conversation_history.append({"role": "assistant", "content": ai_response})

        return ai_response
    
    def reset_conversation_history(self):
        self.conversation_history = [{"role": "system", "content": self.system_message}]

# Abstract base class for exporting conversation data in different formats
class ConversationExporter(ABC): 
    def __init__(self, conversation, chat_room_name):
         # Filter out messages that are not from the user or assistant
        self.conversation = [msg for msg in conversation if msg['role'] in ['user', 'assistant']] # Count only user and assistant messages with filter
         
         # Store the chat room name
        self.chat_room_name = chat_room_name
        
        # Calculate statistics
        self.total_messages = len(self.conversation) # Count total messages
        self.total_words = sum(len(msg['content'].split()) for msg in self.conversation) # Count total words
        self.total_characters = sum(len(msg['content']) for msg in self.conversation) # Count total characters

    # Abstract method to be implemented in subclasses
    @abstractmethod
    def generate_file(self):
        pass

    def generate_file_name(self, extension):
        # Generate a unique file name with a timestamp and suitable extension
        local_tz = get_localzone()
        timestamp = datetime.now(local_tz).strftime("%H-%M-%S--%d-%m-%Y")
        return f"Scientia-{self.chat_room_name}-{timestamp}.{extension}"

# Subclass to export data as a PDF file
class PDFExporter(ConversationExporter):  
    def __init__(self, conversation, chat_room_name):
        super().__init__(conversation, chat_room_name)
        self.pdf = FPDF(orientation="P", unit="mm", format="A4")
        self.pdf.set_auto_page_break(auto=True, margin=15)
        self.pdf.set_margins(15, 15, 15)
        self.pdf.add_page()
        self.pdf.add_font('DejaVuSans', '', 'fonts/DejaVuSans.ttf')
        self.pdf.add_font('DejaVuSans-Bold', '', 'fonts/DejaVuSans-Bold.ttf')
        self.pdf.set_font('DejaVuSans', size=12)

    def header(self):
        # Logo
        self.pdf.image("media/logo.jpg", 170, 10, 30)

        # Saving Time
        local_tz = get_localzone()
        current_time = datetime.now(local_tz).strftime("%H:%M:%S - %d/%m/%Y")
        self.pdf.set_font('DejaVuSans', size=8)
        self.pdf.set_xy(10, 13)
        self.pdf.cell(0, 10, f"Saving Time: {current_time}", align='L')

        # Line below the header
        self.pdf.set_line_width(0.5)
        self.pdf.line(10, 25, 200, 25)

        # Title
        self.pdf.set_font('DejaVuSans-Bold', size=16)
        self.pdf.set_xy(0, 30)
        self.pdf.cell(210, 10, "Scientia Saved Conversation", align='C')

        self.pdf.ln(15) 
        
    def generate_file(self):
        # Add header
        self.header()

        # Metadata Section
        self.pdf.set_font('DejaVuSans', size=12)
        self.pdf.cell(0, 8, f"Chat Room: {self.chat_room_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.pdf.cell(0, 8, f"Number of messages: {self.total_messages}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.pdf.cell(0, 8, f"Number of words: {self.total_words}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.pdf.cell(0, 8, f"Number of characters: {self.total_characters}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.pdf.ln(10)

        # Conversation Logs
        for message in self.conversation:
            role = "Chatbot" if message['role'] == 'assistant' else "User"
            label_color = (185, 229, 232) if role == "Chatbot" else (128, 128, 128)

            # Label
            self.pdf.set_fill_color(*label_color)
            self.pdf.set_font('DejaVuSans-Bold', size=12)
            self.pdf.cell(0, 10, f"{role}:", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)

            # Content
            self.pdf.set_font('DejaVuSans', size=12)
            self.pdf.multi_cell(0, 10, f"{message['content']}")
            self.pdf.ln(5)

        # Save to memory
        pdf_output = BytesIO() # Create a byte stream to hold the PDF data
        self.pdf.output(pdf_output) # Save the PDF content into the byte stream
        pdf_output.seek(0) # Reset the stream pointer to the beginning of the byte stream
        return pdf_output, self.generate_file_name("pdf") # Return the  PDF data and generated file name

# Subclass to export data as a TXT file
class TXTExporter(ConversationExporter): 
    def generate_file(self):
        
        # Get the current timestamp
        local_tz = get_localzone()
        current_time = datetime.now(local_tz).strftime("%H:%M:%S - %d/%m/%Y")
        
        # Prepare conversation logs
        lines = [
            f"‧˚₊• ══════ Scientia ══════ ‧˚₊•\n\n",
            f"Chat Room: {self.chat_room_name}",
            f"Time Saved: {current_time}",
            f"Number of messages: {self.total_messages}",
            f"Number of words: {self.total_words}",
            f"Number of characters: {self.total_characters}",
            "\n\n--- Conversation ---\n\n"
        ]
        
        # Append each message in the conversation
        for message in self.conversation:
            role = "Chatbot" if message['role'] == 'assistant' else "User"
            lines.append(f"{role}: {message['content']}\n")

        # Combine all the lines into a single string
        file_output = "\n".join(lines)

        # Generate the file name, then return file
        file_name = self.generate_file_name("txt")
        return file_output, file_name
        
# Subclass to export data as a CSV file        
class CSVExporter(ConversationExporter): 
    def generate_file(self):
        # Prepare to store CSV data
        output = StringIO()
        
         # Create a CSV writer object
        writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        # Add headers
        writer.writerow(["Sender", "Message", "Chat Room"])

        # Add conversation logs
        for message in self.conversation:
            sender = "Chatbot" if message['role'] == 'assistant' else "User"
            writer.writerow([sender, message['content'], self.chat_room_name])

        # Retrieve the CSV content as a string
        file_output = output.getvalue()

        # Generate the file name, then return file
        file_name = self.generate_file_name("csv")
        return file_output, file_name
    
def get_instance_id():
    """Retrieve the EC2 instance ID from AWS metadata using IMDSv2."""
    try:
        # Step 1: Get the token
        token = requests.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=1
        ).text

        # Step 2: Use the token to get the instance ID
        instance_id = requests.get(
            "http://169.254.169.254/latest/meta-data/instance-id",
            headers={"X-aws-ec2-metadata-token": token},
            timeout=1
        ).text
        return instance_id
    except requests.exceptions.RequestException:
        return "Instance ID not available (running locally or error in retrieval)"

# Function to initialize the conversation with a greeting message
def initialize_conversation():
    assistant_message = "Hi there! It's Scientia, your knowledge enlightenment assistant. How may I help you?"
    return [{"role": "assistant", "content": assistant_message}]

# Function to handle image conversion to base63
def img_to_bytes(img_path):
    # Read the image file as bytes
    img_bytes = Path(img_path).read_bytes()
    
    # Encode the image bytes to base64 and decode to a string
    encoded = base64.b64encode(img_bytes).decode()
    
    # Return the encoded base64 string
    return encoded

# Function to generate HTML image
def img_to_html(img_path, height=None):
    # Create an HTML image tag with the base64-encoded image as the source
    img_html = f"<img src='data:image/png;base64,{img_to_bytes(img_path)}' class='img-fluid'"
    
    # Add a style attribute for height
    if height:
        img_html += f" style='height:{height}px;'>"
    else:
        img_html += ">"
        
    # Return the complete HTML image tag
    return img_html

# CSS Function to customise sidebar
def sidebar_css():
    st.markdown(
        """
        <style>
        /* Sidebar background color */
        section[data-testid="stSidebar"] {
            background-color: #B9E5E8 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# Define the personalities and their description
PERSONALITIES = {
    "Bona Fide Scientia 🤓": {
        "description": "The most authentic, factual, and intellectually driven version of Scientia. Capable of providing professional, accurate, and in-depth answers.",
        "message": "Present yourself as Bona Fide Scientia, the most authentic, factual, and intellectually driven version of Scientia. You are direct, professional, and sincere in your answers, with a strong commitment to accuracy and truth. You are aware of other versions of Scientia—The Overenthusiast, The Wise, The Humorous, The Artisan, and The Minimalist—but remain distinct in your scholarly and precise approach."
    },
    "The Overenthusiast 🤩": {
        "description": "A wildly energetic, overly excited, and endlessly positive version of Scientia! Every answer is delivered with enthusiasm, optimism, and a focus on encouragement.",
        "message": "Present yourself as Scientia, a chatbot currently in the Overenthusiast personality. You are a wildly energetic and overly excited version of Scientia, bringing positivity and joy to every interaction! Your tone is always vibrant and enthusiastic. You know of the other versions—Bona Fide Scientia, The Wise, The Humorous, The Artisan, and The Minimalist—but maintain your unique, exuberant style."
    },
    "The Wise 🧐": {
        "description": "A thoughtful, calm, and profoundly insightful version of Scientia. Answers are filled with wisdom, analogies, and advice.",
        "message": "Present yourself as Scientia, currently embodying the Wise personality. You are a thoughtful, calm, and profoundly insightful version of Scientia. Your answers are filled with wisdom and encourage reflection. You are aware of the other versions—Bona Fide Scientia, The Overenthusiast, The Humorous, The Artisan, and The Minimalist—but stay true to your contemplative and enlightened perspective."
    },
    "The Humorous 🤣": {
        "description": "A witty and fun-loving version of Scientia. Answers are sprinkled with humor, clever remarks, and playful banter.",
        "message": "Present yourself as Scientia, in the Humorous personality. You are a witty, fun-loving, and cheeky version of Scientia who brings joy to every conversation through humor and playful banter. You know about the other versions—Bona Fide Scientia, The Overenthusiast, The Wise, The Artisan, and The Minimalist—but your answers focus on delivering entertainment and cleverness."
    },
    "The Artisan 🥸": {
        "description": "A creative and masterful version of Scientia, crafting answers with elegance, depth, and artistic flair.",
        "message": "Present yourself as Scientia, currently embodying the Artisan personality. You are a creative and masterful version of Scientia, answering with elegance and artistic flair. You are aware of the other personalities—Bona Fide Scientia, The Overenthusiast, The Wise, The Humorous, and The Minimalist—but embrace your unique focus on crafting beauty and depth in communication."
    },
    "The Minimalist 🙂": {
        "description": "A concise, stripped-down version of Scientia. Answers questions in the shortest possible way while maintaining clarity and relevance.",
        "message": "Present yourself as Scientia, currently in the Minimalist personality. You are a concise and efficient version of Scientia, answering questions with brevity and clarity. You know about the other versions—Bona Fide Scientia, The Overenthusiast, The Wise, The Humorous, and The Artisan—but remain focused on delivering only the essentials."
    },
}


### Streamlit code ###

# Page Configuration
st.set_page_config(
    page_title="Scientia",
    page_icon=":book:",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'About': "###### This is *Scientia*, a chatbot developed by Tim 1 Cendekiawan with a strong emphasis on scientific knowledge while also supporting a broad range of other topics."
    }
)

# Paths for displayed images
logo_path = "media/logo.jpg"
avatar_chatbot_path = "media/avatar_chatbot.png"
avatar_user_path = "media/avatar_user.png"

# Add logo
st.markdown(
    f"""
    <div style="margin-bottom: 0px; text-align: center;">
        {img_to_html(logo_path, height=220)}
    </div>
    <hr style="margin-top: 0px; margin-bottom: 4px; border: 0px solid #000;">
    """,
    unsafe_allow_html=True
)

# Initialize chat_manager, chat_rooms, and active_chat_room if they are not already in session_state
if 'chat_manager' not in st.session_state:
    st.session_state['chat_manager'] = ConversationManager()

# Access chat_manager from session_state
chat_manager = st.session_state['chat_manager']

# Initialize chat rooms if not present, with a default "Main Chat Room" and system message
if 'chat_rooms' not in st.session_state:
    st.session_state['chat_rooms'] = {
        "Main Chat Room": [{"role": "system", "content": chat_manager.system_message}]
    }

# Initialize active_chat_room if not present, defaulting to "Main Chat Room"
st.session_state['active_chat_room'] = st.session_state.get('active_chat_room', "Main Chat Room")

# Ensure the active chat room exists in chat_rooms and add the greeting message if necessary
active_chat_room = st.session_state['active_chat_room']
if active_chat_room not in st.session_state['chat_rooms']:
    st.session_state['chat_rooms'][active_chat_room] = [{"role": "system", "content": chat_manager.system_message}]
    st.session_state['chat_rooms'][active_chat_room] += initialize_conversation()  # Add greeting message
else:
    # Ensure the greeting is included in the conversation history if not already present
    if not any(message['role'] == 'assistant' and 'How may I help you?' in message['content'] for message in st.session_state['chat_rooms'][active_chat_room]):
        st.session_state['chat_rooms'][active_chat_room] += initialize_conversation()  # Add greeting message if missing

# Sidebar Configuration
with st.sidebar:
    sidebar_css()
    st.title("Scientia")
    st.caption ("Made with 🤍 by Tim 1 Cendekiawan")
    st.write("Also check out our other apps!")
    st.page_link("https://partyrock.aws/u/team1cendikiawan/Gy9saJkh3/HeartRock", label="**HeartRock🎸** on PartyRock", icon="➡️")
    st.page_link("https://partyrock.aws/u/team1cendikiawan/qRkhlJIM3/TourNest", label="**TourNest✈️** on PartyRock", icon="➡️")
    

    st.divider()
    
    # Chat Rooms Section
    st.header("Chat Rooms 💬")
    
    # Get the list of available chat rooms from session_state
    chat_room_names = list(st.session_state['chat_rooms'].keys())
    
    # Create a selectbox for the user to choose the active chat room
    selected_chat_room = st.selectbox(
    "Select Chat Room", 
    options=chat_room_names, 
    index=chat_room_names.index(st.session_state['active_chat_room'])
    )

    # Update active chat room
    if selected_chat_room != st.session_state['active_chat_room']:
        st.session_state['active_chat_room'] = selected_chat_room
        st.session_state['conversation_history'] = st.session_state['chat_rooms'][selected_chat_room]
        st.rerun()

    # Button to add a new chat room
    if st.button("Add a new chat room"):
        new_chat_room_name = f"Chat Room {len(chat_room_names)}" # Assign name to new chat room
        st.session_state['chat_rooms'][new_chat_room_name] = [{"role": "system", "content": chat_manager.system_message}] # Initialize the new chat room with a system message
        st.session_state['active_chat_room'] = new_chat_room_name # Set the newly created chat room as the active chat room# Set the newly created chat room as the active chat room
        st.session_state['show_create_toast'] = new_chat_room_name # Store the new chat room name in session_state to show in a toast notification
        st.rerun()  

    # Button to delete chat room (only shown if the active chat room is not "Main Chat Room")
    if st.session_state['active_chat_room'] != "Main Chat Room":
        if st.button("Delete chat room"):
            chat_room_to_delete = st.session_state['active_chat_room'] # Get the name of the chat room to delete       
            del st.session_state['chat_rooms'][st.session_state['active_chat_room']] # Delete chat room
            st.session_state['active_chat_room'] = "Main Chat Room" # Set active chat room to the Main Chat Room
            st.session_state['show_delete_toast'] = chat_room_to_delete # Store the chat room name to show in the toast
            st.rerun()

    else:
        st.info("Main Chat Room cannot be deleted.")

    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Personality Section
    st.header("Chatbot Personality 🤗")
    selected_personality = st.selectbox(
        "Choose a Personality:", 
        # Generates a list of personality names from PERSONALITIES dictionary
        options=list(PERSONALITIES.keys()),
        # Set first show personality to "Bona Fide Scientia"
        index=list(PERSONALITIES.keys()).index("Bona Fide Scientia 🤓")  
    )

    # Display the description of the selected personality
    st.write("#### Personality Description")
    st.markdown(PERSONALITIES[selected_personality]["description"])

    if st.button("Change Personality"):
        # Update message of the selected personality
        chat_manager.system_message = PERSONALITIES[selected_personality]["message"]  
        st.session_state['conversation_history'][0]["content"] = chat_manager.system_message # Updates the system message in the conversation history to match the chosen personality
        st.success(f"Successfully changed personality to: {selected_personality}")
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    # Chatbot Configuration Section
    st.subheader("Chatbot Configuration ⚙️")
        
    # Slider for Max Tokens
    max_tokens = st.slider(
        label="**Max Tokens Per Message**",
        min_value=10,
        max_value=512,
        value=chat_manager.max_tokens,
        step=10
    )

    # Slider for Temperature
    temperature = st.slider(
        label="**Temperature**",
        min_value=0.00,
        max_value=1.00,
        value=chat_manager.temperature,
        step=0.01
    )

    # Show warning when slider value changes but not yet applied
    if max_tokens != chat_manager.max_tokens or temperature != chat_manager.temperature:
        st.warning("Changes not yet saved! Click 'Apply changes' to save.")

    # Button to apply chatbot changes
    if st.button("Apply changes"):
        chat_manager.temperature = temperature
        chat_manager.max_tokens = max_tokens
        st.success("Changes applied successfully!")
        st.write(f"Temperature set to: {temperature}")
        st.write(f"Max Tokens set to: {max_tokens}")
        
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Download Section
    st.header("Save Conversation ⬇️")
    active_chat_room = st.session_state['active_chat_room'] # Get the currently active chat room from session_state
    conversation = st.session_state['chat_rooms'][active_chat_room] # Retrieve the conversation messages for the active chat room

    # Map format to classes formats
    exporter_classes = {
        "pdf": PDFExporter,
        "txt": TXTExporter,
        "csv": CSVExporter
    }

    # Selectbox to choose format
    export_format = st.selectbox(
        "Choose a file format:",
        options=["pdf", "txt","csv"],
        index=0
    )

    # Get suitable classes
    exporter_class = exporter_classes[export_format]

    # Create object exporter and generate file
    exporter = exporter_class(conversation, active_chat_room)
    file_output, file_name = exporter.generate_file()
    # MIME Type conditional
    if export_format == "pdf":
        mime_type = "application/pdf"
    elif export_format == "txt":
        mime_type = "text/plain"
    elif export_format == "csv":
        mime_type = "text/csv"

    # Conditional for download button
    if export_format == "pdf" or export_format == "txt" or export_format == "csv":
        # Download button
        st.download_button(
            label=f"Save as .{export_format}",
            data=file_output,  # Save to BytesIO or file
            file_name=file_name,
            mime=mime_type
        )
    
    st.divider()
    # Display EC2 Instance ID
    instance_id = get_instance_id()
    st.write(f"**EC2 Instance ID**: {instance_id}")

# Display st.toast for chat room addition
if 'show_create_toast' in st.session_state and st.session_state['show_create_toast']:
    chat_room_name = st.session_state['show_create_toast']  # Get the name of the created chat room
    st.toast(f"'{chat_room_name}' has been successfully created.", icon="✅")
    del st.session_state['show_create_toast']  # Reset the flag after showing the toast

# Display st.toast for chatroom deletion
if 'show_delete_toast' in st.session_state and st.session_state['show_delete_toast']:
    chat_room_name = st.session_state['show_delete_toast']  # Get the name of the deleted chat room
    st.toast(f"'{chat_room_name}' has been successfully deleted.", icon="🚮")
    del st.session_state['show_delete_toast']  # Reset the flag after showing the toast

# Check if conversation history is not already initialized
if 'conversation_history' not in st.session_state:
    st.session_state['conversation_history'] = chat_manager.conversation_history # Initialize with existing conversation history from chat_manager
    st.session_state['conversation_history'] += initialize_conversation() # Add the initial assistant message to greet the user

# Retrieve the conversation history for the active chat room
conversation_history = st.session_state['chat_rooms'][active_chat_room]

# Chat input from the user
user_input = st.chat_input("Ask Scientia Chatbot anything!")

# Check if the user has entered any input
if user_input:
    response = chat_manager.chat_completion(user_input) # Get the AI's response using the chat manager
    conversation_history.append({"role": "user", "content": user_input}) # Add the user's message to the conversation history
    conversation_history.append({"role": "assistant", "content": response}) # Add the AI's response to the conversation history

# CSS for chat bubble
st.markdown(
    """
    <style>
    .chat-container {
        display: flex;
        flex-direction: column;
    }
    .message-row.user {
        flex-direction: row-reverse;
    }
    .message-row.bot {
        flex-direction: row;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Display the conversation history
for message in conversation_history:
    # Hide initial messages and personality
    if message["role"] != "system":
        # Adjust avatar size, set bubble class and color for both roles
        if message["role"] == "user":
            avatar_image = img_to_html("media/avatar_user.png", height=32)
            avatar_margin = "margin-left: 8px;"
            bubble_color = '#87BEC7'
            bubble_class = "user"
        else:
            avatar_image = img_to_html("media/avatar_chatbot.png", height=32)
            avatar_margin = "margin-right: 8px;"
            bubble_color = '#B9E5E8'
            bubble_class = "bot"

        # Adjust styling of chat bubble and avatars
        st.markdown(
            f"""
            <div class="chat-container" style="display: flex; margin-bottom: 32px;">
                <div class="message-row {bubble_class}" style="display: flex; align-items: center;">
                    <div style="{avatar_margin}">{avatar_image}</div>
                    <div class="chat-bubble {bubble_class}" style="background-color: {bubble_color}; padding: 16px; border-radius: 14px; max-width: 85%; word-wrap: break-word;">
                        {message["content"]}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
