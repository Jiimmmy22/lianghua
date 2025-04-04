from flask import Flask
from app import app

# 配置matplotlib使用Agg后端
import matplotlib
matplotlib.use('Agg')

def handler(request):
    """Handle Vercel serverless function requests"""
    return app(request) 