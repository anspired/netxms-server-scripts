#!/usr/bin/env nxpython
# 
# Iterates over all nodes, and tries to do the following:
#   1. Identify a category for the node
#         If the custom attribute categoryName is set, this value will be used
#         If the custom attribute isServer is set to 1, NodeIdentification.SERVER will be used
#   2. Set a custom attribute (_categoryName) for the node
#   3. Sets the node's object category to one of the following values:
#         category-name
#         category-name.grey (if "categoryname.green" and "categoryname.grey" exist)
#      For example a "Multifunction-Printer" category would update the category to multifunction-printer.grey,
#      if multifunction-printer.grey and multifunction-printer.green both exist (and the current category is neither
#      .grey or .green). Otherwise, it will try for "multifunction-printer"
#


import os
import re
from java.util import HashMap
from org.netxms.client.objects.configs import CustomAttribute
from org.netxms.client import NXCObjectModificationData
import org.netxms.client.objects as objects


def in_list_upper(check_item, find_items):
    if not check_item:
        return None
    for li in find_items:
        if li.upper() in check_item.upper():
            return True
    return False


class NodeIdentification(object):
    nx_object_categories = {}
    PRINTER = 'Multifunction-Printer'
    ROUTER = 'Router'
    UTM_DEVICE = 'Firewall'
    SWITCH = 'Switch'
    NAS = 'NAS'
    NETWORK_STORAGE = 'NAS'
    PORTABLE = 'Workstation'
    SERVER = 'Server'
    WORKSTATION = 'Workstation'
    OTHER = 'Other'
    UNKNOWN = 'Unknown'
    MISC = 'Misc'

            
    def __init__(self, node, session=None):
        self.node = node
        self.session = session
        self.tags = []
        self.category = self.UNKNOWN

        # Collect object categories so we don't need to fetch them later
        if not self.nx_object_categories:
            self.__class__.nx_object_categories = {
                nxc.getName().lower(): nxc.getId()
                for nxc in session.getObjectCategories()
            }

    def evaluate(self):
        self.category = self.get_category_name()

    def nx_update_custom_attr(self):
        ''' Check _categoryName on node, if it is not set to the current value (or missing) update it '''

        required_attrs = {
            '_categoryName': self.category,
            'disableUnreachableAlarms': str(int(self.category in (self.WORKSTATION, self.PORTABLE, self.PRINTER))),
            'disableInterfaceAlarms': str(int(self.category in (self.WORKSTATION, self.PORTABLE, self.PRINTER)))
        }

        for attr in required_attrs:
            ca = self.node.customAttributes.get(attr, None)
            if ca and ca.value == required_attrs[attr]:
                del required_attrs[attr]
        
        if required_attrs:
            md = NXCObjectModificationData(self.node.getObjectId())
            attr_map = HashMap(self.node.getCustomAttributes())
            flags = CustomAttribute.INHERITABLE
            for attr in required_attrs:
                attr_map.put(attr, CustomAttribute(str(required_attrs[attr]), flags, 0))
            md.setCustomAttributes(attr_map)
            self.session.modifyObject(md)

    def nx_update_obj_category(self):
        ''' Here I am using the object categories I have created using create-object-categories.py
        to set the object category, but I also use an NXSL Script to change these between grey/green
        depending on need '''
        use_category_grey = self.nx_object_categories.get(self.category.lower() + ".grey", 0)
        use_category_green = self.nx_object_categories.get(self.category.lower() + ".green", 0)
        use_category_other = self.nx_object_categories.get(self.category.lower(), 0)
        if use_category_green and use_category_grey:
            if self.node.categoryId not in (use_category_green, use_category_grey):
                md = NXCObjectModificationData(self.node.getObjectId())
                md.setCategoryId(use_category_grey)
                self.session.modifyObject(md)
        elif use_category_other:
            if self.node.categoryId != use_category_other:
                md = NXCObjectModificationData(self.node.getObjectId())
                md.setCategoryId(use_category_other)
                self.session.modifyObject(md)

    def has_tag(self, tag):
        return tag in self.tags

    def add_tag(self, tag):
        if self.has_tag(tag):
            self.tags.append(tag)
        self.__class__._instances.append(self)

    def save_to_file(self):
        save_dir = 'data/nodes'
        if os.path.exists(save_dir):
            save_file = os.path.join(save_dir, 'node_%s.txt' % self.node.getObjectId())
            fh = open(save_file, 'w')
            fh.write('result _categoryName = %s\n' % self.category)
            
            for key in self.node.customAttributes:
                fh.write('node.customAttribute.%s = %s\n' % (key, self.node.customAttributes[key].value))

            fh.write('node.objectName = %s\n' % self.node.getObjectName())
            for attr in dir(self.node):
                if (
                    (attr.startswith('hardware') and attr != 'hardwareId') or
                    (attr.startswith('snmpSys') or attr == 'snmpOID') or
                    attr.startswith('system') or
                    attr == 'nodeType' or attr == 'nodeSubType' or
                    attr in ('wirelessController', 'primaryMAC', 'platformName')
                ):
                    fh.write('node.%s = %s\n' % (attr, getattr(self.node, attr)))
            fh.close()

    def id_watchguard_firewall(self):
        descr = self.node.systemDescription
        if descr and descr.startswith('FireboxCloud-') or re.match('(T[12345][05](-W|)|M(2\d\d|5\d\d))', descr):
            return self.UTM_DEVICE
        if str(self.node.snmpOID) in ('.1.3.6.1.4.1.3097.1.5.78', '.1.3.6.1.4.1.3097.1.5.72'):
            return self.UTM_DEVICE

    def id_printer(self):
        printer_strings = [
            'DocuPrint',
            'Fuji Xerox',
            'Zebra Wired',
            'Ricoh',
            'Toshiba e-Studio',
            'Epson',
            'Samsung SL',
            'Kyocera'
        ]
        if in_list_upper(self.node.systemDescription, printer_strings): return self.PRINTER
        if in_list_upper(self.node.snmpSysName, printer_strings): return self.PRINTER
        if str(self.node.primaryMAC).startswith('00:80:77:'): return self.PRINTER # Brother

    def id_portables(self):
        if self.node.hardwareVendor.startswith('Microsoft') and self.node.hardwareProductName.startswith('Surface'): return self.PORTABLE
        if 'HP ProBook' in self.node.hardwareProductName: return self.PORTABLE
        if 'VivoBook' in self.node.hardwareProductName: return self.PORTABLE
        if 'Laptop' in self.node.hardwareProductName: return self.PORTABLE
        if 'ZBook' in self.node.hardwareProductName: return self.PORTABLE

    def id_workstations(self):
        if str(self.node.nodeType) == 'PHYSICAL' and self.node.platformName.startswith('windows'): return self.WORKSTATION
        if 'Windows 10' in self.node.systemDescription: return self.WORKSTATION
        if 'Windows 7' in self.node.systemDescription: return self.WORKSTATION
        if 'Windows 8' in self.node.systemDescription: return self.WORKSTATION
        if 'Windows 8.1' in self.node.systemDescription: return self.WORKSTATION

    def id_servers(self):
        if self.node.hardwareProductName == 'Virtual Machine': return self.SERVER
        if self.node.hardwareProductName == 'HVM domU': return self.SERVER
        if 'Windows Server' in self.node.systemDescription: return self.SERVER
        if 'linux' in self.node.systemDescription.lower(): return self.SERVER
        if str(self.node.platformName).lower().startswith('linux'): return self.SERVER

    def id_network_storage(self):
        if str(self.node.primaryMAC).startswith('00:11:32:'): return self.NETWORK_STORAGE # Synology
        if str(self.node.primaryMAC).startswith('1C:34:DA:'): return self.NETWORK_STORAGE # Synology

    def id_switches(self):
        if self.node.hardwareProductName.startswith('UBNT-ES'): return self.SWITCH
        if self.node.systemDescription.startswith('UAP-'): return self.SWITCH

    def id_overrides(self):
        if 'categoryName' in self.node.customAttributes:
            return self.node.customAttributes['categoryName'].value
        if 'isServer' in self.node.customAttributes:
            if str(self.node.customAttributes['isServer'].value) == '1':
                return self.SERVER

    def get_category_name(self):
        funcs = [
            self.id_watchguard_firewall,
            self.id_overrides,
            self.id_servers,
            self.id_network_storage,
            self.id_portables,
            self.id_printer,
            self.id_network_storage,
            self.id_workstations,
            self.id_switches
        ]

        fh = None
        if os.path.exists('data/nodes'):
            fh = open('data/nodes/funclog.txt', 'w')
        for func in funcs:
            func_result = func()
            if fh:
                fh.write('[%s] %s returned %s\n' % (self.node.getObjectName(), func, func_result))
            if func_result:
                return func_result
        if fh:
            fh.close()

        return self.OTHER


nodes = [o for o in s.getAllObjects() if isinstance(o, objects.Node)]
for node in nodes:
    ident = NodeIdentification(node, session)
    ident.evaluate()
    ident.save_to_file()
    ident.nx_update_custom_attr()
    ident.nx_update_obj_category()

session.syncObjects()
session.disconnect()
