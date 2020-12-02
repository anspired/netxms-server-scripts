#!/usr/bin/env nxpython
from nxfunctions import *


# For 'customerGroup' groups, give them the same permissions as
CUSTOMER_GROUP_LEVEL = 'L1'

# Access Rights and the groups that are assigned to them
PERMISSION_MAPPING = {
    UserAccessRights.OBJECT_ACCESS_READ: ('L1', 'L2', 'L3'),
    UserAccessRights.OBJECT_ACCESS_MODIFY: ('L2', 'L3'),
    UserAccessRights.OBJECT_ACCESS_DELETE: ('L2', 'L3'),
    UserAccessRights.OBJECT_ACCESS_CREATE: ('L2', 'L3'),
    UserAccessRights.OBJECT_ACCESS_UPDATE_ALARMS: ('L2', 'L3'),
    UserAccessRights.OBJECT_ACCESS_READ_ALARMS: ('L1', 'L2', 'L3'),
    UserAccessRights.OBJECT_ACCESS_TERM_ALARMS: ('L1', 'L2', 'L3'),
    UserAccessRights.OBJECT_ACCESS_CONTROL: ('L2', 'L3'),
    UserAccessRights.OBJECT_ACCESS_SEND_EVENTS: ('L3', ),
    UserAccessRights.OBJECT_ACCESS_ACL: ('L3', ),
    UserAccessRights.OBJECT_ACCESS_PUSH_DATA: ('L3', ),
    UserAccessRights.OBJECT_ACCESS_DOWNLOAD: ('L2', 'L3'),
    UserAccessRights.OBJECT_ACCESS_UPLOAD: ('L2', 'L3'),
    UserAccessRights.OBJECT_ACCESS_READ_AGENT: ('L2', 'L3'),
    UserAccessRights.OBJECT_ACCESS_READ_SNMP: ('L2', 'L3'),
    UserAccessRights.OBJECT_ACCESS_CREATE_ISSUE: ('L3', ),
    UserAccessRights.OBJECT_ACCESS_SCREENSHOT: ('L1', 'L2', 'L3'),
    UserAccessRights.OBJECT_ACCESS_MAINTENANCE: ('L1', 'L2', 'L3'),
    UserAccessRights.OBJECT_ACCESS_MANAGE_FILES: ('L1', 'L2', 'L3')
}

# Create a dict of "group name" -> UserGroup object
GROUP_MAP = {
    group.getName(): group
    for group in session.userDatabaseObjects
    if isinstance(group, users.UserGroup)
}


def generate_acl_list(*group_subs):
    '''
    Enumerate PERMISSION_MAPPING and return a list of AccessListElement objects for session.setACL
    Optionally can be provided multiple tuples as separate arguments, this tuple will be:
        (original_group, base_on_group) -> permissions in PERMISSION_MAPPING for 'base_on_group'
        will be duplicated and ACLs generated for original_group
    '''
    acl_list = {}
    for accessright in PERMISSION_MAPPING:
        identities = list(PERMISSION_MAPPING[accessright]) + ['Admins',]
        for if_group, add_group in group_subs:
            if if_group in identities:
                identities.append(add_group)
        for identity in identities:
            if identity not in acl_list:
                acl_list[identity] = 0
            acl_list[identity] |= accessright
    return [
        AccessListElement(GROUP_MAP[e].getId(), acl_list[e])
        for e in acl_list if e in GROUP_MAP
    ]


# Iterate over all containers below the Service Root object, 'Infrastructure Services'
sr_children = session.findObjectById(objects.GenericObject.SERVICEROOT).getChildrenAsArray()
for container in [o for o in sr_children if isinstance(o, objects.Container)]:
    # Don't adjust permissions for groups starting with '_'
    if container.getObjectName().startswith('_'):
        continue

    # Retrieve the 'customerGroup' attribute on container, this should match exactly an existing group
    # and that group will also be given permissions over the container, matching CUSTOMER_GROUP_LEVEL
    customer_group = container.getCustomAttributeValue('customerGroup')    
    acl_list = generate_acl_list((CUSTOMER_GROUP_LEVEL, customer_group))

    # Apply our new list of ACLs to the sub-container
    print 'Setting ACLs on %s to %s' % (rep_object(container), acl_list)
    session.setObjectACL(container.getObjectId(), acl_list, False)

