from flask import Flask
from openai import OpenAI
from ragflow_sdk import RAGFlow
import pvporcupine

import pvorca

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    client = OpenAI(api_key=app.config['LLM_KEY'])
    from .models import set_client
    set_client(client)

    from .models import set_session
    rag_object = RAGFlow(api_key=app.config['RAGFLOW_API_KEY'], base_url=app.config["RAGFLOW_URL"]+":9380")
    set_session(rag_object)

    from .models import set_picovoice
    porcupine = pvporcupine.create(
        access_key=app.config['PICOVOICE_ACCESS_KEY'],
        keyword_paths=None,
        keywords=["jarvis"]
    )
    set_picovoice(porcupine)

    from .models import set_orca
    orca = pvorca.create(access_key=app.config['PICOVOICE_ACCESS_KEY'])
    set_orca(orca)

    from . import routes
    app.register_blueprint(routes.bp)

    return app