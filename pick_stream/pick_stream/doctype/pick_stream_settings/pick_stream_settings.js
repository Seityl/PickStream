// Copyright (c) 2025, Jollys Pharmacy Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pick Stream Settings', {
	refresh: function(frm) {
        frm.set_query('warehouse', 'warehouse_group_map', function() {
			return {
				filters: {
					is_group: 1
				}
			};
		});
		frm.set_query('picking_warehouse_1', 'workflow_settings', function() {
			return {
				filters: {
					is_group: 1
				}
			};
		});
		
		frm.set_query('picking_warehouse_2', 'workflow_settings', function() {
			return {
				filters: {
					is_group: 1
				}
			};
		});
		
		frm.set_query('picking_warehouse_3', 'workflow_settings', function() {
			return {
				filters: {
					is_group: 1
				}
			};
		});
		frm.set_query('target_warehouse', 'workflow_settings', function() {
			return {
				filters: {
					is_group: 0
				}
			};
		});
	},
});

frappe.ui.form.on('Pick Stream Workflow', {
	target_warehouse: function(frm, cdt, cdn) {
		validate_workflow_uniqueness(frm, cdt, cdn);
	},
	
	transit_after_verification: function(frm, cdt, cdn) {
		validate_workflow_flags(frm, cdt, cdn);
	},
	
	receiving_after_verification: function(frm, cdt, cdn) {
		validate_workflow_flags(frm, cdt, cdn);
	},
	
	verification_after_receiving: function(frm, cdt, cdn) {
		validate_workflow_flags(frm, cdt, cdn);
	},

	picking_warehouse_1: function(frm, cdt, cdn) {
		validate_warehouse_branch_match(frm, cdt, cdn, 'picking_warehouse_1', 'picking_user_branch_1');
	},
	
	picking_warehouse_2: function(frm, cdt, cdn) {
		validate_warehouse_branch_match(frm, cdt, cdn, 'picking_warehouse_2', 'picking_user_branch_2');
	},
	
	picking_warehouse_3: function(frm, cdt, cdn) {
		validate_warehouse_branch_match(frm, cdt, cdn, 'picking_warehouse_3', 'picking_user_branch_3');
	}
});

function validate_workflow_uniqueness(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let workflows = frm.doc.workflow_settings || [];
	let duplicates = workflows.filter(w => 
		w.target_warehouse === row.target_warehouse && 
		w.name !== row.name &&
		w.is_active
	);
	
	if (duplicates.length > 0) {
		frappe.msgprint({
			title: __('Duplicate Workflow'),
			message: __('An active workflow already exists for warehouse: {0}', [row.target_warehouse]),
			indicator: 'red'
		});
		frappe.model.set_value(cdt, cdn, 'target_warehouse', '');
	}
}

function validate_workflow_flags(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	
	if (row.transit_after_verification && row.receiving_after_verification) {
		frappe.msgprint({
			title: __('Invalid Configuration'),
			message: __('Cannot enable both "Transit After Verification" and "Receiving After Verification" simultaneously'),
			indicator: 'red'
		});
		frappe.model.set_value(cdt, cdn, 'receiving_after_verification', 0);
		frappe.model.set_value(cdt, cdn, 'transit_after_verification', 0);
	}
	
	if (row.verification_after_receiving && (row.transit_after_verification || row.receiving_after_verification)) {
		frappe.msgprint({
			title: __('Invalid Configuration'),
			message: __('Cannot enable "Transit After Verification" or "Receiving After Verification" simultaneously when "Verification After Receiving" is enabled.'),
			indicator: 'yellow'
		});
		frappe.model.set_value(cdt, cdn, 'verification_after_receiving', 0);
		frappe.model.set_value(cdt, cdn, 'receiving_after_verification', 0);
		frappe.model.set_value(cdt, cdn, 'transit_after_verification', 0);
	}
}

function validate_warehouse_branch_match(frm, cdt, cdn, warehouse_field, branch_field) {
	let row = locals[cdt][cdn];
	let warehouse = row[warehouse_field];
	
	if (!warehouse) {
		frappe.model.set_value(cdt, cdn, branch_field, '');
		return;
	}
	
	let warehouse_maps = frm.doc.warehouse_group_map || [];
	let matching_map = warehouse_maps.find(map => {
		return frappe.db.get_value('Warehouse', warehouse, 'parent_warehouse')
			.then(r => r.message && r.message.parent_warehouse === map.warehouse);
	});
	
	if (matching_map && !row[branch_field]) {
		frappe.model.set_value(cdt, cdn, branch_field, matching_map.branch);
		frappe.show_alert({
			message: __('Auto-selected branch: {0}', [matching_map.branch]),
			indicator: 'green'
		});
	}
}