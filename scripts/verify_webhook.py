from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

VERIFY_TOKEN = "amritp.ap2026@gmail.com"

class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)

        mode = params.get('hub.mode', [None])[0]
        token = params.get('hub.verify_token', [None])[0]
        challenge = params.get('hub.challenge', [None])[0]

        if mode == 'subscribe' and token == VERIFY_TOKEN:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(challenge.encode('utf-8'))
            print("Verification successful! Challenge: " + str(challenge))
        else:
            self.send_response(403)
            self.end_headers()
            print("Verification failed. Token mismatch.")

if __name__ == '__main__':
    server = HTTPServer(('localhost', 8080), WebhookHandler)
    print("Webhook verification server started on port 8080...")
    server.serve_forever()
