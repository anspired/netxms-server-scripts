#!/usr/bin/env nxpython

from org.netxms.client import NXCObjectModificationData, NXCObjectCreationData

# Dump the existing category name, category IDs
existing_categories = {c.getName(): c.getId() for c in session.getObjectCategories()}
images = []

# Grab our image library, create a list of guid/names for everything under "Downloaded Icons"
for img in session.getImageLibrary():
    if img.getCategory() == 'Downloaded Icons':
        images.append((img.guid, img.name))

# For every image available, make sure we have a category
for img_guid, img_name in images:
    moc = MutableObjectCategory(img_name, img_guid, img_guid)
    if img_name not in existing_categories:
        category_id = session.modifyObjectCategory(moc)
        existing_categories[img_name] = category_id
        print category_id, moc

session.syncObjects()
session.disconnect()
