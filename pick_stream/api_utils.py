import frappe
from frappe import _

import wrapt
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Union

def generate_response(
    status: int,
    message: Union[str, Exception],
    data: Optional[Union[List, Dict]] = None
) -> Dict:
    """Generate consistent API response format"""
    response = {
        "status": status,
        "data": data if data is not None else []
    }
    frappe.response["http_status_code"] = status

    if message:
        if isinstance(message, Exception):
            message_str = f"{type(message).__name__}: {message}"
            sanitized_message = BeautifulSoup(message_str, 'html.parser').get_text()
            response["error"] = {
                "status": status,
                "message": sanitized_message
            }
            frappe.response["error"] = response["error"]
        else:
            sanitized_message = BeautifulSoup(message, 'html.parser').get_text()
            response["message"] = sanitized_message
            frappe.response["message"] = sanitized_message

    return response

def exception_handler(e: Exception) -> None:
    """Global exception handler for API endpoints"""
    frappe.log_error(title="Pick Stream App Error", message=frappe.get_traceback())
    status_code = getattr(e, 'http_status_code', 500)
    frappe.clear_messages()
    return generate_response(status_code, e)

def generate_key(user: str) -> Dict[str, str]:
    """Generate or retrieve API keys for a user.
    
    Args:
        user (str): User ID to generate keys for
    """
    user_doc = frappe.get_doc('User', user)
    
    if not user_doc.api_key or not user_doc.api_secret:
        # Regenerate both keys if either is missing
        api_secret = frappe.generate_hash(length=15)
        api_key = frappe.generate_hash(length=15)
        
        user_doc.api_key = api_key
        user_doc.api_secret = api_secret
        user_doc.save(ignore_permissions=True)
    
    return {
        'api_secret': user_doc.get_password('api_secret'),
        'api_key': user_doc.get('api_key')
    }

def pick_stream_validate(methods: List[str]):
    """Decorator to validate HTTP methods for endpoints"""
    allowed_methods = set(methods)
    
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        if frappe.local.request.method not in allowed_methods:
            return generate_response(405, "Method Not Allowed")
        return wrapped(*args, **kwargs)

    return wrapper