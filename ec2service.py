#!/usr/bin/python3

__author__ = 'ebianchi'

import bottle
import json

@bottle.route("/")
def hello():
    return "Hello World!"

@bottle.route("/machines/", method="GET")
def machine_list():
    return json.dumps({"result": "ko", "message": "Not implemented"})

@bottle.route("/machines/<name>", method="GET")
def machine_show(name):
    return json.dumps({"result": "ko", "message": "List for machine " + name + " not implemented"})

@bottle.route("/machines/<name>/start", method="GET")
def machine_command(name):
    return json.dumps({"result": "ko", "message": "Start command for machine " + name + " not implemented"})

@bottle.route("/machines/<name>/stop", method="GET")
def machine_command(name):
    return json.dumps({"result": "ko", "message": "Stop command for machine " + name + " not implemented"})

if __name__ == "__main__":
    bottle.run(host='localhost', port=8080, debug=False)
