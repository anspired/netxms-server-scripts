#!/usr/bin/env nxpython
from nxfunctions import *
from org.netxms.client.constants import UserAccessRights
from org.netxms.client.users import UserGroup
from org.netxms.client import AccessListElement

# For 'customerGroup' groups, give them the same permissions as
CUSTOMER_GROUP_LEVEL = 'Techs-Level1'

# These groups have access to everything
ADMIN_GROUPS = ['NetXMS-Admins', 'Admins']

# Access Rights and the groups that are assigned to them
PERMISSION_MAPPING = {
    UserAccessRights.OBJECT_ACCESS_READ: ('Techs-Level1', 'Techs-Level2', 'Techs-Level3'),
    UserAccessRights.OBJECT_ACCESS_MODIFY: ('Techs-Level2', 'Techs-Level3'),
    UserAccessRights.OBJECT_ACCESS_DELETE: ('Techs-Level2', 'Techs-Level3'),
    UserAccessRights.OBJECT_ACCESS_CREATE: ('Techs-Level2', 'Techs-Level3'),
    UserAccessRights.OBJECT_ACCESS_UPDATE_ALARMS: ('Techs-Level2', 'Techs-Level3'),
    UserAccessRights.OBJECT_ACCESS_READ_ALARMS: ('Techs-Level1', 'Techs-Level2', 'Techs-Level3'),
    UserAccessRights.OBJECT_ACCESS_TERM_ALARMS: ('Techs-Level1', 'Techs-Level2', 'Techs-Level3'),
    UserAccessRights.OBJECT_ACCESS_CONTROL: ('Techs-Level2', 'Techs-Level3'),
    UserAccessRights.OBJECT_ACCESS_SEND_EVENTS: ('Techs-Level3', ),
    UserAccessRights.OBJECT_ACCESS_ACL: ('Techs-Level3', ),
    UserAccessRights.OBJECT_ACCESS_PUSH_DATA: ('Techs-Level3', ),
    UserAccessRights.OBJECT_ACCESS_DOWNLOAD: ('Techs-Level2', 'Techs-Level3'),
    UserAccessRights.OBJECT_ACCESS_UPLOAD: ('Techs-Level2', 'Techs-Level3'),
    UserAccessRights.OBJECT_ACCESS_READ_AGENT: ('Techs-Level2', 'Techs-Level3'),
    UserAccessRights.OBJECT_ACCESS_READ_SNMP: ('Techs-Level2', 'Techs-Level3'),
    UserAccessRights.OBJECT_ACCESS_CREATE_ISSUE: ('Techs-Level3', ),
    UserAccessRights.OBJECT_ACCESS_SCREENSHOT: ('Techs-Level1', 'Techs-Level2', 'Techs-Level3'),
    UserAccessRights.OBJECT_ACCESS_MAINTENANCE: ('Techs-Level1', 'Techs-Level2', 'Techs-Level3'),
    UserAccessRights.OBJECT_ACCESS_MANAGE_FILES: ('Techs-Level1', 'Techs-Level2', 'Techs-Level3')
}

# Create a dict of "group name" -> UserGroup object
GROUP_MAP = {
    group.getName(): group
    for group in session.userDatabaseObjects
    if isinstance(group, UserGroup)
}


def generate_acl_list(skip_groups=[], subs=[]):
    '''
    Enumerate PERMISSION_MAPPING and return a list of AccessListElement objects for session.setACL
    Optionally can be provided multiple tuples as separate arguments, this tuple will be:
        (original_group, base_on_group) -> permissions in PERMISSION_MAPPING for 'base_on_group'
        will be duplicated and ACLs generated for original_group
    '''
    acl_list = {}
    for accessright in PERMISSION_MAPPING:
        identities = list(PERMISSION_MAPPING[accessright]) + ADMIN_GROUPS
        identities = [ident for ident in identities if ident not in skip_groups]
        for if_group, add_group in subs:
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
    skip_groups = []

    # Skip applying some ACLs if the container starts with an underscore:
    #if container.getObjectName().startswith('_'):
    #    skip_groups = ['Techs-Level1']

    # Retrieve the 'customerGroup' attribute on container, this should match exactly an existing group
    # and that group will also be given permissions over the container, matching CUSTOMER_GROUP_LEVEL
    customer_group = container.getCustomAttributeValue('customerGroup')
    acl_list = generate_acl_list(
        skip_groups=skip_groups,
        subs=[(CUSTOMER_GROUP_LEVEL, customer_group)]
    )

    # Apply our new list of ACLs to the sub-container
    print 'Setting ACLs on %s to %s' % (rep_object(container), acl_list)
    session.setObjectACL(container.getObjectId(), acl_list, False)

session.syncObjects()
session.disconnect()

