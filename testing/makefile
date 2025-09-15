# Compiler and flags
CC = gcc
CFLAGS = -Wall -Wextra -O2

# Target binary name
TARGET = scraper

# Source files
SRC = scraper.c

# Default rule
all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC)

# Clean up build artifacts
clean:
	rm -f $(TARGET)

# Rebuild everything from scratch
rebuild: clean all
