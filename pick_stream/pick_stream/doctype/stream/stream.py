# Copyright (c) 2025, Jollys Pharmacy Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document
# from pick_stream.api import update_crate

class Stream(Document):
    pass
    # def on_update(self):
    #     update_crate(self)

    def validate(self):
        self.update_status(self.status)

    def update_status(self, status:str):
        self.db_set("status", status)