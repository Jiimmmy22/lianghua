from flask import Flask, request
from api.app import app

def handler(request):
    """Handle Vercel serverless function requests"""
    if request.method == "GET":
        return app.send_static_file('index.html')
    
    with app.test_request_context(
        method=request.method,
        base_url=request.base_url,
        path=request.path,
        query_string=request.query_string,
        data=request.get_data(),
        headers=request.headers
    ):
        try:
            response = app.full_dispatch_request()
            return response
        except Exception as e:
            return str(e), 500 