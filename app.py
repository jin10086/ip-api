from __future__ import absolute_import, unicode_literals

from flask import Flask
from flask_restful import Resource, Api, reqparse
from flask_cache import Cache
from flask_pymongo import PyMongo
from flask_cors import CORS
from flask_redis import FlaskRedis
from celery import Celery

import pymongo
import logging
import json
import os


app = Flask(__name__)
CORS(app, origins=["*"])
app.config.from_pyfile("config.py")
api = Api(app)
mongo = PyMongo(app)
cache = Cache(app, config={"CACHE_TYPE": "redis"})
redis_store = FlaskRedis(app)

parser = reqparse.RequestParser()
parser.add_argument("ssinfo", location="json", required=True)


class Ip(Resource):

    def post(self):
        args = parser.parse_args()
        print(args.ssinfo)
        data = eval(args.ssinfo)
        update_squid_conf(data["ip_port"])
        # save2db(data, 'ip_port')
        return {"data": data}


def save2db(data, k):
    if isinstance(data, list):
        for i in data:
            mongo.db.ss.update_one({k: i[k]}, {"$set": i}, upsert=True)
    else:
        mongo.db.ss.update_one({k: data[k]}, {"$set": data}, upsert=True)


def update_squid_conf(ipport):
    with open("/usr/local/etc/squid.conf.example", "r") as f:
        default_conf = f.read()
    proxy = ipport.split(":")
    index = redis_store.incr("iplist")
    proxy_conf = (
        "cache_peer "
        + proxy[0]
        + " parent "
        + proxy[1]
        + " 0 no-query weighted-round-robin weight=2 connect-fail-limit=2 allow-miss max-conn=5 name=proxy-"
        + str(index)
        + "\n"
    )
    default_conf += proxy_conf
    with open("/usr/local/etc/squid.conf", "w") as f:
        f.write(default_conf)

    message = os.system("brew services restart squid")
    print(message)


api.add_resource(Ip, "/api/ss")
# api.add_resource(Feed, "/api/feed/<string:id>")


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8200, threaded=False)
