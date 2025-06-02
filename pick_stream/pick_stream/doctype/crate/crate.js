// Copyright (c) 2025, Jollys Pharmacy Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Crate", {
    onload: function(frm) {
        frm.get_field('items').grid.cannot_add_rows = true;
        frm.set_df_property('items', 'cannot_delete_rows', 1);
    },
    
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            frm.disable_save();
            frm.add_custom_button('Print Label', async function() {
                try {
                    const printerResponse = await frappe.call({
                        method: 'pick_stream.api.get_printer_list_view',
                        freeze: true,
                        freeze_message: 'Fetching available printers...'
                    });

                    if (!printerResponse.message || !printerResponse.message.data || printerResponse.message.data.length === 0) {
                        frappe.msgprint({
                            title: 'No Printers Available',
                            indicator: 'red',
                            message: 'No printers found. Conatct IT.'
                        });
                        return;
                    }

                    const printers = printerResponse.message.data;

                    const fields = [
                        {
                            fieldtype: 'Select',
                            label: 'Select Printer',
                            fieldname: 'printer',
                            options: printers.map(p => ({
                                label: p,
                                value: p
                            })),
                            default: printers[0], // Default to first printer
                            reqd: 1
                        },
                        {
                            fieldtype: 'Int',
                            label: 'Number of Labels',
                            fieldname: 'qty',
                            default: 1,
                            min: 1,
                            max: 100,
                            reqd: 1
                        }
                    ];

                    frappe.prompt(fields, (values) => {
                        frappe.call({
                            method: 'pick_stream.api.submit_print_request',
                            args: {
                                crate_code: frm.doc.name,
                                qty: values.qty,
                                printer: values.printer
                            },
                            callback: (r) => {
                                if (r.exc) {
                                    frappe.msgprint({
                                        title: 'Print Error',
                                        indicator: 'red',
                                        message: `Failed to print label: ${r.exc}`
                                    });
                                } else {
                                    frappe.show_alert({
                                        message: `Successfully printed ${values.qty} label(s) to ${values.printer}`, 
                                        indicator: 'green'
                                    }, 5);
                                }
                            },
                            freeze: true,
                            freeze_message: 'Printing label(s)...'
                        });
                    }, 'Print Crate Label', 'Print');

                } catch (error) {
                    frappe.msgprint({
                        title: 'Error',
                        indicator: 'red',
                        message: `An error occurred: ${error.message}`
                    });
                }
            });
        }
        $('.row-check').hide();
    }
});