#include "Shm_Interface.h"
#include "UDP_Server.h"
#include "Sem_Stop.h"

DATA UP_DATA[MAX_IO]; // Upper limit of IO = 1000
DATA PUB_DATA[MAX_IO];
pthread_mutex_t DATA_Mutx;

void *Shm_Interface()
{

	key_t msg_key = 10620; //shared memory DB key
	key_t SHM_PUB = 10618; //shared memory publish key
	key_t SHM_UP = 10619; //shared memory update key
	char msg[256*100];
    sem_t *up;
    sem_t *pub;
	sem_t *msg_sem;

	//Setup semaphores
	pub = sem_open("/pp_sem", O_CREAT, 0644, 0);
	up = sem_open("/up_sem", O_CREAT, 0644, 0);
	msg_sem = sem_open("/msg", O_CREAT, 0644, 0);

	//Gather number of update and publish points from simulink
	//And get timestep size
	sem_wait(msg_sem);

	int shmdb = shmget(msg_key, sizeof(MSG_DATA), 0600|IPC_CREAT);
	MSG_DATA *MSG_DB = (MSG_DATA *) shmat(shmdb,NULL,0);
	int N_UP = MSG_DB->UP; //number update points
	int N_PUB = MSG_DB->PUB; //number publish points
	double DT = MSG_DB->TimeStep * 1000.0; //timestep size in milli-seconds
	shmdt(MSG_DB);

	//setup shared memory
	int shmidup = shmget(SHM_UP, N_UP * sizeof(DATA), 0600 | IPC_CREAT);
	int shmidpub = shmget(SHM_PUB, N_PUB * sizeof(DATA), 0600 | IPC_CREAT);

	if ((shmidup == -1) || (shmidpub == -1))
	{
		perror("Shared memory");
	}

	DATA *PublishSHM = (DATA *)shmat(shmidpub, NULL, 0);
	DATA *UpdateSHM = (DATA *)shmat(shmidup, NULL, 0);

	int n;
	pthread_mutex_lock(&DATA_Mutx);
	
	n = 0;
	for (n = 0; n < N_UP; n++)
	{
		UP_DATA[n] = UpdateSHM[n];
	}
	pthread_mutex_unlock(&DATA_Mutx);

	int STOP;
	struct timespec tw1, tw2;
	double T_INTERVAL = 0;

	clock_gettime(CLOCK_MONOTONIC, &tw2);
	sem_post(pub);
	sem_post(up);

	while (1)
	{
		//get semaphore
		sem_wait(pub);

		//Lock mutex and distribute Publish data and import Update data structs
		n = 0;
		memset(msg,0,sizeof(msg));
		pthread_mutex_lock(&DATA_Mutx);
		for (n = 0; n < N_PUB; n++)
		{
			PUB_DATA[n] = PublishSHM[n];
			if (n == 0){
				sprintf(msg,"%s %s %f %f sec \n", PUB_DATA[n].Name, PUB_DATA[n].Type, PUB_DATA[n].Value, PUB_DATA[n].Time);
			}else {
				sprintf(msg+strlen(msg),"%s %s %f %f sec \n", PUB_DATA[n].Name, PUB_DATA[n].Type, PUB_DATA[n].Value, PUB_DATA[n].Time);
			}
			printf("%s %s %f %f sec \n", PUB_DATA[n].Name, PUB_DATA[n].Type, PUB_DATA[n].Value, PUB_DATA[n].Time);
		}
		
		shmdt(&PublishSHM);
		n = 0;
		for (n = 0; n < N_UP; n++)
		{
			UpdateSHM[n].Value = UP_DATA[n].Value;
			UpdateSHM[n].Time = UP_DATA[n].Time;
			printf("%s %s %f %f sec \n", UP_DATA[n].Name, UP_DATA[n].Type, UP_DATA[n].Value, UP_DATA[n].Time);
		}
		pthread_mutex_unlock(&DATA_Mutx);

		shmdt(&UpdateSHM);

		printf("\n***Press X then Enter to stop simulation***\n");
		
		// send UDP message
		UDP_Server(msg);

		// Time control
		while (T_INTERVAL < DT)
		{
			clock_gettime(CLOCK_MONOTONIC, &tw1);
			T_INTERVAL = 1000.0 * tw1.tv_sec + 1e-6 * tw1.tv_nsec - (1000.0 * tw2.tv_sec + 1e-6 * tw2.tv_nsec);
		}
		clock_gettime(CLOCK_MONOTONIC, &tw2);
		T_INTERVAL = 0;

		//Release semaphore
		sem_post(up);

		//Check stop semaphore
		STOP = Sem_Stop();
		if (STOP > 0)
		{
			break;
		}
	}
	memset(msg,0,sizeof(msg));
	sprintf(msg,"STOP\nSTOP\n");
	UDP_Server(msg);

	pthread_exit((void *)0);
}