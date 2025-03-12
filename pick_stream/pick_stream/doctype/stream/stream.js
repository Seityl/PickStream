// Copyright (c) 2025, Jollys Pharmacy Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stream", {
	onload: function(frm) {
        // Hides Add Row button from items child table
        frm.get_field('items').grid.cannot_add_rows = true;
        // Hides Delete button from items child table
        frm.set_df_property('items', 'cannot_delete_rows', 1);
    },
    refresh: function(frm) {
        frm.disable_save();
        $('.row-check').hide();
    }
})
