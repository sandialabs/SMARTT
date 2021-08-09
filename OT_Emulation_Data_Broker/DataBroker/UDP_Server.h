#ifndef sem_server
#define sem_server
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>
void UDP_Server(char *msg);
// UDP server defines
#define PORT 8000
#endif