"""Run the Lambda handler locally by translating HTTP requests into function-URL events."""
import base64, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, ".")
import handler as h

class Req(BaseHTTPRequestHandler):
    def _run(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        event = {"rawPath": self.path.split("?")[0], "requestContext": {"http": {"method": self.command}},
                 "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body.decode("utf-8"), "isBase64Encoded": False}
        out = h.handler(event, None)
        data = out["body"].encode("utf-8")
        self.send_response(out["statusCode"])
        for k, v in out["headers"].items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    do_GET = do_POST = _run

ThreadingHTTPServer(("127.0.0.1", 8502), Req).serve_forever()
