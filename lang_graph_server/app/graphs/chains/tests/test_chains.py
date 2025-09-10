from dotenv import load_dotenv
load_dotenv()


from langchain.prompts import ChatPromptTemplate

# Define the chat prompt template
chat_template = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant that provides concise answers."),
    ]
)

# Format the prompt with specific values
formatted_prompt = chat_template.format_messages(country="France")