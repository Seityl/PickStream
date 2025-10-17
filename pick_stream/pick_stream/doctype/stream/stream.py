# Copyright (c) 2025, Jollys Pharmacy Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document

from pick_stream import exceptions


class Stream(Document):
    def before_save(self):
        self.update_previous_status()

    def on_update(self):
        self.update_crate()

    def update_previous_status(self):
        self.previous_status = frappe.db.get_value(
            self.doctype, self.name, 'status'
        )

    def update_crate(self):
        # Load crate with FOR UPDATE lock to prevent race conditions
        crate = frappe.get_doc('Crate', self.crate_code, for_update=True)
        # Validate warehouse consistency
        self.validate_crate(crate)
        # Calculate aggregate status from ALL streams
        aggregated_status = self.calculate_aggregate_crate_status()
        crate.update({
            'status': aggregated_status,
            'from_warehouse': self.from_warehouse,
            'to_warehouse': self.to_warehouse,
        })
        # Add item_group if not present
        if self.item_group not in [row.item_group for row in crate.item_groups]:
            crate.append('item_groups', {'item_group': self.item_group})
        # Add this stream if not present
        if self.name not in [row.stream for row in crate.streams]:
            crate.append('streams', {'stream': self.name})
        # Update items for this stream (remove old, add new)
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
                'source': stream_item.source,
                'material_request': stream_item.material_request,
                'material_request_item': stream_item.material_request_item
            })
        try:
            crate.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            raise exceptions.SystemError(
                f'Failed to update crate {self.crate_code}. {str(e)}'
            )    

    def validate_crate(self, crate):
        """
        Validate that the crate's warehouses are consistent with this stream.
        Once a crate has warehouses set, all streams must match.
        """
        if crate.from_warehouse and crate.from_warehouse != self.from_warehouse:
            raise exceptions.ValidationError(
                f'Crate {self.crate_code} is already sourced from '
                f'{crate.from_warehouse}. Cannot move from {self.from_warehouse}.'
            )
        if crate.to_warehouse and crate.to_warehouse != self.to_warehouse:
            raise exceptions.ValidationError(
                f'Crate {self.crate_code} is already destined for '
                f'{crate.to_warehouse}. Cannot redirect to {self.to_warehouse}.'
            )

    def calculate_aggregate_crate_status(self):
        """
        Calculate the crate status by aggregating ALL streams in the crate.
        
        The crate status should reflect the LEAST progressed stream, since
        the crate cannot proceed until ALL streams complete each stage.
        
        Status hierarchy (least to most progressed):
          Picking < Waiting < Verified < In Transit < Received < Completed
        
        Returns:
            str: The aggregated crate status
        """
        # Get all streams for this crate
        all_streams = frappe.get_all(
            'Stream',
            filters={'crate_code': self.crate_code},
            fields=['name', 'status'],
            order_by='modified desc'
        )
        if not all_streams:
            # No streams yet - should not happen, but default to Picking
            return 'Picking'
        # Define status priority (lower number = less progressed)
        status_priority = {
            'Picking': 1,
            'Waiting': 2,
            'Verified': 3,
            'In Transit': 4,
            'Received': 5,
            'Completed': 6
        }
        # Find the minimum (least progressed) status
        min_priority = min(
            status_priority.get(stream.status, 1) 
            for stream in all_streams
        )
        # Map back to status name
        for status_name, priority in status_priority.items():
            if priority == min_priority:
                least_progressed_status = status_name
                break
        # Map Stream status to Crate status
        return self.map_stream_status_to_crate_status(least_progressed_status)
    
    def map_stream_status_to_crate_status(self, stream_status):
        """
        Map Stream status to Crate status.
        
        The key difference is that Stream has "Completed" while
        Crate has "Available".
        
        Args:
            stream_status: The stream's current status
            
        Returns:
            str: The corresponding crate status
        """
        status_mapping = {
            'Picking': 'Picking',
            'Waiting': 'Waiting', 
            'Verified': 'Verified',
            'In Transit': 'In Transit',
            'Received': 'Received',
            'Completed': 'Available'
        }
        return status_mapping.get(stream_status, 'Picking')