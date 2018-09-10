from flask import Flask, request, Response
import os
import requests
import logging
import json
import dotdictify
import urllib
from time import sleep
import ast



app = Flask(__name__)
logger = None
format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger('o365graph-service')

# Log to stdout
stdout_handler = logging.StreamHandler()
stdout_handler.setFormatter(logging.Formatter(format_string))
logger.addHandler(stdout_handler)
logger.setLevel(logging.DEBUG)

##getting token from oauth2
def get_token():
    logger.info("Creating header")
    headers= {}
    payload = {
        "client_id":os.environ.get('client_id'),
        "client_secret":os.environ.get('client_secret'),
        "grant_type": os.environ.get('grant_type'),
        "resource": os.environ.get('resource')
    }
    resp = requests.post(url=os.environ.get('token_url'), data=payload, headers=headers).json()
    token = dotdictify.dotdictify(resp).access_token
    logger.info("Received access token from " + os.environ.get('token_url'))
    return token

class DataAccess:
#main get function, will probably run most via path:path
    def __get_all_paged_entities(self, path):
        logger.info("Fetching data from paged url: %s", path)
        url = os.environ.get("base_url") + path
        access_token = get_token()
        next_page = url
        page_counter = 1
        while next_page is not None:
            if os.environ.get('sleep') is not None:
                logger.info("sleeping for %s milliseconds", os.environ.get('sleep') )
                sleep(float(os.environ.get('sleep')))

            logger.info("Fetching data from url: %s", next_page)
            req = requests.get(next_page, headers={"Authorization": "Bearer " + access_token})
            if req.status_code != 200:
                logger.error("Unexpected response status code: %d with response text %s" % (req.status_code, req.text))
                raise AssertionError ("Unexpected response status code: %d with response text %s"%(req.status_code, req.text))
            res = dotdictify.dotdictify(json.loads(req.text))
            for entity in res.get(os.environ.get("entities_path")):

                yield(entity)

            if res.get(os.environ.get('next_page')) is not None:
                page_counter+=1
                next_page = res.get(os.environ.get('next_page'))
            else:
                next_page = None
        logger.info('Returning entities from %i pages', page_counter)

    def get_paged_entities(self,path):
        print("getting all paged")
        return self.__get_all_paged_entities(path)

    def get_paged_owners(self, path):
        print("getting all paged")
        return self.__get_all_paged_entities(path)

    def get_paged_groups(self, path):
        print("getting all paged")
        return self.__get_all_paged_entities(path)

data_access_layer = DataAccess()


def stream_json(clean):
    first = True
    yield '['
    for i, row in enumerate(clean):
        if not first:
            yield ','
        else:
            first = False
        yield json.dumps(row)
    yield ']'

@app.route("/owners", methods=["GET"])
def get_owners():
    if request.method == "GET":
        path = os.environ.get('groups-owners-odata')
        entities = data_access_layer.get_paged_owners(path)

    return Response(
        stream_json(entities),
        mimetype='application/json'
    )


@app.route("/groups", methods=["GET"])
def get_groups():
    if request.method == "GET":
        path = os.environ.get('groups-odata')
        entities = data_access_layer.get_paged_groups(path)

    return Response(
        stream_json(entities),
        mimetype='application/json'
    )
@app.route("/<path:path>", methods=["GET", "POST"])
def get(path):
    if request.method == "POST":
        path = request.get_json()

    if request.method == "GET":
        path = path

    entities = data_access_layer.get_paged_entities(path)

    return Response(
        stream_json(entities),
        mimetype='application/json'
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', threaded=True, port=os.environ.get('port',5000))
