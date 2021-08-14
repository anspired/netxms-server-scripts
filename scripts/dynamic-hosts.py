#!/usr/bin/env nxpython
#
# Iterates over all nodes, and tries to do the following:
#   1. Checks for hostnameFromDNS custom attribute
#   2. Uses socket.gethostbyname to resolve that value to an IP address
#   3. If there is a result, the primaryName attribute of the node is updated
#
# This is useful for devices with dynamic IPs, such as WatchGuard firewalls
# connecting to a management server via Management Tunnels. Used in conjunction
# with a script that parses firewall logs to update DNS records.
#

import socket

nodes = [o for o in s.getAllObjects() if isinstance(o, objects.Node)]
for node in nodes:
    hostname_from_dns = None
    for key in node.customAttributes:
        if key == 'hostnameFromDNS':
            hostname_from_dns = node.customAttributes[key].value

    if hostname_from_dns:
        ipv4 = None
        try:
            ipv4 = socket.gethostbyname(hostname_from_dns)
        except:
            print 'Unable to resolve: %s' % hostname_from_dns
            pass

        if ipv4 and node.primaryName != ipv4:
            print 'Updating %s primaryName to %s' % (node.getObjectName(), ipv4)
            md = NXCObjectModificationData(node.getObjectId())
            md.setPrimaryName(ipv4)
            session.modifyObject(md)

session.syncObjects()
session.disconnect()
