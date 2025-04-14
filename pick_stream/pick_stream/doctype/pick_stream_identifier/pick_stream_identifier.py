# Copyright (c) 2025, Jollys Pharmacy Limited and contributors
# For license information, please see license.txt

import random

import frappe
from frappe.model.document import Document

from pick_stream.core import get_pick_stream_settings

class PickStreamIdentifier(Document):
    def autoname(self):
        prefix = self.get_prefix()
        unique_id = str(random.randint(00000000, 99999999))
        name = f'{prefix}{unique_id}'
        if not self.validate_name(name):
            raise frappe.exceptions.DuplicateEntryError(f"Identifier '{name}' is already used. Contact IT.")
        self.name = name

    def validate_name(self, name):
        if frappe.db.exists('Pick Stream Identifier', name):
            return False
        return True
        
    def get_prefix(self):
        settings = get_pick_stream_settings()
        matching_item = next((item for item in settings.item_types if item.item_type == self.item_type), None)
        if not matching_item:
            raise frappe.exceptions.ValidationError(f"Item type '{self.item_type}' not in valid item types. Contact IT.")
        return matching_item.prefix