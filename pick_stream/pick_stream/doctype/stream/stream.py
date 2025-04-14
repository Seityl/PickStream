# Copyright (c) 2025, Jollys Pharmacy Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from pick_stream.core import update_crate

class Stream(Document):
    def on_update(self):
        if self.is_new():
            return update_crate(self)