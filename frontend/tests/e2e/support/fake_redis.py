"""In-memory Redis for local end-to-end runs when no real Redis is available.

Usage: python fake_redis.py [port]   (needs the backend's dev dependency `fakeredis`)
"""

import sys

from fakeredis import TcpFakeServer

port = int(sys.argv[1]) if len(sys.argv) > 1 else 6391
server = TcpFakeServer(("127.0.0.1", port), server_type="redis")
print(f"fake redis listening on {port}", flush=True)
server.serve_forever()
