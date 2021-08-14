#!/usr/bin/env nxpython
import time
import sys
from nxfunctions import *

default_password = None
import_zones = {}
add_suffix = ' (Default)'
all_zones = [o for o in s.getAllObjects() if isinstance(o, objects.Zone)]

fh = open('data/bulk-add-zones.csv', 'r')
for line in fh.readlines():
    if ',' in line:
        zone_name, zone_secret = line.strip().split(',', 1)
        import_zones[zone_name] = {'secret': zone_secret}
fh.close()

for zone_name in import_zones:
    new_zone_name = zone_name + (add_suffix or '')
    existing_zones = [z for z in all_zones if z.getObjectName() == new_zone_name]
    if existing_zones:
        import_zones[zone_name]['zone_id'] = existing_zones[0].getObjectId()
    else:
        cz = NXCObjectCreationData(objects.GenericObject.OBJECT_ZONE, new_zone_name, objects.GenericObject.NETWORK)
        zone_id = session.createObject(cz)
        import_zones[zone_name]['zone_id'] = zone_id

session.syncObjects()

for zone_name in sorted(import_zones.keys()):
    zone_id = import_zones[zone_name]['zone_id']
    apply_secrets = [import_zones[zone_name]['secret'], ]
    zone = session.findObjectById(zone_id)
    zone_uin = zone.getUIN()
    session.updateAgentSharedSecrets(zone_uin, apply_secrets)

    print rep_object(zone), '=', str(zone_uin)
    continue

    print rep_object(zone)
    print '\tNetXMS_ZoneID = ' + str(zone.getUIN())
    print '\tNetXMS_Secret = ' + import_zones[zone_name]['secret']


