from flask import Flask
from flask_cors import CORS
from rag.api import rag_bp
from config import Config

app = Flask(__name__)
CORS(app)

@app.get("/hello")
def hello():
    return "Hello from Agentic RAG service"

# expose RAG at /ask
app.register_blueprint(rag_bp, url_prefix="/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=(Config.FLASK_ENV == "development"), use_reloader=False)
