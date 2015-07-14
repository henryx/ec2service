#!/usr/bin/python3

__author__ = 'ebianchi'

import boto.ec2
import bottle
import configparser
import json
import sys

from contextlib import closing

app = application = bottle.Bottle()

def load_cfg():
    cfg = configparser.ConfigParser()
    try:
        cfg.read(sys.argv[1])
    except:
        print("Usage: " + sys.argv[0] + " <configfile>")
        sys.exit(1)

    return cfg

def open_ec2(region=None, key=None, secret=None):
    cfg = load_cfg()

    awskey = key or cfg["aws"]["key"]
    awssecret = secret or cfg["aws"]["secret"]
    awsregion = region or cfg["aws"]["region"]

    if not any(region.name == awsregion for region in boto.ec2.regions()):
        raise ValueError('Region "{}" not valid'.format(awsregion))

    ec2 = boto.ec2.connect_to_region(awsregion,
                                     aws_access_key_id=awskey,
                                     aws_secret_access_key=awssecret)
    if not ec2:
        raise ValueError("Problem when connecting to EC2")

    return ec2

def list_ec2_instances(ec2conn, instance_id=None):
    results = []

    for reservation in ec2conn.get_all_reservations(instance_ids=[instance_id] if instance_id else None):
        for instance in reservation.instances:
            if "managed" in instance.tags and instance.tags["managed"] == "auto":
                details = {
                    "instance-id": instance.id,
                    "instance-type": instance.instance_type,
                    "placement": instance.placement,
                    "tags": instance.tags,
                    "state": instance.state,
                    "launch-time": instance.launch_time,
                    "network": [dict(public_ip=i.publicIp if hasattr(i, "publicIp") else None,
                                     # TODO: check public IP resolution in DNS
                                     public_dns=i.publicDnsName if hasattr(i, "publicDnsName") else None,
                                     private_dns=i.privateDnsName,
                                     private_ip=i.private_ip_address)
                                for i in instance.interfaces],
                    "security-group": [dict(id=g.id, name=g.name)
                                       for g in instance.groups],
                    "volumes": [dict(id=v.id, size=v.size, type=v.type,
                                     created=v.create_time)
                                for v in ec2conn.get_all_volumes(filters={'attachment.instance-id': instance.id})]
                }
                results.append(details)

    return results

@app.hook('before_request')
def strip_path():
    bottle.request.environ['PATH_INFO'] = bottle.request.environ['PATH_INFO'].rstrip('/')

@app.error(500)
def error500(error):
    return json.dumps({"result": "ko", "message": error.body})

@app.route("/")
def hello():
    return "Hello World!"

@app.route("/instances", method="GET")
def machine_list():
    bottle.response.headers['Content-type'] = 'application/json'
    try:
        with closing(open_ec2(region=bottle.request.query.region,
                       key=bottle.request.query.key,
                       secret=bottle.request.query.secret)) as ec2:

            machines = list_ec2_instances(ec2)
            if machines:
                data = {"result": "ok", "machine": machines, "total": len(machines)}
            else:
                raise bottle.HTTPError(status=500, body="No managed machines")
    except ValueError as err:
        raise bottle.HTTPError(status=500, body=str(err))

    return json.dumps(data)

@app.route("/instances/<name>", method="GET")
def machine_show(name):
    bottle.response.headers['Content-type'] = 'application/json'
    try:
        with closing(open_ec2(region=bottle.request.query.region,
                       key=bottle.request.query.key,
                       secret=bottle.request.query.secret)) as ec2:

            machines = list_ec2_instances(ec2, name)
            if machines:
                data = {"result": "ok", "machine": machines, "total": len(machines)}
            else:
                raise bottle.HTTPError(status=500, body="No managed machine")
    except ValueError as err:
        raise bottle.HTTPError(status=500, body=str(err))

    return json.dumps(data)

@app.route("/instances/<name>/start", method="GET")
def machine_command(name):
    bottle.response.headers['Content-type'] = 'application/json'
    try:
        with closing(open_ec2(region=bottle.request.query.region,
                       key=bottle.request.query.key,
                       secret=bottle.request.query.secret)) as ec2:

            machines = list_ec2_instances(ec2, name)
            if machines:
                ec2.start_instances(instance_ids=[name])
            else:
                raise bottle.HTTPError(status=500, body="No managed machine")
    except ValueError as err:
        raise bottle.HTTPError(status=500, body=str(err))

    return json.dumps({"result": "ok", "message": "Instance {} started".format(name)})

@app.route("/instances/<name>/stop", method="GET")
def machine_command(name):
    bottle.response.headers['Content-type'] = 'application/json'
    try:
        with closing(open_ec2(region=bottle.request.query.region,
                       key=bottle.request.query.key,
                       secret=bottle.request.query.secret)) as ec2:

            machines = list_ec2_instances(ec2, name)
            if machines:
                ec2.stop_instances(instance_ids=[name])
            else:
                raise bottle.HTTPError(status=500, body="No managed machine")
    except ValueError as err:
        raise bottle.HTTPError(status=500, body=str(err))

    return json.dumps({"result": "ok", "message": "Instance {} stopped".format(name)})

@app.route("/instances/<name>/reboot", method="GET")
def machine_command(name):
    bottle.response.headers['Content-type'] = 'application/json'
    try:
        with closing(open_ec2(region=bottle.request.query.region,
                       key=bottle.request.query.key,
                       secret=bottle.request.query.secret)) as ec2:

            machines = list_ec2_instances(ec2, name)
            if machines:
                ec2.reboot_instances(instance_ids=[name])
            else:
                raise bottle.HTTPError(status=500, body="No managed machine")
    except ValueError as err:
        raise bottle.HTTPError(status=500, body=str(err))

    return json.dumps({"result": "ok", "message": "Instance {} rebooted".format(name)})

if __name__ == "__main__":
    cfg = load_cfg()

    bottle.run(app=app,
               host=cfg["service"]["listen"],
               port=int(cfg["service"]["port"]),
               debug=cfg["service"].getboolean("debug"))
