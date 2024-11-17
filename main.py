from openai import OpenAI
import tiktoken
import requests
import os
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

        self.system_message = "Present yourself as Scientia, a chatbot that is friendly and supportive. You answer questions with kindness, encouragement, and patience, always looking to help the user feel comfortable and confident."  # Default persona
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

### Streamlit code ###
st.title("Scientia")
st.markdown("<hr>", unsafe_allow_html=True)

# Initialize the ConversationManager object
if 'chat_manager' not in st.session_state:
    st.session_state['chat_manager'] = ConversationManager()

chat_manager = st.session_state['chat_manager']

# Sidebar Configuration
with st.sidebar:
    # LOGO_URL = "media/logo.jpg"
    # st.image(LOGO_URL, use_container_width=True) 
    st.header("Chatbot Configuration")
    st.markdown("<br>", unsafe_allow_html=True)

    # Slider for Max Tokens
    max_tokens = st.slider(
        label="**Max Tokens Per Message**",
        min_value=10,
        max_value=500,
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
        
    st.markdown("<hr>", unsafe_allow_html=True)
    # Display EC2 Instance ID
    instance_id = get_instance_id()
    st.write(f"**EC2 Instance ID**: {instance_id}")

# Initialize conversation history with a greeting message from the assistant
if 'conversation_history' not in st.session_state:
    st.session_state['conversation_history'] = chat_manager.conversation_history
    # Add the initial assistant message to greet the user
    st.session_state['conversation_history'] += initialize_conversation()

conversation_history = st.session_state['conversation_history']

# Chat input from the user
user_input = st.chat_input("Ask Scientia Chatbot anything!")

# Call the chat manager to get a response from the AI
if user_input:
    response = chat_manager.chat_completion(user_input)

# Display the conversation history
for message in conversation_history:
    if message["role"] != "system":
        # Set avatar image based on role
        avatar_image = "media/avatar_user.png" if message["role"] == "assistant" else "media/avatar_chatbot.png"
        # Display message with avatar
        with st.chat_message(message["role"], avatar=avatar_image):
            st.write(message["content"])