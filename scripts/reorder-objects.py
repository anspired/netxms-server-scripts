#!/usr/bin/env nxpython
import time
import sys
import re
from nxfunctions import *


class ZoneCache:
    _instances = {}

    def __init__(self, session, zone):
        self.session = session
        self.zone = zone
        self.name = self.zone.getObjectName()
        self.loc_name = 'Default'
        if '(' in self.name and self.name[-1] == ')':
            a, b = self.name.rsplit('(', 1)
            self.name = a.strip()
            self.loc_name = b[0:-1].strip()

    def __getattr__(self, attr):
        return getattr(self.zone, attr)

    def to_container_name(self):
        ca_parent_container = self.zone.getCustomAttribute('parentContainer')
        if ca_parent_container:
            container = self.session.findObjectById(int(ca_parent_container.value))
            if container:
                return container.getObjectName()
        return self.name

    @classmethod
    def from_node(cls, session, node):
        if node.zoneId is not None:
            if node.zoneId not in cls._instances:
                cls._instances[node.zoneId] = cls(session, session.findZone(node.zoneId))
            return cls._instances[node.zoneId]


class NodeCategoriser:
    _hier = []
    _instances = []

    def __init__(self, session, node):
        self.node = node
        self.session = session
        self.name = self.get_category()
        self.zone = ZoneCache.from_node(session, node)
        self.__class__._instances.append(self)

    def __str__(self):
        return self.name

    def get_hierarchy(self):
        if self.zone:
            return tuple([self.node.zoneId] + [e for e in [self.zone.to_container_name(), self.get_location(), self.get_category()] if e is not None])
        else:
            return (None, self.get_location(), self.get_category())

    def get_location(self):
        for hide_if in ('hideLocation', 'locationHide'):
            if hide_if in self.node.customAttributes:
                if str(self.node.customAttributes[hide_if].value) == '1':
                    return
        for return_if in ('locationName', '_locationName'):
            if return_if in self.node.customAttributes:
                return self.node.customAttributes[return_if].value
        location = self.zone.loc_name
        if location == 'Default':
            return
        return location

    def get_category(self):
        for hide_if in ('hideCategory', 'categoryHide'):
            if hide_if in self.node.customAttributes:
                if str(self.node.customAttributes[hide_if].value) == '1':
                    return
        for return_if in ('categoryName', '_categoryName'):
            if return_if in self.node.customAttributes:
                return self.node.customAttributes[return_if].value


class ContainerObj:
    def __init__(self, zone_id, path, parent):
        self.zone_id = zone_id
        self.path = path
        self.parent = parent
        self.object_id = None
        self.children = []
        if parent:
            self.parent.children.append(self)

    def __repr__(self):
        return '<ContainerObj(%s, count:%s>' % (self.path, self.child_count())

    def child_count(self):
        total = len(self.children)
        for child in self.children:
            total += child.child_count()
        return total


class HierarchyBuilder:
    KEEP_EMPTY_CONTAINERS = ['_Default',]

    def __init__(self, session, categorisers):
        self.session = session
        self.categorisers = categorisers
        self.container_cache = {}
        self.paths = {}
        self.hier = {}
        self.get_container_hierarchy()
        self.newly_created_containers = []

    def get_paths(self):
        for path in set([c.get_hierarchy() for c in self.categorisers if c.node.zoneId != 0]):
            for i in range(1, len(path)):
                short_path = (path[0],) + path[1:i+1]
                if short_path not in paths:
                    paths.append(short_path)
        return sorted(paths)#, key=lambda x: str(x[1:]))

    def get_container_hierarchy(self):
        for path in set([c.get_hierarchy() for c in self.categorisers if c.node.zoneId != 0]):
            last_obj = None
            for i in range(1, len(path)):
                zone_id = path[0]
                short_path = path[1:i+1]
                if short_path not in self.hier:
                    self.hier[short_path] = ContainerObj(zone_id, short_path, last_obj)
                last_obj = self.hier[short_path]
        return self.hier

    def build_hierarchy(self):
        newly_created = []
        for co in sorted(self.hier.values(), key=lambda x: x.path):
            path_seg_name = co.path[-1]
            parent_id = objects.GenericObject.SERVICEROOT
            if co.parent:
                parent_id = co.parent.object_id

            existing = None
            if parent_id not in newly_created:
                parent_containers = self.containers_below_object(parent_id)
                existing = [c for c in parent_containers if c.getObjectName() == path_seg_name]

            if existing:
                co.object_id = existing[0].getObjectId()
            else:
                print 'creating %s (%s)' % (co, path_seg_name)
                co.object_id = self.create_container(path_seg_name, parent_id)
                print 'container ID is %s' % co.object_id
                newly_created.append(co.object_id)
                self.newly_created_containers.append(co.object_id)

    def relocate_nodes(self, lowercase_names=None):
        for c in self.categorisers:
            path = c.get_hierarchy()[1:]
            co = self.hier.get(path, None)
            if co:
                bound_containers = [o for o in c.node.getParentsAsArray() if isinstance(o, objects.Container)]
                bound_containers_ids = [o.getObjectId() for o in bound_containers]
                if co.object_id not in bound_containers_ids:
                    session.bindObject(co.object_id, c.node.getObjectId())
                for container in bound_containers:
                    container_id = container.getObjectId()
                    if container.autoBindEnabled:
                        pass
                    if container_id != co.object_id:
                        self.session.unbindObject(container_id, c.node.getObjectId())
                if lowercase_names is True:
                    name_orig = c.node.getObjectName()
                    name_lower = c.node.getObjectName().lower()
                    if name_orig != name_lower:
                        self.session.setObjectName(c.node.getObjectId(), name_lower)

    def find_empty_containers(self):
        return [
            o for o in s.getAllObjects()
            if (
                isinstance(o, objects.Container) and
                len(o.getChildrenAsArray()) == 0 and
                o.getObjectId() not in self.newly_created_containers and
                not o.getObjectName().startswith('_') and
                not o.autoBindEnabled and
                o.getObjectName() not in self.KEEP_EMPTY_CONTAINERS
            )
        ]

    def remove_empty_containers(self):
        while True:
            empties = self.find_empty_containers()
            for empty in empties:
                self.session.deleteObject(empty.getObjectId())
            if not empties:
                break

    def containers_below_object(self, object_id):
        return [
            o for o in self.session.findObjectById(object_id).getChildrenAsArray()
            if isinstance(o, objects.Container)
        ]

    def create_container(self, container_name, parent=None):
        if parent is None:
            parent = objects.GenericObject.SERVICEROOT
        return self.session.createObject(NXCObjectCreationData(
            objects.GenericObject.OBJECT_CONTAINER,
            container_name,
            parent
        ))


def filter_node_by_args(node):
    filter_by_node = [e.lower() for e in sys.argv[1:]]
    if filter_by_node:
        return node.getObjectName().lower() in filter_by_node
    return True

nodes = [o for o in s.getAllObjects() if isinstance(o, objects.Node)]
categorisers = [NodeCategoriser(session, node) for node in nodes if filter_node_by_args(node)]
builder = HierarchyBuilder(session, categorisers)
builder.build_hierarchy()
session.syncObjects()
builder.relocate_nodes(lowercase_names=True)
session.syncObjects()
builder.remove_empty_containers()
session.disconnect()
