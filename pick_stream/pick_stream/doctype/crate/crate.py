# Copyright (c) 2025, Jollys Pharmacy Limited and contributors
# For license information, please see license.txt

import re
import random

import frappe
from frappe import _
from frappe.model.document import Document

import pick_stream

class Crate(Document):
    def autoname(self):
        self.name = self.get_crate_code()

    # def on_update(self):
    #     self.create_crate_log() or self.update_crate_log()
    

    def validate(self):
        self.validate_item_groups()
        self.validate_streams()
        # self.validate_items()
        self.validate_warehouse_logic()

    def validate_item_groups(self):
        if not self.item_groups:
            return
        
        seen_item_groups = set()
        for row in self.item_groups:
            if row.item_group in seen_item_groups:
                raise pick_stream.exceptions.ValidationError(f"Duplicate Item Group '{row.item_group}' found in row {row.idx}. Contact IT.")
    
            seen_item_groups.add(row.item_group)

    def validate_streams(self):
        if not self.streams:
            return
        
        seen_streams = set()
        for row in self.streams:
            if row.stream in seen_streams:
                raise pick_stream.exceptions.ValidationError(f"Duplicate Stream '{row.stream}' found in row {row.idx}. Each Stream can only be added once.")
        
            seen_streams.add(row.stream)

    def validate_items(self):
        if not self.items:
            return
        
        for row in self.items:
            if row.stream and self.streams:
                stream_exists = any(s.stream == row.stream for s in self.streams)
                if not stream_exists:
                    raise pick_stream.exceptions.ValidationError(f"Stream '{row.stream}' in item row {row.idx} is not present in the Streams table. Contact IT.")
            
            if row.item_group and self.item_groups:
                item_group_exists = any(ig.item_group == row.item_group for ig in self.item_groups)
                if not item_group_exists:
                    raise pick_stream.exceptions.ValidationError(f"Item Group '{row.item_group}' in item row {row.idx} is not present in the Item Groups table. Contact IT.")

    def validate_warehouse_logic(self):
        if self.from_warehouse and self.to_warehouse and self.from_warehouse == self.to_warehouse:
            raise pick_stream.exceptions.ValidationError("From Warehouse and To Warehouse cannot be the same")
        
        if self.items:
            child_warehouses = pick_stream.utils.get_child_warehouses(self.from_warehouse)
            for row in self.items:
                if self.from_warehouse and row.from_warehouse and row.from_warehouse not in child_warehouses:  
                    raise pick_stream.exceptions.ValidationError(f"Item's From Warehouse '{row.from_warehouse}' in row {row.idx} not under Crate's From Warehouse '{self.from_warehouse}'. Contact IT.")

                if self.to_warehouse and row.to_warehouse and row.to_warehouse != self.to_warehouse:
                    raise pick_stream.exceptions.ValidationError(f"Item's To Warehouse '{row.to_warehouse}' in row {row.idx} does not match Crate's To Warehouse '{self.to_warehouse}'. Contact IT.")

    def get_crate_code(self):
        color_range = self.get_color_range_and_prefix()
        if not color_range:
            frappe.throw(f'No crate settings found for color {self.color}')

        existing_crates = frappe.db.get_list('Crate', 
            filters={'color': self.color}, 
            fields=['name']
        )
        
        existing_numbers = set()
        for crate in existing_crates:
            match = re.search(r'\d+', crate.name)
            if match:
                existing_numbers.add(int(match.group()))
        
        available_numbers = []
        for num in range(color_range.start_number, color_range.end_number + 1):
            if num not in existing_numbers:
                available_numbers.append(num)
        
        if not available_numbers:
            frappe.throw('No available crate codes remaining for this color range')
        
        random_number = random.choice(available_numbers)
        
        return f'{color_range.prefix}{str(random_number).zfill(4)}'

    def get_color_range_and_prefix(self):
        settings = pick_stream.utils.get_settings()
        if not settings or not settings.crate_settings:
            frappe.throw('Crate settings not found in Pick Stream Settings')

        for row in settings.crate_settings:
            if row.color == self.color:
                return frappe._dict({
                    'start_number': row.start_number,
                    'end_number': row.end_number,
                    'prefix': row.prefix
                })

    def create_crate_log(self):
        if not self.streams:
            return

        if not frappe.db.exists('Streams', {
            'parent': self.name,
            'parenttype': 'Crate Log',
            'stream': ['in', {row.stream for row in self.streams}]
        }): 
            crate_log = frappe.new_doc('Crate Log')
            crate_log.update({
                'crate_code': self.name,
                'to_warehouse': self.to_warehouse,
                'from_warehouse': self.from_warehouse
            })

            for stream in self.streams:
                crate_log.append('streams', {'stream': stream})

            for item in self.items:
                crate_log.append('items', {
                    'item_code': item.item_code,
                    'item_name': item.item_name,
                    'item_group': item.item_group,
                    'description': item.description,
                    'from_warehouse': item.from_warehouse,
                    'to_warehouse': item.to_warehouse,
                    'uom': item.uom,
                    'conversion_factor': item.conversion_factor,
                    'requested_qty': item.requested_qty,
                    'scanned_qty': item.scanned_qty,
                    'scanned': item.scanned,
                    'crate_closed': item.crate_closed,
                    'crate_code': item.crate_code,
                    'material_request': item.material_request,
                    'material_request_item': item.material_request_item
                })
            try:
                crate_log.insert(ignore_permissions=True)
                frappe.db.commit()
                
            except Exception as e:
                raise pick_stream.exceptions.ValidationError(f'Error creating crate log: {e}')

            return crate_log

    def update_crate_log(self):
        if not self.streams:
            return

        # Should only update crate log when crate is not available
        if self.status == 'Available':
            return

        # TODO: This could throw unaccounted error
        if frappe.db.exists('Streams', {
            'parent': self.name,
            'parenttype': 'Crate Log',
            'stream': ['in', {row.stream for row in self.streams}]
        }):
            return 
            crate_log = frappe.get_doc('Crate Log', {'stream': self.stream})
            crate_log.update({
                'crate_code': self.name,
                'stream': self.stream,
                'to_warehouse': self.to_warehouse,
                'from_warehouse': self.from_warehouse,
                'picked_by': frappe.db.get_value('Stream', self.stream, 'user') or '',
                'items': []
            })

            for stream in self.streams:
                if stream not in crate_log.streams:
                    crate_log.append('streams', {'stream': stream})
                
            for item in self.items:
                crate_log.append('items', {
                    'item_code': item.item_code,
                    'item_name': item.item_name,
                    'item_group': item.item_group,
                    'description': item.description,
                    'from_warehouse': item.from_warehouse,
                    'to_warehouse': item.to_warehouse,
                    'uom': item.uom,
                    'conversion_factor': item.conversion_factor,
                    'requested_qty': item.requested_qty,
                    'scanned_qty': item.scanned_qty,
                    'scanned': item.scanned,
                    'crate_closed': item.crate_closed,
                    'crate_code': item.crate_code,
                    'stream': self.name,
                    'material_request': item.material_request,
                    'material_request_item': item.material_request_item
                })
            try:
                crate_log.save(ignore_permissions=True)
                frappe.db.commit()
                
            except Exception as e:
                raise pick_stream.exceptions.ValidationError(f'Error saving crate log: {e}')