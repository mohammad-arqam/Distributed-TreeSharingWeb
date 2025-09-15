TreeDrive FileSharing System - Assignment 2

How to Run the Program:

1. Start the file server:
   cd database_server
   python3 server.py

2. Start the web API server:
   cd ..
   python3 webserver.py
   Enter the databse host IP address to connect to the db server

3. Open the frontend in browser (eg. goose):
   http://goose.cs.umanitoba.ca:8041/

How to Run the Scraper:

1. Build the scraper:
   cd test
   make

2. Run the scraper with test file (eg. goose):
   ./scraper goose.cs.umanitoba.ca 8041 testuser test.txt
(test file is included in the test folder)
Notes:
- Port 8042 is used by the file server.
- Port 8041 is used by the web server.
- No bonus features were implemented.

