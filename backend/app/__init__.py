from flask import Flask
from openai import OpenAI
from langchain_ollama import OllamaLLM

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    client = OpenAI(
        base_url = app.config['OLLAMA_URL'],
        api_key='ollama',
    )
    # client = OllamaLLM(
    #     model='deepseek-r1:14b',
    # )
    from .models import set_client
    set_client(client)

    from . import routes
    app.register_blueprint(routes.bp)

    return app