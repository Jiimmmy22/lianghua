from flask import Flask
from api.app import app

def handler(request):
    """Handle Vercel serverless function requests"""
    return app.wsgi_app(request.environ, start_response)

def start_response(status, headers):
    """WSGI start_response function"""
    return None 