import wrapt
import frappe
import traceback
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Union


def generate_response(
    status: int,
    message: Union[str, Exception],
    data: Optional[Union[List, Dict]] = None
) -> Dict:
    """Generate consistent API response format"""
    response = frappe._dict({
        'status': status,
        'data': data if data is not None else []
    })
    frappe.response['http_status_code'] = status
    if message:
        if isinstance(message, Exception):
            error = frappe._dict({
                'error_type': str(type(message).__name__),
                'error_message': str(message)
            })
            response.error = error
        else:
            sanitized_message = BeautifulSoup(
                message,
                'html.parser'
            ).get_text()
            response.message = sanitized_message
    return response


def exception_handler(e: Exception) -> None:
    exception_name = type(e).__name__
    tb = traceback.extract_tb(e.__traceback__)
    location = 'Unknown location'
    for trace in reversed(tb):
        filename = trace.filename
        parts = filename.split('pick_stream', 2)
        if len(parts) >= 3:
            trimmed_path = 'pick_stream' + parts[2]
            location = f'{trimmed_path} in {trace.name}'
            break
    log_title = f'{exception_name} at {location}'
    request_data = {}
    if hasattr(frappe.local, 'request'):
        request = frappe.local.request
        request_data = {
            'method': request.method,
            'path': request.path,
            'headers': dict(request.headers),
            'args': dict(request.args),
            'form': dict(request.form),
            'json': request.get_json(silent=True),
        }
    error_message = f'{frappe.get_traceback()}\n\n--- Request Data ---\n{frappe.as_json(request_data, indent=2)}'
    frappe.log_error(
        title=log_title,
        message=error_message
    )
    status_code = getattr(e, 'http_status_code', 500)
    return generate_response(status_code, e)


def handler(methods: List[str]):
    """Decorator to validate HTTP method and handle exceptions"""
    allowed_methods = set(methods)
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        try:
            if frappe.local.request.method not in allowed_methods:
                return generate_response(405, 'Method Not Allowed')
            return wrapped(*args, **kwargs)
        except Exception as e:
            return exception_handler(e)
    return wrapper