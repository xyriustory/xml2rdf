from flask import Flask, request, Response
from flask_cors import CORS
from . import rdf

app = Flask(__name__)
CORS(app, supports_credentials=True)

@app.route('/', methods=["POST"])
def export_ttl():
    xml = request.form["xml"]
    ttl = rdf.xml_to_ttl(xml)
    return Response(ttl, mimetype='text/turtle')
