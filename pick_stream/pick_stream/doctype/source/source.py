# Copyright (c) 2025, Jollys Pharmacy Limited and contributors
# For license information, please see license.txt

from collections import OrderedDict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.nestedset import get_descendants_of
from frappe.utils import cint, flt, floor, get_link_to_form

import pick_stream
from pick_stream.core import get_pick_stream_settings, create_stream, update_stream

class Source(Document):
    def before_save(self):
        self.set_item_locations()

    def validate(self):
        self.validate_scanned_qty()
        self.validate_stock_qty()
        self.update_streams()

    def on_update(self):
        if self.is_completed():
            self.db_set('status', 'Completed')
            self.update_linked_streams_status()
            
    def is_completed(self):
        return all(item.scanned or item.skipped for item in self.items)

    def update_linked_streams_status(self):
        """Update all linked streams to 'Waiting' status after completion of source"""
        streams = frappe.db.get_list('Stream',
            filters={'source': self.name},
            fields=['name']
        )
        for stream in streams:
            stream = frappe.get_doc('Stream', stream.name)
            if stream.status != 'Completed':
                stream.db_set('status', 'Waiting')
            
        frappe.db.commit()

    def update_streams(self):
        crates_status = self.get_crates_status()
        
        if not crates_status:
            return

        for crate_code, is_closed in crates_status.items():
            stream_name = frappe.db.get_value(
                'Stream', 
                {
                    'crate_code': crate_code,
                    'source': self.name
                }, 
                'name'
            )
            status = 'Waiting' if is_closed else None
            if not stream_name:
                stream_name = create_stream(self, crate_code)
                update_stream(self, stream_name, status)
            else:
                update_stream(self, stream_name, status)

    def get_crates_status(self):
        """Returns {crate_code: True only if all items for crate are closed}"""
        crates_status = frappe._dict()
        
        for row in self.item_crates:
            if row.crate_code not in crates_status:
                crates_status[row.crate_code] = True
            
            if not row.crate_closed:
                crates_status[row.crate_code] = False
        
        return crates_status
    
    def validate_stock_qty(self):
        for row in self.items:
            if not row.scanned_qty:
                continue

            bin_qty = frappe.db.get_value('Bin', {'item_code': row.item_code, 'warehouse': row.from_warehouse}, 'actual_qty')

            if row.available_qty != flt(bin_qty):
                row.available_qty = flt(bin_qty)

            if row.available_qty > flt(bin_qty):
                raise pick_stream.exceptions.ValidationError(f'Scanned qty {row.scanned_qty} exceeds available qty {bin_qty} for item {row.item_code}')

    def validate_scanned_qty(self):
        item_qty_map = {}
        
        for crate in self.item_crates:
            if crate.item_code in item_qty_map:
                item_qty_map[crate.item_code] += crate.qty
            else:
                item_qty_map[crate.item_code] = crate.qty
        
        for row in self.items:
            row.scanned_qty = item_qty_map.get(row.item_code, 0)
            
            if not row.scanned_qty:
                continue
                
            if row.scanned_qty <= 0:
                raise pick_stream.exceptions.ValidationError(
                    f'Scanned qty {row.scanned_qty} cannot be less than or equal to 0 for item {row.item_code}'
                )
                
            if row.scanned_qty > row.requested_qty:
                raise pick_stream.exceptions.ValidationError(
                    f'Scanned qty {row.scanned_qty} exceeds requested qty {row.requested_qty} for item {row.item_code}'
                )          
            
    def set_item_locations(self):
        items = self.aggregate_item_qty()
        scanned_items_details = self.get_scanned_items_details(items)

        settings = get_pick_stream_settings()
        # Set default source warehouse if none is set on Material Request
        default_set_from_warehouse = settings.default_set_from_warehouse
        set_from_warehouse = frappe.db.get_value('Material Request', self.material_request, 'set_from_warehouse')
        from_warehouses = [set_from_warehouse] if set_from_warehouse else [default_set_from_warehouse]
        from_warehouses.extend(get_descendants_of('Warehouse', from_warehouses))

        # Create replica before resetting, to handle empty table on update after submit.
        locations_replica = self.get('items')

        # Reset Items
        reset_rows = []
        for row in self.get('items'):
            if not row.scanned_qty:
                reset_rows.append(row)

        for row in reset_rows:
            self.remove(row)

        updated_locations = frappe._dict()
        self.item_location_map = frappe._dict()

        for item_doc in items:
            item_code = item_doc.item_code
            self.item_location_map.setdefault(
                item_code,
                get_available_item_locations(
                    item_code,
                    from_warehouses,
                    self.item_count_map.get(item_code),
                    scanned_item_details=scanned_items_details.get(item_code)
                )
            )

            locations = get_item_with_location_and_quantity(item_doc, self.item_location_map)

            item_doc.idx = None
            item_doc.name = None

            for row in locations:
                location = item_doc.as_dict()
                location.update(row)
                key = (
                    location.item_code,
                    location.warehouse,
                    location.uom,
                    location.material_request_item
                )

                if key not in updated_locations:
                    updated_locations.setdefault(key, location)
                else:
                    updated_locations[key].qty += location.qty

        sorted_locations = sorted(updated_locations.values(), key=lambda loc: loc.get('from_warehouse', ''))

        for location in sorted_locations:
            self.append('items', location)

        # This is to avoid empty Sources on update after submit.
        if not self.get('items') and self.docstatus == 1:
            for location in locations_replica:
                location.requested_qty = 0
                location.scanned_qty = 0
                self.append('items', location)
            frappe.log_error(
                message=_(
                    'Please Restock Items and Update the Pick List to continue. To discontinue, cancel the Pick List.'
                ),
                title=_('[Pick Stream] Out of Stock')
            )

    def aggregate_item_qty(self):
        """Returns combined requested qty for items with same item_code, uom and to_warehouse"""
        items = self.items
        self.item_count_map = {}

        # Aggregate qty for same item
        item_map = OrderedDict()
        
        for item in items:
            if item.scanned_qty:
                continue
            
            if not cint(frappe.get_cached_value('Item', item.item_code, 'is_stock_item')):
                continue

            item_code = item.item_code
            material_request = item.material_request
            material_request_item = item.material_request_item

            key = (item_code, item.uom, item.to_warehouse, material_request, material_request_item)

            item.idx = None
            item.name = None

            if item_map.get(key):
                item_map[key].requested_qty += flt(item.requested_qty)
                
            else:
                item_map[key] = item

            # Maintain count of each item (useful to limit get query)
            self.item_count_map.setdefault(item_code, 0)
            self.item_count_map[item_code] += flt(item.requested_qty)

        return item_map.values()
        
    def get_scanned_items_details(self, items):
        """Returns combined scanned qty for items from other sources that have not been completed"""
        scanned_items = frappe._dict()

        if not items:
            return scanned_items

        items_data = self.get_source_items(items)

        for item_data in items_data:
            key = item_data.to_warehouse

            if item_data.item_code not in scanned_items:
                scanned_items[item_data.item_code] = {}

            if key not in scanned_items[item_data.item_code]:
                scanned_items[item_data.item_code][key] = frappe._dict({
                    'scanned_qty': 0,
                    'to_warehouse': key
                })

            scanned_items[item_data.item_code][key]['scanned_qty'] += flt(item_data.scanned_qty)

        self.update_scanned_item_from_current_source(scanned_items)
        
        return scanned_items

    def update_scanned_item_from_current_source(self, scanned_items):
        for row in self.items:
            if flt(row.scanned_qty) > 0:
                key = row.from_warehouse

                if row.item_code not in scanned_items:
                    scanned_items[row.item_code] = {}

                if key not in scanned_items[row.item_code]:
                    scanned_items[row.item_code][key] = frappe._dict(
                        {
                            "scanned_qty": 0,
                            "to_warehouse": key
                        }
                    )

                scanned_items[row.item_code][key]["scanned_qty"] += flt(row.scanned_qty)
                    
    def get_source_items(self, items):
        """Returns {item_code, to_warehouse, scanned_qty} of items from other sources that have not been completed"""
        source = frappe.qb.DocType('Source')
        source_item = frappe.qb.DocType('Source Item')
        query = (
            frappe.qb.from_(source)
            .inner_join(source_item)
            .on(source.name == source_item.parent)
            .select(
                source_item.item_code,
                source_item.to_warehouse,
                source_item.scanned_qty,
            )
            .where(
                (source_item.item_code.isin([x.item_code for x in items]))
                & (source.status != 'Completed')
                & (source_item.scanned_qty > 0)
                & (source.docstatus != 1)
                & (source.docstatus != 2)
            )
        )

        if self.name:
            query = query.where(source_item.parent != self.name)

        query = query.for_update()

        return query.run(as_dict=True)
    
