# TreeDrive Server and Client Implementation
# Note: Save server and client in separate files and run them separately.

# --- server.py ---
import os
import select
import socket
import sys
import time

SERVER_FILES_DIR = "server_files"
METADATA_FILE = os.path.join(SERVER_FILES_DIR, "metadata.txt")
host = ""  # Listen to all addresses
port = 8042

# Function to get the local IP address
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))  # This does not actually send data
        return s.getsockname()[0]
    finally:
        s.close()
        
# create a TCP server socket
try:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCP socket
except socket.error as e:
    print(f"Server: Failed to create socket: {e}")
    sys.exit(1)

# bind the socket
try:
    server_socket.bind((host, port))
except socket.error as e:
    print(f"Server: Failed to bind socket: {e}")
    sys.exit(1)

# Start Listening
try:
    server_socket.listen()
    local_ip = get_local_ip()
    print(f"Server is listening on {local_ip}: {port}")
except socket.error as e:
    print(f"Server: Failed to listen: {e}")
    sys.exit(1)

# check if server_files exist, if not, create it
if not os.path.exists(SERVER_FILES_DIR):
    os.makedirs(SERVER_FILES_DIR)

# check if metadata.txt exist, if not, create it
if not os.path.exists(METADATA_FILE):
    with open(METADATA_FILE, "w") as meta_file:
        meta_file.write("username,filename,size_MB,timestamp\n")

# maintaining a socket list and clients
socket_list = [server_socket]
clients = {}  # Dictionary to hold connected clients

