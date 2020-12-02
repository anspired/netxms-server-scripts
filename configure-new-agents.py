#!/usr/bin/env nxpython

'''
Not actually used for anything.
'''

zone_secrets_map = {}
for zone in [o for o in s.getAllObjects() if isinstance(o, objects.Zone)]:
    zone_secrets = session.getAgentSharedSecrets(zone.UIN)
    if zone_secrets:
        zone_secrets_map[zone.getObjectId()] = zone_secrets[0]

for node in [o for o in s.getAllObjects() if isinstance(o, objects.Node)]:
    zone_id = node.getZoneId()
    if zone_id in zone_secrets_map:
        if not node.getAgentSharedSecret() and node.getPrimaryIP().toString() == '0.0.0.0/32':
            print('Updating secret for ' + node.getObjectName())
            md = NXCObjectModificationData(node.getObjectId())
            md.setAgentSecret(zone_secrets_map[zone_id])
            session.modifyObject(md)
            print('Polling node ' + node.getObjectName())
            session.pollNode(node.getObjectId(), NodePollType.CONFIGURATION_FULL, None)
