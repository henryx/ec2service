#!/usr/bin/python3

__author__ = 'ebianchi'

import boto.ec2
import boto.route53
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


def r53_open_conn(cfg):
    region = cfg["dns"]["region"]
    secret = cfg["dns"]["secret"]
    key = cfg["dns"]["key"]

    r53 = boto.route53.connect_to_region(region,
                                         aws_access_key_id=key,
                                         aws_secret_access_key=secret)

    if not r53:
        raise ValueError("Problem when connecting to Route53")

    return r53


def r53_manage(address, ip, action):
    cfg = load_cfg()
    r53 = r53_open_conn(cfg)
    domain = cfg["dns"]["domain"]

    zone = r53.get_zone(domain + ".")
    change_set = boto.route53.record.ResourceRecordSets(r53, zone.id)
    record = change_set.add_change(action, address + "." + domain, "A")
    record.add_value(ip)
    change_set.commit()


def ec2_open_conn(awsregion, account):
    cfg = load_cfg()

    awskey = cfg[account]["key"]
    awssecret = cfg[account]["secret"]

    if not any(region.name == awsregion for region in boto.ec2.regions()):
        raise ValueError('Region "{}" not valid'.format(awsregion))

    ec2 = boto.ec2.connect_to_region(awsregion,
                                     aws_access_key_id=awskey,
                                     aws_secret_access_key=awssecret)
    if not ec2:
        raise ValueError("Problem when connecting to EC2")

    return ec2


def ec2_instance_list(ec2conn, instance_id=None):
    results = []

    for reservation in ec2conn.get_all_reservations(
            instance_ids=[instance_id] if instance_id else None):
        for instance in reservation.instances:
            if instance.tags.get("managed", "") == "auto":
                details = {
                    "instance-id": instance.id,
                    "instance-type": instance.instance_type,
                    "region": reservation.region.name,
                    "placement": instance.placement,
                    "tags": instance.tags,
                    "state": instance.state,
                    "launch-time": instance.launch_time,
                    "image-id": instance.image_id,
                    "network": [dict(public_ip=i.publicIp if hasattr(i,
                                                                     "publicIp") else None,
                                     # TODO: check public IP resolution in DNS
                                     public_dns=i.publicDnsName if hasattr(i,
                                                                           "publicDnsName") else None,
                                     private_dns=i.privateDnsName,
                                     private_ip=i.private_ip_address)
                                for i in instance.interfaces],
                    "security-group": [dict(id=g.id, name=g.name)
                                       for g in instance.groups],
                    "volumes": [dict(id=v.id, size=v.size, type=v.type,
                                     created=v.create_time)
                                for v in ec2conn.get_all_volumes(
                            filters={'attachment.instance-id': instance.id})]
                }
                results.append(details)

    return results


def ec2_instance_ops(operation, name=None, hostname=None):
    data = {}
    try:
        region = bottle.request.query.region
        account = bottle.request.query.account

        if not region:
            raise ValueError("Region not selected")

        if not account:
            raise ValueError("Account not selected")

        with closing(ec2_open_conn(region, account)) as ec2:
            machines = ec2_instance_list(ec2, name)
            if machines:
                if operation == "list":
                    data = {"result": "ok",
                            "machine": machines,
                            "total": len(machines)
                            }
                elif operation == "start":
                    ec2.start_instances(instance_ids=[name])
                    if hostname:
                        r53_manage(hostname,
                                   machines[0]["network"]["public_ip"],
                                   "CREATE")
                    data = {"result": "ok",
                            "message": "Instance {} started".format(name)}
                elif operation == "stop":
                    ec2.stop_instances(instance_ids=[name])
                    if hostname:
                        r53_manage(hostname,
                                   machines[0]["network"]["public_ip"],
                                   "DELETE")
                    data = {"result": "ok",
                            "message": "Instance {} stopped".format(name)}
                elif operation == "reboot":
                    ec2.reboot_instances(instance_ids=[name])
                    data = {"result": "ok",
                            "message": "Instance {} rebooted".format(name)}
            else:
                raise bottle.HTTPError(status=500, body="No managed machines")

    except ValueError as err:
        raise bottle.HTTPError(status=500, body=str(err))

    return data


@app.hook('before_request')
def strip_path():
    bottle.request.environ['PATH_INFO'] = bottle.request.environ[
        'PATH_INFO'].rstrip('/')


@app.error(500)
def error500(error):
    return json.dumps({"result": "ko", "message": error.body})


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/instances", method="GET")
def instances_list():
    bottle.response.headers['Content-type'] = 'application/json'
    return json.dumps(ec2_instance_ops("list"))


@app.route("/instances/<name>", method="GET")
def instances_show(name):
    bottle.response.headers['Content-type'] = 'application/json'
    return json.dumps(ec2_instance_ops("list", name))


@app.route("/instances/<name>/<command:re:(start|stop|reboot)>", method="GET")
def instances_command(name, command):
    bottle.response.headers['Content-type'] = 'application/json'
    hostname = bottle.request.query.hostname or None

    return json.dumps(ec2_instance_ops(command, name, hostname))


if __name__ == "__main__":
    cfg = load_cfg()

    bottle.run(app=app,
               host=cfg["service"]["listen"],
               port=int(cfg["service"]["port"]),
               debug=cfg["service"].getboolean("debug"))
