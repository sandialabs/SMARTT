#include "Sem_Stop.h"

//utility to check the simulations stop flag semaphore
int Sem_Stop(void)
{
    sem_t *stop;
    int ST;
	stop = sem_open("/stop", O_CREAT, 0644, 0);
	sem_getvalue(stop, &ST);
	int value = (int)ST;
	return value;
}