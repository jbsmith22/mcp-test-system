#!/usr/bin/env python3
"""
Simple test server to debug browser connection issues
"""

from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def hello():
    return '''
    <html>
    <head><title>Test Server</title></head>
    <body>
        <h1>🎉 Connection Successful!</h1>
        <p>If you can see this, the Flask server is working correctly.</p>
        <p>Server is running on: <code>http://0.0.0.0:5001</code></p>
        <p>Try accessing via:</p>
        <ul>
            <li><a href="http://127.0.0.1:5001">http://127.0.0.1:5001</a></li>
            <li><a href="http://localhost:5001">http://localhost:5001</a></li>
        </ul>
    </body>
    </html>
    '''

@app.route('/test')
def test():
    return {"status": "ok", "message": "API working"}

if __name__ == '__main__':
    print("🧪 Starting test server on port 5001...")
    print("🌐 Try: http://127.0.0.1:5001 or http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)