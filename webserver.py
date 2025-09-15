# webserver.py
import socket
import threading
import os
import json
import uuid


# Constants
HOST = ''
PORT = 8041
DB_HOST = input("Enter database server address (e.g., 127.0.0.1): ").strip()
sessions= {}  # In-memory sessions (session_id : username)
STATIC_INDEX_FILE = 'index.html'

# parse query parameters from a path
def parse_path_and_query(path):
    if '?' in path:
        route, query_string = path.split('?', 1)
        query = {}
        for pair in query_string.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                query[key]=value
        return route, query
    return path, {}

# send an HTTP response
def send_response(conn,status_code,headers,body):
    if body:  # automatically add content length to the header
        if isinstance(body, bytes):  #if content is in bytes 
            content_length = len(body)
        else:
            content_length = len(body.encode('utf-8'))
        headers['Content-Length'] = str(content_length)

        origin = headers.pop("Requested-Origin", None)
        if origin:  
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"

    response= f"HTTP/1.1 {status_code}\r\n" # status code
    for key, value in headers.items():
        response += f"{key}: {value}\r\n"  # add in the headers
    response += "\r\n"  # second new line
    
    if body:  #if body exists
        if isinstance(body, bytes):
            response = response.encode('utf-8') + body
        else:
            response = response.encode('utf-8') + body.encode('utf-8')
    else:  # body does not exist
        response = response.encode('utf-8')
    
    conn.sendall(response)  # send response

def parse_request(conn):
    data = b""
    # Step 1: Read until we get the full headers (ending with \r\n\r\n)
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(1024)
        if not chunk:
            break
        data += chunk

    header, _, body = data.partition(b"\r\n\r\n")

    header_lines = header.decode().split("\r\n")
    if not header_lines or len(header_lines[0].split(" ")) < 3:
        raise ValueError("Malformed request line")

    method, path, _ = header_lines[0].split(" ", 2)
    headers = {}

    for line in header_lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()

    content_length = int(headers.get("content-length", 0))

    # Step 2: Read the body (if present)
    while len(body) < content_length:
        chunk = conn.recv(1024)
        if not chunk:
            break
        body += chunk

    # Step 3: Handle CORS
    origin = headers.get("origin")
    if origin:
        headers["Requested-Origin"] = origin

    return method, path, headers, body


# parse cookies
def parse_cookies(header):
    cookies = {}
    for pair in header.split(';'):
        if '=' in pair:
            key, value = pair.strip().split('=', 1)
            cookies[key] = value
    return cookies


