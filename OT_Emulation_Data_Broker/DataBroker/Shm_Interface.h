#ifndef shm_int
#define shm_int
#include <sys/ipc.h>
#include <sys/shm.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <stdio.h>
#include <stdlib.h>
#include <semaphore.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>
#include <pthread.h>
#include <time.h>
#include <unistd.h>
// S-function Defines
#define _BSD_SOURCE
#define MAX_IO 1000
void *Shm_Interface();
// Shm Variables
typedef struct {
    char Name[128];
    char Type[50];
    double Value;
    double Time;
} DATA;
typedef struct {
    int PUB;
    int UP;
    double TimeStep;
    } MSG_DATA;

extern DATA UP_DATA[MAX_IO];
extern DATA PUB_DATA[MAX_IO];
extern pthread_mutex_t DATA_Mutx;

#endif