// Copyright (c) 2025, Jollys Pharmacy Limited and contributors
// For license information, please see license.txt

frappe.listview_settings['Crate'] = {
    hide_name_column: true,
    get_indicator: function(doc) {
		const status_colors = {
			'Available': 'grey',
			'Picking': 'orange',
            'Waiting': 'grey',
			'In Transit': 'yellow',
			'Verifying': 'purple'
		};
		return [__(doc.status), status_colors[doc.status], 'status,=,'+doc.status];
	},
    onload: function(listview) {
        $('.sidebar-toggle-btn').hide();
        $('.col-lg-2.layout-side-section').hide();
    }
}

function extend_listview_event(doctype, event, callback) {
    if (!frappe.listview_settings[doctype]) {
        frappe.listview_settings[doctype] = {};
    }
    const old_event = frappe.listview_settings[doctype][event];
    frappe.listview_settings[doctype][event] = function (listview) {
        if (old_event) {
            old_event(listview);
        }
        callback(listview);
    };
}

extend_listview_event("Crate", "refresh", function (listview) {
    $(document).ready(function() {
        $('span[data-filter="color,=,Red"]').each(function() {
            $(this).removeClass('gray').addClass('red');
        });
    });
    $(document).ready(function() {
        $('span[data-filter="color,=,Green"]').each(function() {
            $(this).removeClass('gray').addClass('green');
        });
    });
    $(document).ready(function() {
        $('span[data-filter="color,=,Yellow"]').each(function() {
            $(this).removeClass('gray').addClass('yellow');
        });
    });
    $(document).ready(function() {
        $('span[data-filter="color,=,Blue"]').each(function() {
            $(this).removeClass('gray').addClass('blue');
        });
    });
});