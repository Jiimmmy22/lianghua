from flask import Flask, Response
from api.app import app

def handler(request):
    """Handle Vercel serverless function requests"""
    try:
        if request.method == "GET" and request.path == "/":
            return app.send_static_file('index.html')
            
        with app.request_context(request):
            response = app.full_dispatch_request()
            return Response(
                response.get_data(),
                status=response.status_code,
                headers=dict(response.headers)
            )
    except Exception as e:
        return str(e), 500 