#!/usr/bin/env nxpython
from nxfunctions import *


containers_by_id = {}
containers_by_name = {}
newly_bound_agents = None


# Locate the container that we automatically bind new agents to
def refresh_container_mappings():
    containers_by_id = {}
    containers_by_name = {}
    for container in [o for o in s.getAllObjects() if isinstance(o, objects.Container)]:
        containers_by_id[container.getObjectId()] = container
        containers_by_name[container.getObjectName()] = container
        if container.getObjectName() == INCOMING_CONTAINER_NAME:
            newly_bound_agents = container
refresh_container_mappings()

# Enumerate zones, set customAttribute if the container already exists
for zone in [o for o in s.getAllObjects() if isinstance(o, objects.Zone)]:
    set_custom_attribute(session, zone, 'zoneUIN', zone.UIN)
    container_attr = zone.getCustomAttribute('parentContainer')
    zone_container = None
    if container_attr is not None:
        container = session.findObjectById(int(container_attr.value))
        if container is None:
            container_attr = None
    if container_attr is None:
        zone_container = containers_by_name.get(zone.getObjectName(), None)
        if zone_container:
            set_custom_attribute(session, zone, 'parentContainer', zone_container.getObjectId())
    else:
        zone_container = session.findObjectById(int(container_attr.value))
        if zone_container:
            container_name = zone_container.getObjectName()
            new_container_name = zone_name_to_container_name(zone.getObjectName())
            if container_name != INCOMING_CONTAINER_NAME and container_name != new_container_name:
                if not container_name.startswith('_'):
                    print 'renaming %s to "%s"' % (rep_object(zone_container), new_container_name)
                    session.setObjectName(zone_container.getObjectId(), new_container_name)
    if container_attr:
        set_custom_attribute(session, zone, 'parentContainer', container_attr.value, inheret=True)
refresh_container_mappings()

# Throw nodes in a container matching the name of their zone
# -> creating a container if no container ID has been recorded in parentContainer attribute
# -> in an existing container if there's a parentContainer (which allows for it to be renamed)
need_containers_for_zones = []
for node in [o for o in s.getAllObjects() if isinstance(o, objects.Node)]:
    containers = [o for o in node.getParentsAsArray() if isinstance(o, objects.Container)]
    zone = session.findZone(node.zoneId)
    container_attr = zone.getCustomAttribute('parentContainer')
    container_for_zone = None
    if not container_attr and zone.getObjectName() != 'Default':
        if zone not in need_containers_for_zones:
            need_containers_for_zones.append(zone)
for zone in need_containers_for_zones:
    container_attr = zone.getCustomAttribute('parentContainer')
    print 'Creating container for %s' % rep_object(zone)
    zone_name = zone.getObjectName()
    container_id = create_container(session, zone_name_to_container_name(zone_name))
    set_custom_attribute(session, zone, 'parentContainer', container_id, inheret=True)
    container_for_zone = containers_by_id.get(int(container_id))
    if container_for_zone:
        set_custom_attribute(session, zone, 'parentContainer', container.getObjectId())
refresh_container_mappings()

# Refresh container mappings and print all containers
for container_id in containers_by_id:
    print rep_object(session.findObjectById(container_id))

# Print our container/zone mappings
for zone in [o for o in s.getAllObjects() if isinstance(o, objects.Zone)]:
    container_attr = zone.getCustomAttribute('parentContainer')
    if container_attr:
        container = session.findObjectById(int(container_attr.value))
        if container:
            print '%s has parent %s' % (rep_object(zone), rep_object(container))

# Bind/unbind our nodes if there are parentContainer objects
# NOTE: you can set parentContainer on a per-node level if necessary
for node in [o for o in s.getAllObjects() if isinstance(o, objects.Node)]:
    containers = [o for o in node.getParentsAsArray() if isinstance(o, objects.Container)]
    container_ids = [c.getObjectId() for c in containers]
    container_attr = node.getCustomAttribute('parentContainer')
    if container_attr:
        zone_container = session.findObjectById(int(container_attr.value))
        # If we have a valid zone container and our node is not bound here, bind it
        if zone_container and zone_container.getObjectId() not in container_ids:
            print 'Binding %s to %s' % (rep_object(node), rep_object(zone_container))
            session.bindObject(int(container_attr.value), node.getObjectId())
        # If we have a valid zone container remove all other container bindings
        for container in containers:
            if container != zone_container:
                print 'Unbinding %s from %s' % (rep_object(node), rep_object(container))
                session.unbindObject(container.getObjectId(), node.getObjectId())

# Convert all object names to lowercase
for node in [o for o in s.getAllObjects() if isinstance(o, objects.Node)]:
    node_name = node.getObjectName()
    node_name_lower = node.getObjectName().lower()
    if node_name != node_name_lower:
        print 'Renaming node %s to %s' % (rep_object(node), node_name_lower)
        session.setObjectName(node.getObjectId(), node_name_lower)

sys.exit(0)
