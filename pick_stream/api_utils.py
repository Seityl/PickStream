"""
API response handling and exception management utilities for Pick Stream system.

Provides standardized response formatting and error handling for API endpoints:
- generate_response: Creates consistent JSON responses with status codes
- exception_handler: Centralizes exception logging and error responses
- handler: Decorator for HTTP method validation and automatic exception handling
- log_api_access: Logs all API requests and responses

Author: Jeriel Francis

Copyright (c) 2025, Jollys Pharmacy Limited and contributors
For license information, please see license.txt
"""


import wrapt
import frappe
import traceback
from bs4 import BeautifulSoup
from datetime import datetime
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
    error_message = None
    if message:
        if isinstance(message, Exception):
            error = frappe._dict({
                'error_type': str(type(message).__name__),
                'error_message': str(message)
            })
            response.error = error
            error_message = f'{error.error_type}: {error.error_message}'
        else:
            sanitized_message = BeautifulSoup(
                message,
                'html.parser'
            ).get_text()
            response.message = sanitized_message
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
        execution_time = None
        if hasattr(frappe.local, 'api_start_time'):
            execution_time = (datetime.now() - frappe.local.api_start_time).total_seconds() * 1000
        log_api_access(
            endpoint=request.path,
            request_method=request.method,
            request_data=request_data,
            response_data=response,
            status_code=status,
            execution_time=execution_time,
            error=error_message
        )
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
        # Store start time for execution time calculation
        frappe.local.api_start_time = datetime.now()
        try:
            if frappe.local.request.method not in allowed_methods:
                return generate_response(405, 'Method Not Allowed')
            return wrapped(*args, **kwargs)
        except Exception as e:
            return exception_handler(e)
    return wrapper


def log_api_access(
    endpoint: str,
    request_method: str,
    request_data: Dict,
    response_data: Dict,
    status_code: int,
    user: Optional[str] = None,
    execution_time: Optional[float] = None,
    error: Optional[str] = None
) -> None:
    """Queue API access logging as a background job."""
    try:
        request_headers = frappe.as_json(request_data.get('headers', {}), indent=2)
        request_params = frappe.as_json(request_data.get('args', {}), indent=2)
        request_body = frappe.as_json(
            request_data.get('json') or request_data.get('form', {}), 
            indent=2
        )
        response_json = frappe.as_json(response_data, indent=2)
        current_user = user or frappe.session.user
        ip_address = frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else None
        timestamp = datetime.now().isoformat()
        frappe.enqueue(
            method='pick_stream.api_utils.create_api_log',
            queue='default',
            timeout=300,
            is_async=True,
            now=False,
            job_name=f'api_log_{endpoint}_{timestamp}',
            endpoint=endpoint,
            request_method=request_method,
            request_headers=request_headers,
            request_params=request_params,
            request_body=request_body,
            response_data=response_json,
            status_code=status_code,
            user=current_user,
            ip_address=ip_address,
            execution_time=execution_time,
            error_message=error,
            timestamp=timestamp
        )
    except Exception as e:
        frappe.log_error(
            title='API Access Log Queueing Failed',
            message=f'Failed to queue API Access Log: {str(e)}\n{frappe.get_traceback()}'
        )


def create_api_log(
    endpoint: str,
    request_method: str,
    request_headers: str,
    request_params: str,
    request_body: str,
    response_data: str,
    status_code: int,
    user: str,
    ip_address: Optional[str],
    execution_time: Optional[float],
    error_message: Optional[str],
    timestamp: str
) -> None:
    try:
        log_doc = frappe.get_doc({
            'doctype': 'API Access Log',
            'endpoint': endpoint,
            'request_method': request_method,
            'request_headers': request_headers,
            'request_params': request_params,
            'request_body': request_body,
            'response_data': response_data,
            'status_code': status_code,
            'user': user,
            'ip_address': ip_address,
            'execution_time': execution_time,
            'error_message': error_message,
            'timestamp': timestamp
        })
        log_doc.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            title='API Access Log Creation Failed',
            message=f'Failed to create API Access Log: {str(e)}\n{frappe.get_traceback()}'
        )