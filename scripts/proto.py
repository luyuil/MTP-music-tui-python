import socket

with socket.create_connection(("127.0.0.1", 6600), timeout=5) as s:
    s.sendall(b"status\ncurrentsong\nclose\n")
    with s.makefile("rb") as f:          # 按行读，直到 EOF
        for raw in f:
            print(raw.decode().rstrip())