#!/usr/bin/python3

__author__ = 'ebianchi'

import boto.ec2
import bottle
import configparser
import json
import sys

# FIXME: for commodity, config file is declared as global variable. Change in future
CFG = configparser.ConfigParser()

# AWS Available regions
REGIONS = [
    "us-east-1",  # North Virginia
    "us-west-1",  # North California
    "us-west-2",  # Oregon
    "eu-west-1",  # Ireland
    "eu-central-1",  # Frankfurt
    "ap-southeast-1",  # Singapore
    "ap-northeast-1",  # Tokyo
    "ap-southeast-2",  # Sydney
    "sa-east-1",  # Sao Paulo
]

def open_ec2(region=None):
    awskey = CFG.get("aws", "key")
    awssecret = CFG.get("aws", "secret")
    awsregion = region or CFG.get("aws", "region")

    if awsregion not in REGIONS:
        raise ValueError('Region "{}" not valid'.format(awsregion))

    ec2 = boto.ec2.connect_to_region(awsregion,
                                     aws_access_key_id=awskey,
                                     aws_secret_access_key=awssecret)
    if not ec2:
        raise ValueError("Problem when connecting to EC2")

    return ec2

def list_ec2_instances(ec2conn, instance_id=None):
    def list_interfaces(interfaces):
        result = []
        for interface in interfaces:
            details_interface = {
                "public ip": interface.publicIp,
                "public dns": interface.publicDnsName,  # TODO: check public IP resolution in DNS
                "private dns": interface.privateDnsName,
                "private ip": interface.private_ip_address,
            }
            result.append(details_interface)
        return result

    def list_security_groups(groups):
        result = []
        for group in groups:
            details_group = {
                "id": group.id,
                "name": group.name,
            }
            result.append(details_group)
        return result

    results = []
    reservations = ec2conn.get_all_reservations()
    for reservation in reservations:
        for instance in reservation.instances:
            if "managed" in instance.tags and instance.tags["managed"] == "auto":
                if not instance_id:
                    details = {
                        "id": instance.id,
                        "placement": instance.placement,
                        "tags": instance.tags,
                        "state": instance.state,
                        "launch time": instance.launch_time,
                        "network": list_interfaces(instance.interfaces),
                        "security group": list_security_groups(instance.groups)
                    }
                else:
                    if instance_id == instance.id:
                        details = {
                            "id": instance.id,
                            "placement": instance.placement,
                            "tags": instance.tags,
                            "state": instance.state,
                            "launch time": instance.launch_time,
                            "network": list_interfaces(instance.interfaces),
                            "security group": list_security_groups(instance.groups)
                        }
                results.append(details)

    return results

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
            data = {"result": "ok", "machines": machines}
        else:
            raise bottle.HTTPError(status=500, body="No managed machines")
    except ValueError as err:
        raise bottle.HTTPError(status=500, body=str(err))

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
