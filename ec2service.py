#!/usr/bin/python3

__author__ = 'ebianchi'

from bottle import route, run

@route('/')
def hello():
    return "Hello World!"

if __name__ == "__main__":
    run(host='localhost', port=8080, debug=False)
