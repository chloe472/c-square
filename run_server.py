#!/usr/bin/env python3
"""
Simple script to run the Flask server for testing
"""
import logging
import sys
import socket
from routes import app

def find_free_port():
    """Find a free port to run the server on"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def setup_logging():
    """Set up logging"""
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

def main():
    logger = setup_logging()
    
    # Use port 8080 if available, otherwise find a free port
    try:
        port = 8080
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
    except OSError:
        port = find_free_port()
        logger.info(f"Port 8080 not available, using port {port}")
    
    logger.info("Starting Princess Diaries server...")
    logger.info(f"Server will run on http://localhost:{port}")
    logger.info("Available endpoints:")
    logger.info("  GET  /                 - Health check")
    logger.info("  POST /princess-diaries - Main endpoint")
    logger.info("")
    logger.info("To test the server, run: python test_princess_diaries.py")
    logger.info("Press Ctrl+C to stop the server")
    
    try:
        app.run(host='localhost', port=port, debug=True)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()