def get_available_item_locations(item_code, from_warehouses, requested_qty, scanned_item_details=None):
    locations = []
    locations = get_available_item_locations_for_item(item_code, from_warehouses)

    if scanned_item_details:
        locations = filter_locations_by_scanned_items(locations, scanned_item_details)

    if locations:
        locations = get_locations_based_on_requested_qty(locations, requested_qty)

    validate_scanned_items(item_code, requested_qty, locations, scanned_item_details)

    return locations

def get_available_item_locations_for_item(item_code, from_warehouses):
    """Returns {warehouse, qty} for item based on the given warehouses that have stock"""
    bin = frappe.qb.DocType('Bin')
    query = (
        frappe.qb.from_(bin)
        .select(bin.warehouse, bin.actual_qty.as_('qty'))
        .where((bin.item_code == item_code) & (bin.actual_qty > 0))
        .orderby(bin.creation)
    )
    query = query.where(bin.warehouse.isin(from_warehouses))
    item_locations = query.run(as_dict=True)
    return item_locations

def filter_locations_by_scanned_items(locations, scanned_item_details) -> list[dict]:
	filterd_locations = []
	for row in locations:
		key = row.warehouse
		scanned_qty = scanned_item_details.get(key, {}).get('scanned_qty', 0)

		if not scanned_qty:
			filterd_locations.append(row)
			continue

		if scanned_qty >= row.qty:
			row.qty = 0

		else:
			row.qty -= scanned_qty
			scanned_item_details[key]['scanned_qty'] = 0.0

		if row.qty > 0:
			filterd_locations.append(row)

	return filterd_locations

