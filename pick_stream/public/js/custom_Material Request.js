frappe.ui.form.on('Material Request', {
    before_submit: function(frm) {
        return new Promise((resolve) => {
            // Determine branch based on warehouse
            const warehouse = frm.doc.set_from_warehouse;
            let branch = 'King George';  // Default
            
            if (warehouse === 'KG Warehouse - JP') {
                branch = 'King George';
            } else if (warehouse === 'JP Mega - JP') {
                branch = 'JP Mega';
            }

            frappe.confirm(
                __(`Assign this Material Request to Warehouse Staff at ${branch}?`),
                () => { // Yes
                    frm.set_value('custom_assign_warehouse_staff', 1);
                    resolve();
                },
                () => { // No
                    frm.set_value('custom_assign_warehouse_staff', 0);
                    resolve();
                }
            );
        });
    }
});