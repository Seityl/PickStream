# Copyright (c) 2025, Jollys Pharmacy Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

import pick_stream.exceptions
from pick_stream.core import crate_is_closed

class Stream(Document):
    def on_update(self):
        self.update_crate()

    def update_crate(self):
        crate = frappe.get_doc('Crate', self.crate_code)
        self.validate_crate(crate)
        status = get_updated_crate_status(self.crate_code, self.user)
        
        crate.update({
            'status': status,
            'picking_user': self.user,
            'from_warehouse': self.from_warehouse,
            'to_warehouse': self.to_warehouse,
        })

        if self.item_group not in [row.item_group for row in crate.item_groups]:
            crate.append('item_groups', {'item_group': self.item_group})

        if self.name not in [row.stream for row in crate.streams]:
            crate.append('streams', {'stream': self.name})

        crate.items = [item for item in crate.items if item.stream != self.name]

        for stream_item in self.items:
            crate.append('items', {
                'item_code': stream_item.item_code,
                'item_name': stream_item.item_name,
                'item_group': stream_item.item_group,
                'description': stream_item.description,
                'from_warehouse': stream_item.from_warehouse,
                'to_warehouse': stream_item.to_warehouse,
                'uom': stream_item.uom,
                'conversion_factor': stream_item.conversion_factor,
                'requested_qty': stream_item.requested_qty,
                'scanned_qty': stream_item.scanned_qty,
                'scanned': stream_item.scanned,
                'stream': self.name,
                'material_request': stream_item.material_request,
                'material_request_item': stream_item.material_request_item
            })

        try:
            crate.save(ignore_permissions=True)
            frappe.db.commit()

        except Exception as e:
            frappe.db.rollback()
            raise pick_stream.exceptions.ValidationError(f'Failed to update crate {self.crate_code}. {str(e)}')
    
    def validate_crate(self, crate):
        if crate.from_warehouse and crate.from_warehouse != self.from_warehouse:
            raise pick_stream.exceptions.ValidationError(
                f'Crate {self.crate_code} already sourced from warehouse {crate.from_warehouse}. '
                f'Cannot move from {self.from_warehouse}.'
            )

        if crate.to_warehouse and crate.to_warehouse != self.to_warehouse:
            raise pick_stream.exceptions.ValidationError(
                f'Crate {self.crate_code} already destined for warehouse {crate.to_warehouse}. '
                f'Cannot redirect to {self.to_warehouse}.'
            )

# A lot to be done here 20/05/2025
def get_updated_crate_status(crate_code:str, user:str) -> str:
    if crate_is_closed(crate_code, user):
        return 'Waiting'
    return 'Picking'