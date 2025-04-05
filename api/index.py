from flask import Flask, Response
from api.app import app
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(request):
    """Handle Vercel serverless function requests"""
    try:
        logger.info(f"收到请求: {request.method} {request.path}")
        
        if request.method == "GET" and request.path == "/":
            try:
                return app.send_static_file('index.html')
            except Exception as e:
                logger.error(f"加载首页失败: {str(e)}")
                return "加载首页失败", 500
                
        with app.request_context(request):
            try:
                response = app.full_dispatch_request()
                return response
            except Exception as e:
                logger.error(f"处理请求失败: {str(e)}")
                return str(e), 500
                
    except Exception as e:
        logger.error(f"服务器错误: {str(e)}")
        return str(e), 500 