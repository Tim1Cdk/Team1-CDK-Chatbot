import logging
from openai import OpenAI
import tiktoken
import requests
import os
import streamlit as st
import subprocess
import sys
from dotenv import load_dotenv

# Initialize environment variables and logging
load_dotenv()
logging.basicConfig(level=logging.DEBUG)  # Set logging level to DEBUG

DEFAULT_API_KEY = os.getenv("TOGETHER_API_KEY")
DEFAULT_BASE_URL = os.getenv("BASE_URL")
DEFAULT_MODEL = os.getenv("MODEL")
DEFAULT_TEMPERATURE = float(os.getenv("TEMPERATURE"))
DEFAULT_MAX_TOKENS = int(os.getenv("MAX_TOKENS"))
DEFAULT_TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET"))
EC2_METADATA_URL = os.getenv("EC2_METADATA_URL")
TOKEN_TTL_SECONDS = os.getenv("TOKEN_TTL_SECONDS")
print("TOGETHER_API_KEY:", os.getenv("TOGETHER_API_KEY"))
print("BASE_URL:", os.getenv("BASE_URL"))
print("MODEL:", os.getenv("MODEL"))
print("TEMPERATURE:", float(os.getenv("TEMPERATURE")))
print("MAX_TOKENS:", int(os.getenv("MAX_TOKENS")))
print("TOKEN_BUDGET:", int(os.getenv("TOKEN_BUDGET")))
print("EC2_METADATA_URL:", os.getenv("EC2_METADATA_URL"))
print("TOKEN_TTL_SECONDS:", os.getenv("TOKEN_TTL_SECONDS"))

class ConversationManager:
    def __init__(self, api_key=None, base_url=None, model=None, temperature=None, max_tokens=None, token_budget=None):
        logging.debug("Initializing ConversationManager with default values or environment values.")
        self.api_key = api_key if api_key else DEFAULT_API_KEY
        self.base_url = base_url if base_url else DEFAULT_BASE_URL
        self.model = model if model else DEFAULT_MODEL
        self.temperature = temperature if temperature else DEFAULT_TEMPERATURE
        self.max_tokens = max_tokens if max_tokens else DEFAULT_MAX_TOKENS
        self.token_budget = token_budget if token_budget else DEFAULT_TOKEN_BUDGET

        logging.debug(f"API Key: {self.api_key}, Base URL: {self.base_url}, Model: {self.model}")
        
        # Initialize OpenAI client with error handling
        try:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            logging.info("OpenAI client initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize OpenAI client: {e}")
        
        self.system_message = "You are a friendly and supportive guide."
        self.conversation_history = [{"role": "system", "content": self.system_message}]

    def count_tokens(self, text):
        try:
            encoding = tiktoken.encoding_for_model(self.model)
            tokens = encoding.encode(text)
            logging.debug(f"Counting tokens for text: '{text}' - Token count: {len(tokens)}")
            return len(tokens)
        except Exception as e:
            logging.error(f"Error counting tokens: {e}")
            return 0

    def total_tokens_used(self):
        try:
            total = sum(self.count_tokens(message['content']) for message in self.conversation_history)
            logging.debug(f"Total tokens used: {total}")
            return total
        except Exception as e:
            logging.error(f"Error calculating total tokens used: {e}")
            return None
    
    def enforce_token_budget(self):
        try:
            logging.debug("Enforcing token budget...")
            while self.total_tokens_used() > self.token_budget:
                if len(self.conversation_history) <= 1:
                    break
                self.conversation_history.pop(1)
            logging.debug("Token budget enforcement complete.")
        except Exception as e:
            logging.error(f"Error enforcing token budget: {e}")

    def chat_completion(self, prompt, temperature=None, max_tokens=None, model=None):
        logging.info(f"Received prompt: {prompt}")
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
            ai_response = response.choices[0].message.content
            logging.debug(f"AI response: {ai_response}")
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            return ai_response
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return None
    
    def reset_conversation_history(self):
        logging.debug("Resetting conversation history.")
        self.conversation_history = [{"role": "system", "content": self.system_message}]

def get_instance_id():
    """Retrieve the EC2 instance ID from AWS metadata using IMDSv2, configurable via environment variables."""
    try:
        # Step 1: Get the token
        token = requests.put(
            f"{EC2_METADATA_URL}/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": TOKEN_TTL_SECONDS},
            timeout=1
        ).text
        logging.debug(f"Retrieved token: {token}")

        # Step 2: Use the token to get the instance ID
        instance_id = requests.get(
            f"{EC2_METADATA_URL}/meta-data/instance-id",
            headers={"X-aws-ec2-metadata-token": token},
            timeout=1
        ).text
        logging.info(f"Retrieved EC2 Instance ID: {instance_id}")
        return instance_id

    except requests.exceptions.RequestException as e:
        logging.warning(f"Failed to retrieve EC2 Instance ID: {e}")
        return "Instance ID not available (running locally or error in retrieval)"

### Streamlit code ###
st.title("AI Chatbot with Debugging")
# run without streamlit run main.py remove '#'
# subprocess.run([sys.executable, "-m", "streamlit", "run", "main.py"])

# Display EC2 Instance ID
instance_id = get_instance_id()
st.write(f"**EC2 Instance ID**: {instance_id}")

# Initialize the ConversationManager object
if 'chat_manager' not in st.session_state:
    st.session_state['chat_manager'] = ConversationManager()

chat_manager = st.session_state['chat_manager']

# Chat input from the user
user_input = st.chat_input("Write a message")
logging.info(f"User input: {user_input}")

# Call the chat manager to get a response from the AI
if user_input:
    response = chat_manager.chat_completion(user_input)
    logging.debug(f"Response generated: {response}")
    st.write(response) if response else st.write("Error generating response.")

# Display the conversation history
for message in chat_manager.conversation_history:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.write(message["content"])
