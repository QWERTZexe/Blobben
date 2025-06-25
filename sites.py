import http.server
import socketserver
import json
import os

def backend(cwd):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            self.cwd = cwd
            super().__init__(*args, **kwargs)

        def do_GET(self):
            if self.path == '/downloads':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                try:
                    downloads_file = os.path.join(self.cwd, "cache", "downloads.json")
                    if os.path.exists(downloads_file):
                        with open(downloads_file, 'r') as f:
                            downloads = json.load(f)
                            # Sort by newest first
                            downloads.reverse()
                            self.wfile.write(json.dumps(downloads).encode())
                    else:
                        # Create empty downloads file
                        os.makedirs(os.path.dirname(downloads_file), exist_ok=True)
                        with open(downloads_file, 'w') as f:
                            json.dump([], f)
                        self.wfile.write(json.dumps([]).encode())
                except Exception as e:
                    print(f"Error serving downloads: {e}")
                    self.wfile.write(json.dumps([]).encode())
                return

            # Serve settings.json for reading
            if self.path == '/settings.json':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                try:
                    settings_file = os.path.join(self.cwd, "sites", "settings.json")
                    with open(settings_file, 'r') as f:
                        self.wfile.write(f.read().encode())
                except:
                    self.wfile.write(json.dumps({}).encode())
                return

            # Default file serving from sites directory
            self.path = os.path.join('/sites', self.path.lstrip('/'))
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

        def translate_path(self, path):
            """Override to serve files from the correct directory"""
            path = path.split('?',1)[0]
            path = path.split('#',1)[0]
            path = path.replace('//', '/')
            return os.path.join(self.cwd, path.lstrip('/'))

        def do_POST(self):
            # Handle settings updates
            if self.path == '/settings.json':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                try:
                    settings = json.loads(post_data.decode())
                    settings_file = os.path.join(self.cwd, "sites", "settings.json")
                    with open(settings_file, 'w') as f:
                        json.dump(settings, f, indent=2)
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'OK')
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(str(e).encode())
                return

            self.send_response(404)
            self.end_headers()

    with socketserver.TCPServer(("", 7859), Handler) as httpd:
        print("Server started at http://localhost:7859")
        httpd.serve_forever()
