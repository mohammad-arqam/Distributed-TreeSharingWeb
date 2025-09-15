TreeOne - File Sharing Web Server

TreeOne is a multi-threaded web server that extends the TreeDrive file-sharing system by adding a browser-based interface.
It provides a REST-style API for login, file upload/download, deletion, and listing, while communicating with the underlying file-sharing server over sockets.
The project includes a static frontend (index.html + main.js) and a C-based scraper for automated integration tests.

🚀 Features

Web Interface – Simple HTML + JavaScript client for login, file upload/download, delete, and list.

REST-like API – Routes under /api/ handle authentication and file operations.

Session Management – Implements cookies with session_id for authenticated users.

File Operations (via underlying file server):

/api/push?file=<filename> – Upload file.

/api/get?file=<filename> – Download file.

/api/delete?file=<filename> – Delete owned file.

/api/list – List all stored files.

Static File Serving – Serves index.html, main.js, and additional static resources.

C Test Scraper – Verifies login, push, list, and access control via raw HTTP requests.

Makefile – Automates build steps for scraper and server.

📂 Project Structure

webserver.py – Multi-threaded web server handling HTTP requests, sessions, and API routes.

server.py – Backend file-sharing server (from Assignment 1) handling file persistence, metadata, and commands.

index.html – Browser-based UI for interacting with the system.

main.js – Frontend logic for login, file upload/download, list, and delete.

scraper.c – C-based HTTP client performing automated integration tests.

makefile – Build script for compiling and running the scraper.

⚙️ Installation & Usage
1. Clone the repository
git clone https://github.com/yourusername/TreeOne-FileSharing-Web.git
cd TreeOne-FileSharing-Web

2. Start the file server
python3 server.py


(Default port: 8042)

3. Start the web server
python3 webserver.py


(Default port: 8041)

4. Open the web client

Navigate to:

http://localhost:8041/

5. Available API Routes

POST /api/login → login with username

DELETE /api/login → logout

GET /api/list → list files

POST /api/push?file=<filename> → upload file

GET /api/get?file=<filename> → download file

DELETE /api/delete?file=<filename> → delete file

6. Run the scraper tests
make scraper
./scraper localhost 8041 testuser test_file.txt


Validates login, push, list, and unauthorized access protection.
