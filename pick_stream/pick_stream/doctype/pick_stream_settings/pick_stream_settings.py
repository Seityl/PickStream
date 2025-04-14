# Copyright (c) 2025, Jollys Pharmacy Limited and contributors
# For license information, please see license.txt

from frappe.model.document import Document

class PickStreamSettings(Document):
    def validate(self):
        for row in self.item_types:
            row.item_type = str(row.item_type).lower()
            row.prefix = str(row.prefix).upper()
        for row in self.crate_settings:
            row.color = str(row.color).capitalize()
            row.prefix = str(row.prefix).upper()