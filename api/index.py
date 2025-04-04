from app import app

# Vercel需要handler函数
def handler(request):
    return app(request) 