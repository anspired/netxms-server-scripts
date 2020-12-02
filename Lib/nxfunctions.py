import os
import sys
from java.util import HashMap
from java.lang import Long
from org.netxms.client.users import User, UserGroup
from org.netxms.client import NXCObjectModificationData
from org.netxms.client.objects.configs import CustomAttribute


INCOMING_CONTAINER_NAME = os.environ.get('NETXMS_INCOMING_CONTAINER', '_Default')


def zone_name_to_container_name(zone_name):
    return (zone_name.rsplit('(', 1))[0].strip()

def create_container(session, container_name):
    return session.createObject(NXCObjectCreationData(
        objects.GenericObject.OBJECT_CONTAINER,
        container_name,
        objects.GenericObject.SERVICEROOT
    ))

def set_custom_attribute(session, object, attr, value, inheret=False):
    md = NXCObjectModificationData(object.getObjectId())
    attr_map = HashMap(object.customAttributes)
    flags = 0
    if inheret:
        flags = CustomAttribute.INHERITABLE
    if value is None:
        if attr in attr_map:
            del attr_map[attr]
    else:
        attr_map.put(attr, CustomAttribute(str(value), flags, 0))
    md.setCustomAttributes(attr_map)
    session.modifyObject(md)

def rep_object(obj):
    if isinstance(obj, (User, UserGroup)):
        return '%s "%s" [%s]' % (obj.getClass().__name__, obj.getName(), obj.getId())
    try:
        return '%s "%s" [%s]' % (obj.getObjectClassName(), obj.getObjectName(), obj.getObjectId())
    except AttributeError:
        return '%s' % obj
