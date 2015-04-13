#!/usr/bin/python3

__author__ = 'ebianchi'

import boto.ec2
import bottle
import configparser
import json
import sys

# FIXME: for commodity, config file is declared as global variable. Change in future
CFG = configparser.ConfigParser()

def open_ec2(region=None):
    awskey = CFG["aws"]["key"]
    awssecret = CFG["aws"]["secret"]
    awsregion = region or CFG["aws"]["region"]

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

    for reservation in ec2conn.get_all_reservations():
        for instance in reservation.instances:
            if "managed" in instance.tags and instance.tags["managed"] == "auto":
                details = {
                    "id": instance.id,
                    "placement": instance.placement,
                    "tags": instance.tags,
                    "state": instance.state,
                    "launch time": instance.launch_time,
                    "network": [dict(public_ip=i.publicIp if hasattr(i, "publicIp") else None,
                                     # TODO: check public IP resolution in DNS
                                     public_dns=i.publicDnsName if hasattr(i, "publicDnsName") else None,
                                     private_dns=i.privateDnsName,
                                     private_ip=i.private_ip_address)
                                for i in instance.interfaces],
                    "security group": [dict(id=g.id, name=g.name)
                                       for g in instance.groups]
                }

                if not instance_id or instance_id == instance.id:
                    results.append(details)

    return results

@bottle.hook('before_request')
def strip_path():
    bottle.request.environ['PATH_INFO'] = bottle.request.environ['PATH_INFO'].rstrip('/')

@bottle.error(500)
def error500(error):
    return json.dumps({"result": "ko", "message": error.body})

@bottle.route("/")
def hello():
    return "Hello World!"

@bottle.route("/machines", method="GET")
def machine_list():
    try:
        ec2 = open_ec2(region=bottle.request.query.region)
        machines = list_ec2_instances(ec2)
        ec2.close()

        if len(machines) > 0:
            data = {"result": "ok", "machine": machines, "total": len(machines)}
        else:
            raise bottle.HTTPError(status=500, body="No managed machines")
    except ValueError as err:
        raise bottle.HTTPError(status=500, body=str(err))

    return json.dumps(data)

@bottle.route("/machines/<name>", method="GET")
def machine_show(name):
    try:
        ec2 = open_ec2(region=bottle.request.query.region)
        machines = list_ec2_instances(ec2, name)
        ec2.close()

        if len(machines) > 0:
            data = {"result": "ok", "machine": machines, "total": len(machines)}
        else:
            raise bottle.HTTPError(status=500, body="No managed machines")
    except ValueError as err:
        raise bottle.HTTPError(status=500, body=str(err))

    return json.dumps(data)

@bottle.route("/machines/<name>/start", method="GET")
def machine_command(name):
    try:
        ec2 = open_ec2(region=bottle.request.query.region)
        ec2.start_instances(instance_ids=[name])
        ec2.close()
    except ValueError as err:
        raise bottle.HTTPError(status=500, body=str(err))

    return json.dumps({"result": "ok", "message": "Instance {} started".format(name)})

@bottle.route("/machines/<name>/stop", method="GET")
def machine_command(name):
    try:
        ec2 = open_ec2(region=bottle.request.query.region)
        ec2.stop_instances(instance_ids=[name])
        ec2.close()
    except ValueError as err:
        raise bottle.HTTPError(status=500, body=str(err))

    return json.dumps({"result": "ok", "message": "Instance {} stopped".format(name)})

@bottle.route("/machines/<name>/reboot", method="GET")
def machine_command(name):
    try:
        ec2 = open_ec2(region=bottle.request.query.region)
        ec2.reboot_instances(instance_ids=[name])
        ec2.close()
    except ValueError as err:
        raise bottle.HTTPError(status=500, body=str(err))

    return json.dumps({"result": "ok", "message": "Instance {} rebooted".format(name)})

if __name__ == "__main__":
    try:
        CFG.read(sys.argv[1])
    except:
        print("Usage: " + sys.argv[0] + " <configfile>")
        sys.exit(1)

    bottle.run(host=CFG["service"]["listen"], port=int(CFG["service"]["port"]), debug=CFG["service"].getboolean("debug"))
