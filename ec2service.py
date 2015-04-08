#!/usr/bin/python3

__author__ = 'ebianchi'

import boto.ec2
import bottle
import configparser
import json
import sys

# FIXME: for commodity, config file is declared as global variable. Change in future
CFG = configparser.ConfigParser()

def open_ec2():
    awskey = CFG.get("aws", "key")
    awssecret = CFG.get("aws", "secret")
    region = CFG.get("aws", "region")

    ec2 = boto.ec2.connect_to_region(region,
                                     aws_access_key_id=awskey,
                                     aws_secret_access_key=awssecret)
    return ec2

def list_ec2_instances(ec2conn, instance_id=None):
    results = []
    reservations = ec2conn.get_all_reservations()
    for reservation in reservations:
        for instance in reservation.instances:
            if "managed" in instance.tags and instance.tags["managed"] == "auto":
                details = {
                    "id": instance.id,
                    "placement": instance.placement,
                    "tags": instance.tags,
                    "state": instance.state,
                    "launch time": instance.launch_time,
                    "network": [],
                    "security group": []
                }

                for interface in instance.interfaces:
                    details_interface = {
                        "public ip": interface.publicIp,
                        "public dns": interface.publicDnsName,  # TODO: check public IP resolution in DNS
                        "private dns": interface.privateDnsName,
                        "private ip": interface.private_ip_address,
                    }
                    details["network"].append(details_interface)

                # TODO: check if is useful to implement in external function
                for group in instance.groups:
                    details_group = {
                        "id": group.id,
                        "name": group.name,
                    }
                    details["security group"].append(details_group)

                results.append(details)

    return results

@bottle.route("/")
def hello():
    return "Hello World!"

@bottle.route("/machines/", method="GET")
def machine_list():
    data = {}
    ec2 = open_ec2()
    machines = list_ec2_instances(ec2)
    if len(machines) > 0:
        data["result"] = "ok"
        data["machines"] = machines
    else:
        data["result"] = "ko"
        data["message"] = "No managed machines"
    return json.dumps(data)

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
    try:
        CFG.read(sys.argv[1])
    except:
        print("Usage: " + sys.argv[0] + " <configfile>")
        sys.exit(1)

    bottle.run(host=CFG.get("service", "listen"), port=CFG.get("service", "port"), debug=False)
