from flask import Flask, request, jsonify, url_for
from flask_cors import CORS, cross_origin
# import sys, traceback
import base64

# change this so it imports the license plate modules
from license_data import license_detect

app = Flask(__name__)
cors = CORS(app)

@app.route('/', methods=['POST'])
@cross_origin()
def test():
    print(url_for(request.endpoint))
    filext = request.json["extension"]
    filename = "picture.%s" % filext
    b64img = bytes(request.json["img"], 'utf-8')
    with open(filename, "wb") as fh:
        fh.write(base64.decodebytes(b64img))
    fh.close()
    # do the license plate stuff on picture
    return license_detect(filename)
