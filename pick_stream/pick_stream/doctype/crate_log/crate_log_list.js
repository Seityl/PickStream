frappe.listview_settings['Crate Log'] = {
    hide_name_column: true,
    refresh: function (listview) {
        $('div[data-fieldname = name]').hide();
    }
}