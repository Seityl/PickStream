# Copyright (c) 2025, Jollys Pharmacy Limited and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document

from pick_stream.core import create_crate_log, update_crate_log, get_pick_stream_settings

class Crate(Document):
    def autoname(self):
        self.name = self.get_crate_code()
        
    def validate(self):
        if not self.is_new():        
            if not frappe.db.exists('Crate Log', {'stream': self.stream}):
                return create_crate_log(self)
            else:
                return update_crate_log(self)
        
    def get_crate_code(self):
        color_range = self.get_color_range_and_prefix()
        start_number = color_range.start_number
        end_number = color_range.end_number
        prefix = color_range.prefix

        last_crate = frappe.db.get_value('Crate', {'color': self.color}, 'name', order_by = 'creation DESC')
        print('last_crate', last_crate)
        if last_crate:
            match = re.search(r'\d+', last_crate)
            last_number = int(match.group())
        else:
            last_number = start_number - 1

        next_number = last_number + 1
        if next_number > end_number:
            frappe.throw('Crate code limit reached for this color range')
        
        return f'{prefix}{str(next_number).zfill(4)}'  

    def get_color_range_and_prefix(self):
        settings = get_pick_stream_settings()
        for row in settings.crate_settings:
            if row.color == self.color:
                return frappe._dict({
                    'start_number': row.start_number,
                    'end_number': row.end_number,
                    'prefix': row.prefix
                })