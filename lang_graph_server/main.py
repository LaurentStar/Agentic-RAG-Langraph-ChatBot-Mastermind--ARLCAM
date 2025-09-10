# from dotenv import load_dotenv; 
# load_dotenv()

# from graphs.graph import app

# if __name__ == "__main__":
#     print("Hello Advanced RAG")
#     print(app.invoke(input={"question": "agent memory?"}))




from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run() 

