from api.app import app

def handler(request):
    """Handle Vercel serverless function requests"""
    with app.request_context(request):
        return app.handle_request() 