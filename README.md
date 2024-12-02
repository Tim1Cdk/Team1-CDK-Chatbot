# Scientia📖

Scientia is a chatbot powered by the large language model (LLM) LLama Vision Free with a strong emphasis on scientific knowledge while also supporting a broad range of other topics. Its main goal is to help users better understand and engage with concepts related to science and knowledge.

## 📌 Outlines

- Chatbot powered by a **powerful Large Language Model (LLM)**.
- Deployed on **AWS EC2** for scalability.
- Developed using **Streamlit** for a simple, intuitive UI.
- Easy-to-use, **HTTP-based access** via the web for user interactions.
- **Optimized for cloud deployment**, ensuring high performance and availability.

## 🤖 Chatbot Features

- Multiple chat room capabilities for managing different conversations simultaneously.
- Several colorful chatbot personalities to choose from, making interactions more engaging.
- Tokens per message configuration to control the length of responses.
- Adjustable temperature settings for chatbot's response creativity.
- Save conversation feature to allow users to revisit past chats.
- Multilingual support for global accessibility.

## ⚡️ How to Get Started

You can access the application through the following HTTP link:
**http://team1-alb-1351265208.ap-southeast-1.elb.amazonaws.com/**

Alternatively, you can access the application locally by following the steps below:

### 1. Clone the Repository

Start by cloning this repository to your local machine:

```bash
git clone https://github.com/Tim1Cdk/Team1-CDK-Chatbot.git
cd Team1-CDK-Chatbot.git

```

### 2. Install necessary libraries

Install the required Python libraries. You can use pip directly

```bash
pip install -r requirements.txt

```

### 3. Start the Chatbot Application

Once the libraries are installed, you can run Scientia locally using Streamlit

```bash
streamlit run main.py

```

This will launch the chatbot on your local machine. Open the displayed URL in your web browser to start interacting with the chatbot.

## 🌐 Deployment on AWS EC2

The deployment is designed for high availability, with auto scaling ensuring that the application can handle varying traffic levels. If more traffic is encountered, the EC2 instances will automatically scale up, and if the traffic decreases, it will scale down accordingly.
