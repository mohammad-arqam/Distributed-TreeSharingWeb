#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <assert.h>
#include <arpa/inet.h>
#include <netdb.h>

#define BUFFER_SIZE 8192

void send_request(int sock, const char *request) {
    send(sock, request, strlen(request), 0);
}

int connect_to_host(const char *host, int port) {
    int sock;
    struct sockaddr_in server;
    struct hostent *he;

    if ((he = gethostbyname(host)) == NULL) {
        perror("gethostbyname");
        exit(1);
    }

    sock = socket(AF_INET, SOCK_STREAM, 0);
    server.sin_family = AF_INET;
    server.sin_port = htons(port);
    server.sin_addr = *((struct in_addr *)he->h_addr);

    if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
        perror("connect");
        exit(1);
    }

    return sock;
}

char *get_cookie_from_response(const char *response) {
    static char cookie[256];
    char *start = strstr(response, "Set-Cookie: session_id=");
    if (!start) return NULL;
    sscanf(start, "Set-Cookie: %255[^;];", cookie);
    return cookie;
}

void read_response(int sock, char *buffer, int size) {
    memset(buffer, 0, size);
    recv(sock, buffer, size - 1, 0);
}

int main(int argc, char *argv[]) {
    if (argc != 5) {
        fprintf(stderr, "Usage: %s [host] [port] [username] [filename]\n", argv[0]);
        return 1;
    }

    const char *host = argv[1];
    int port = atoi(argv[2]);
    const char *username = argv[3];
    const char *filename = argv[4];

    char request[BUFFER_SIZE], response[BUFFER_SIZE];

    // Step 1: LOGIN
    int sock = connect_to_host(host, port);
    snprintf(request, sizeof(request),
        "POST /api/login HTTP/1.1\r\n"
        "Host: %s\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %lu\r\n"
        "Connection: close\r\n\r\n"
        "{\"username\":\"%s\"}", host, strlen(username) + 14, username);

    send_request(sock, request);
    read_response(sock, response, sizeof(response));
    close(sock);

    char *cookie = get_cookie_from_response(response);
    assert(cookie && "Login failed or cookie not received.");
    printf("Login successful.\n");
    
    // Step 2: LIST (Before push)
    sock = connect_to_host(host, port);
    snprintf(request, sizeof(request),
        "GET /api/list HTTP/1.1\r\n"
        "Host: %s\r\n"
        "Cookie: %s\r\n"
        "Connection: close\r\n\r\n", host, cookie);
    send_request(sock, request);
    read_response(sock, response, sizeof(response));
    close(sock);

    assert(!strstr(response, filename) && "File already exists before push!");
    printf("File doesn't already exist.\n");

    // Step 3: PUSH
    FILE *fp = fopen(filename, "rb");
    assert(fp && "File not found.");
    fseek(fp, 0, SEEK_END);
    long fsize = ftell(fp);
    rewind(fp);
    char *filedata = malloc(fsize);
    fread(filedata, 1, fsize, fp);
    fclose(fp);

    sock = connect_to_host(host, port);
    snprintf(request, sizeof(request),
        "POST /api/push?file=%s HTTP/1.1\r\n"
        "Host: %s\r\n"
        "Cookie: %s\r\n"
        "Content-Length: %ld\r\n"
        "Connection: close\r\n\r\n",
        filename, host, cookie, fsize);

    send_request(sock, request);
    send(sock, filedata, fsize, 0);  // Send file content
    free(filedata);
    read_response(sock, response, sizeof(response));
    close(sock);

    assert(strstr(response, "uploaded") || strstr(response, "success"));
    printf("File pushed.\n");

    // Step 4: LIST (After push)
    sock = connect_to_host(host, port);
    snprintf(request, sizeof(request),
        "GET /api/list HTTP/1.1\r\n"
        "Host: %s\r\n"
        "Cookie: %s\r\n"
        "Connection: close\r\n\r\n", host, cookie);
    send_request(sock, request);
    read_response(sock, response, sizeof(response));
    close(sock);

    assert(strstr(response, filename) && "File not found after push!");
    printf("File exists in updated list.\n");

    // Step 5: Unauthorized LIST (no cookie)
    sock = connect_to_host(host, port);
    snprintf(request, sizeof(request),
        "GET /api/list HTTP/1.1\r\n"
        "Host: %s\r\n"
        "Connection: close\r\n\r\n", host);
    send_request(sock, request);
    read_response(sock, response, sizeof(response));
    close(sock);

    assert(strstr(response, "403") || strstr(response, "Unauthorized"));
    printf("Prohibited unauthorized access sucessfully.\n");

    printf(" All tests passed successfully.\n");
    return 0;
}
