# Copyright (c) 2025, Jollys Pharmacy Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from pick_stream.api import update_crate

class Stream(Document):
    def after_insert(self):
        update_crate(stream=self.name, is_insert=True)

    def validate(self):
        self.update_status(self.status)
        self.update_crate_status()

    def update_status(self, status:str):
        self.db_set("status", status)

    def update_crate_status(self):
        if self.status == "Waiting":
            update_crate(stream=self.name, is_waiting=True)

        elif self.status == "In Transit":
            update_crate(stream=self.name, is_transit=True)

        elif self.status == "Verifying":
            update_crate(stream=self.name, is_verifying=True)

        elif self.status == "Completed":
            update_crate(stream=self.name, is_clear=True)

        else:
            update_crate(stream=self.name, is_update=True)