def get_locations_based_on_requested_qty(locations, requested_qty):
	filtered_locations = []

	for location in locations:
		if location.qty >= requested_qty:
			location.qty = requested_qty
			filtered_locations.append(location)
			break

		requested_qty -= location.qty
		filtered_locations.append(location)

	return filtered_locations

def validate_scanned_items(item_code, requested_qty, locations, scanned_item_details=None):
	for location in list(locations):
		if location['qty'] < 0:
			locations.remove(location)

	total_qty_available = sum(location.get('qty') for location in locations)
	remaining_qty = requested_qty - total_qty_available

	if remaining_qty > 0:
		if scanned_item_details:
			frappe.log_error(
				message=_('{0} units of Item {1} is scanned already in another Source.').format(
					remaining_qty, get_link_to_form('Item', item_code)
				),
				title=_('[Pick Stream] Already Scanned'),
			)

		else:
			frappe.log_error(
				message=_('{0} units of Item {1} is not available in any of the warehouses.').format(
					remaining_qty, get_link_to_form('Item', item_code)
				),
				title=_('[Pick Stream] Insufficient Stock'),
			)
               
def get_item_with_location_and_quantity(item_doc, item_location_map):
	available_locations = item_location_map.get(item_doc.item_code)
	locations = []

	remaining_stock_qty = item_doc.requested_qty

	while remaining_stock_qty > 0 and available_locations:
		item_location = available_locations.pop(0)
		item_location = frappe._dict(item_location)

		original_qty = frappe.db.get_value('Bin', {
            'warehouse': item_location.warehouse,
            'item_code': item_doc.item_code
        }, ['actual_qty'])

		qty = remaining_stock_qty if item_location.qty >= remaining_stock_qty else item_location.qty
		uom_must_be_whole_number = frappe.get_cached_value('UOM', item_doc.uom, 'must_be_whole_number')

		if uom_must_be_whole_number:
			qty = floor(qty)

		locations.append(
			frappe._dict({
                'qty': qty,
                'from_warehouse': item_location.warehouse,
                'available_qty': original_qty
            })
		)

		remaining_stock_qty -= qty
		qty_diff = item_location.qty - qty

		# if extra quantity is available push current warehouse to available locations
		if qty_diff > 0:
			item_location.qty = qty_diff
			available_locations = [item_location, *available_locations]

	# update available locations for the item
	item_location_map[item_doc.item_code] = available_locations
	return locations