try:
    while True:
        readable, writable, exceptional = select.select(socket_list, [], [])  # creates a queue of ready to read sockets

        for r in readable:
            if r is server_socket:
                # create a new connection
                client_socket, client_address = r.accept()
                print(f"New client connected from ({client_address[0]} , {client_address[1]})")
                socket_list.append(client_socket)

            else:
                try:
                    message_received = r.recv(1024)
                    if message_received:
                        decoded_message = message_received.decode("utf-8").strip()

                        if r not in clients:
                            if decoded_message.upper().startswith("LOGIN "):
                                parts = decoded_message.split(" ", 1)
                                if len(parts) == 2 and parts[1]:
                                    username = parts[1].strip()
                                    clients[r] = username
                                    response = "LOGIN SUCCESSFUL\n"
                                    print(f"User {username} logged in from ({client_address[0]} , {client_address[1]}).\n")
                            else:
                                response = "ERROR: Please login first using the LOGIN command.\n"
                                socket_list.remove(r)
                                r.close()
                            r.sendall(response.encode("utf-8"))

                        else:
                            # handle PUSH
                            if decoded_message.upper().startswith("PUSH "):
                                x, file_name = decoded_message.split(" ", 1)
                                file_name = file_name.strip()
                                file_path = os.path.join(SERVER_FILES_DIR, file_name)
                                user = clients[r]
                                # check if file already exists
                                if os.path.exists(file_path):
                                    file_owner = None
                                    with open(METADATA_FILE, "r") as meta:
                                        next(meta)  # Skip header
                                        for line in meta:
                                            parts = [p.strip() for p in line.strip().split(",")]
                                            if len(parts) >= 4:
                                                uname, fname, _, _ = parts
                                                if fname == file_name:
                                                    file_owner = uname
                                                    break
                                        if file_owner and file_owner == user:
                                            os.remove(file_path)  # allow overwriting
                                        else:
                                            response=f"Error: File '{file_name}' cannot be overwritten since you are not the owner.\n"
                                            r.sendall(response.encode("utf-8"))
                                            continue
                                
                                r.sendall(f"Uploading file {file_name}....\n".encode("utf-8"))
                                print(f"Receiving file {file_path} from {user} on ({client_address[0]} , {client_address[1]})\n")
                                # Open the file in write-binary mode to receive data
                                with open(file_path, "wb") as f:
                                    while True:
                                        data_received = r.recv(4096)
                                        if not data_received:
                                            break  # Client disconnected
                                        if data_received.endswith(b"EOF"):
                                            f.write(data_received[:-3])  # Remove EOF marker
                                            break
                                        f.write(data_received)
                                # Calculate file size in bytes
                                file_size = os.path.getsize(file_path) / (1024 * 1024)  # conversion from Bytes to MB
                                # Get the current timestamp
                                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

                                # update the meta-data file
                                with open(METADATA_FILE, "a") as meta:
                                    meta.write(f"{user},{file_name},{file_size:.2f},{timestamp}\n")
                                print(f"File saved: {file_path}\n ")
                                r.sendall(f"File  uploaded successfully.\n".encode("utf-8"))

                            # LIST
                            elif decoded_message.upper().startswith("LIST"):
                                try:
                                    with open(METADATA_FILE, "r") as meta:
                                        header = meta.readline()  # first line/header
                                        server_files = ""
                                        files_second = meta.readline()  # second line just a new line "\n"
                                        files=meta.readline()  # third line

                                        if files:  # there exists a file on the server
                                            r.sendall("Ready".encode("utf-8"))
                                            while files:  # read the file list
                                                parts = files.strip().split(",")
                                                if len(parts) >= 4:
                                                    username, filename, size, timestamp = parts
                                                    server_files += f"{filename}, {size}, {username}, {timestamp}\n"
                                                files = meta.readline()
                                            r.sendall(server_files.encode("utf-8"))
                                        else:  # no files exist on the server
                                            r.sendall("No files exist on the server.".encode("utf-8"))
                                            continue
                                            

                                except Exception as e:
                                    print(f"Error creating list of files: {e}")
                                    r.sendall(f"Error creating a list of files: {e}\n".encode("utf-8"))

                            # GET
                            elif decoded_message.upper().startswith("GET "):
                                try:
                                    x, filename = decoded_message.split(" ", 1)
                                    file_path = os.path.join(SERVER_FILES_DIR, filename)

                                    # check if file exists on server
                                    if not os.path.exists(file_path):
                                        r.sendall(f"ERROR: File '{filename}' does not exist on server.".encode("utf-8"))

                                    else:  # file exists on server
                                        r.sendall(f"Available".encode("utf-8"))  # send a confirmation to client
                                        with open(file_path, "rb") as file:
                                            while True:
                                                data = file.read(4096)  # Read 4096 bytes at a time
                                                if not data:
                                                    break  # End of file reached
                                                r.sendall(data)  # Send the chunk to the client
                                            r.sendall(b"EOF")  # send an EOF marker
                                            print(f"File Sent\n")
                                except Exception as e:
                                    print(f"An error occurred sending the file: {e}")
                                    r.sendall(f"ERROR: {str(e)}\n".encode("utf-8"))

                            # DELETE
                            elif decoded_message.upper().startswith("DELETE "):
                                try:
                                    x, filename = decoded_message.split(" ", 1)
                                    file_path = os.path.join(SERVER_FILES_DIR, filename)

                                    if not os.path.exists(file_path):  # file does not exist on server
                                        r.sendall(f"ERROR: File '{filename}' does not exist on server.\n".encode("utf-8"))
                                    else:  # file exists on server
                                        file_owner = None
                                        with open(METADATA_FILE, "r") as meta:
                                             next(meta)  # Skip header
                                             for line in meta:
                                                parts = [p.strip() for p in line.strip().split(",")]
                                                if len(parts) >= 4:
                                                    uname, fname, _, _ = parts
                                                    if fname == filename:
                                                        file_owner = uname
                                                        break

                                        if file_owner and file_owner == clients[r]:
                                            print(f"{file_owner} has requested to delete file '{filename}'.\n")
                                            os.remove(file_path)  # Delete the file
                                            r.sendall(f"{filename} deleted successfully.\n".encode("utf-8"))
                                            print(f"{filename} deleted successfully.\n")
                                            # remove file from meta data
                                            entry_to_remove = f"{file_owner},{filename},"

                                            with open(METADATA_FILE, "r") as infile, open(METADATA_FILE + ".tmp", "w") as outfile:
                                                for line in infile:
                                                    if not line.startswith(entry_to_remove):
                                                        outfile.write(line)

                                            # Replace the original file with the updated file
                                            os.replace(METADATA_FILE + ".tmp", METADATA_FILE)

                                        else:
                                            r.sendall(f"ERROR: {filename} cannot be deleted since you are not the owner of this file.\n".encode("utf-8"))
                                            print(f"{file_owner} tried deleting a file they don't own")

                                except Exception as e:
                                    print(f"An error occurred deleting the file: {e}\n")
                                    r.sendall(f"ERROR: {str(e)}\n".encode("utf-8"))

                            # QUIT
                            elif decoded_message.upper()== "QUIT":
                                r.sendall(b"Successfully disconnected.\n")
                                print(f"{clients[r]} disconnected.")
                                del clients[r]  # delete client
                                socket_list.remove(r)
                                r.close()  # Close connection

                    else:  # no message received
                        print("Client disconnected.")
                        socket_list.remove(r)
                        r.close()
                        continue
                except ConnectionResetError:
                    # Handle abrupt client disconnection
                    print("Client forcibly closed the connection.")
                    socket_list.remove(r)
                    r.close()
except KeyboardInterrupt:
    # Gracefully close all sockets on Ctrl+C
    print("\nShutting down server...")
    for s in socket_list:
        s.close()
        server_socket.close()
    print("All sockets closed. Server terminated.")
except Exception as e:
    # Catch all unexpected errors to ensure sockets are still closed
    print(f"\nUnexpected server error: {e}")
    for s in socket_list:
        s.close()
        server_socket.close()
    print("All sockets closed due to unexpected error.")