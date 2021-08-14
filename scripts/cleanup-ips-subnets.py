#!/usr/bin/env nxpython
#
# Script to remove auto-discovered objects that have not been renamed

from nxfunctions import *

for node in [o for o in s.getAllObjects() if isinstance(o, objects.Node)]:
    if str(node.primaryName) == '0.0.0.0': continue
    if str(node.objectName) != str(node.primaryName): continue
    if str(node.primaryIP).split('/')[0] == str(node.primaryName):
        print 'Deleting object: %s with primaryIP of %s' % (rep_object(node), node.primaryIP)
        session.deleteObject(node.getObjectId())
    session.syncObjects()

for subnet in [o for o in s.getAllObjects() if isinstance(o, objects.Subnet)]:
    if not list(subnet.getChildrenAsArray()):
        print 'Deleting subnet: %s' % subnet.getObjectName()
        session.deleteObject(subnet.getObjectId())

session.syncObjects()
session.disconnect()