#API handler
def api(conn, method, raw_path, header, body):
    path, query = parse_path_and_query(raw_path)
    cookies= parse_cookies(header.get('cookie',""))  # pass the cookie header
    session_id = cookies.get('session_id')
    username = sessions.get(session_id)
    

    # Validate session
    if path != "/api/login" and (not session_id or session_id not in sessions):
        send_response(conn, "403 Forbidden", {"Content-Type": "text/plain"}, "Unauthorized")
        return
    
    if path == "/api/login" and method == "POST":
        data = json.loads(body.decode())
        username = data.get("username")
        if not username:
            send_response(conn, "400 Bad Request", {"Content-Type": "text/plain"}, "Missing username")
            return
        session_id = str(uuid.uuid4())
        sessions[session_id] = username
        send_response(conn, "200 OK", {
            "Content-Type": "application/json",
            "Set-Cookie": f"session_id={session_id}; HttpOnly"
        }, json.dumps({"message": "Login successful"}))
        return
    
    if path == "/api/login" and method == "DELETE":
        sessions.pop(session_id, None)
        send_response(conn, "200 OK", {"Content-Type": "application/json"}, json.dumps({"message": "Logged out"}))
        return
    
    # Handle /api/list, /api/get, api/push, api/delete. by connecting to file server via socket
    try:
        database_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        database_socket.connect((DB_HOST, 8042))
        database_socket.sendall(f"LOGIN {username}".encode())
        login_resp = database_socket.recv(1024).decode().strip()
        if login_resp != "LOGIN SUCCESSFUL":
            send_response(conn, "403 Forbidden", {"Content-Type": "text/plain"}, login_resp)
            database_socket.close()
            return
        
        if path == "/api/list" and method == "GET":
            database_socket.sendall("LIST".encode())

            # Step 1: receive the first message
            status = database_socket.recv(1024).decode().strip()

            response = ""
            if status == "No files exist on the server.":
                send_response(conn, "200 OK", {"Content-Type": "text/plain"}, "")
                return
            elif status.startswith("Ready"):
                # Proceed to read file list
                file_list = b""
                database_socket.settimeout(1.0)
                try:
                    while True:
                        chunk = database_socket.recv(4096)
                        if not chunk:
                            break
                        file_list += chunk
                except socket.timeout:
                    pass

                send_response(conn, "200 OK", {"Content-Type": "text/plain"}, file_list.decode())
            else:
                # Unknown response
                send_response(conn, "500 Internal Server Error", {"Content-Type": "text/plain"}, f"Unexpected response: {status}")

        elif path == "/api/get" and method == "GET":
            file = query.get("file")
            database_socket.sendall(f"GET {file}".encode())

            # Step 1: wait for confirmation
            initial_response = database_socket.recv(1024).decode().strip()
            if not initial_response.startswith("Available"):
                send_response(conn, "404 Not Found", {"Content-Type": "text/plain"}, initial_response)
                return
    
            # Step 2: receive the file
            file_data = b""
            try:
                while True:
                    chunk = database_socket.recv(4096)
                    if b"EOF" in chunk:
                        file_data += chunk[:-3]
                        break
                    file_data += chunk
            except socket.timeout:
                pass  # done receiving

            # Step 3: send response
            send_response(conn, "200 OK", {
                "Content-Type": "application/octet-stream",
                "Content-Disposition": f'attachment; filename="{file}"'
            }, file_data)

        elif path == "/api/delete" and method == "DELETE":
            file = query.get("file")
            database_socket.sendall(f"DELETE {file}".encode())
            resp = database_socket.recv(1024).decode().strip()

            if resp == f"{file} deleted successfully.":
                send_response(conn, "200 OK", {"Content-Type": "text/plain"}, resp)
            else:
                send_response(conn, "403 Forbidden", {"Content-Type": "text/plain"}, resp)
        elif path == "/api/push" and method == "POST":
            file = query.get("file")
            
            # Step 1: send PUSH <filename>
            database_socket.sendall(f"PUSH {file}\n".encode())

            # Step 2: wait for "Uploading"
            resp = database_socket.recv(1024).decode().strip()
            if not resp.startswith("Uploading"):
                send_response(conn, "403 Forbidden", {"Content-Type": "text/plain"}, resp)
                return

            # Step 3: send file content + EOF
            database_socket.sendall(body)
            database_socket.sendall(b"EOF")

            # Step 4: read server's final response
            resp = database_socket.recv(1024).decode().strip()
            send_response(conn, "200 OK", {"Content-Type": "text/plain"}, resp)

        else:
            send_response(conn, "404 Not Found", {"Content-Type": "text/plain"}, "Not found")
            database_socket.close()    
    
    except Exception as e:
        send_response(conn, "500 Internal Server Error", {"Content-Type": "text/plain"}, str(e))

# client thread
def client_thread(conn):
    try:
        method, path, headers, body = parse_request(conn)
        if path.startswith("/api/"):
            api(conn, method, path, headers, body)
        elif path == "/":
            try:
                with open(STATIC_INDEX_FILE, "rb") as f:
                    content = f.read()
                send_response(conn, "200 OK", {"Content-Type": "text/html"}, content)
            except FileNotFoundError:
                send_response(conn, "404 Not Found", {"Content-Type": "text/plain"}, "index.html not found")
        elif os.path.isfile(path.lstrip("/")):  # <<-- serve static files like main.js
            try:
                with open(path.lstrip("/"), "rb") as f:
                    content = f.read()
                if path.endswith(".js"):
                    content_type = "application/javascript"
                elif path.endswith(".css"):
                    content_type = "text/css"
                else:
                    content_type = "application/octet-stream"
                send_response(conn, "200 OK", {"Content-Type": content_type}, content)
            except FileNotFoundError:
                send_response(conn, "404 Not Found", {"Content-Type": "text/plain"}, "Static file not found")
        else:
            send_response(conn, "404 Not Found", {"Content-Type": "text/plain"}, "Not Found")
    except Exception as e:
        send_response(conn, "500 Internal Server Error", {"Content-Type": "text/plain"}, str(e))
    finally:
        conn.close()


# Start server
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"WebServer listening on {PORT}\n")
# accept clients
    while True:
        conn, addr = server_socket.accept()
        threading.Thread(target=client_thread, args=(conn,)).start()

