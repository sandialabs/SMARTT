#ifndef init_Ser
#define init_Ser
#include <zmq.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <assert.h>
#include <pthread.h>
#include "cJSON.h"
void *init_Server(void *);
char *ReadFile();
#endif