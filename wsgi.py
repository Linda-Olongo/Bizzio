#!/usr/bin/env python3
"""
WSGI entry point for Bizzio application
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

try:
    # Import the Flask app
    from app import app
    application = app
except ImportError as e:
    print(f"Error importing app: {e}")
    # Fallback: try to import from app.py directly
    try:
        from app import app
        application = app
    except ImportError:
        print("Failed to import app from both locations")
        raise

if __name__ == "__main__":
    # For local development
    port = int(os.environ.get('PORT', 5001))
    application.run(host='0.0.0.0', port=port, debug=False)
