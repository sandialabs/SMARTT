#include "Sem_Interface.h"
#include "Shm_Interface.h"
#include "PLC_Interface.h"
#include "Sim_Control.h"
#include "init_Server.h"

int main()
{
	void *status;
	pthread_t Sim_Int;
	pthread_t Sim_Con;
	pthread_t PLC_Con;
	//pthread_t init_S; #Depricated thread for continuous Endpoint reattachment
	int startFlag = 1;
	Sem_Interface();
	printf("Semaphores Initialized\n");
	init_Server(&startFlag);
	//startFlag = 0;

	pthread_mutex_init(&DATA_Mutx, NULL);
	
	//pthread_create(&init_S, NULL, init_Server, &startFlag);
	pthread_create(&Sim_Con, NULL, Sim_Control, (void *)0);
	pthread_create(&Sim_Int, NULL, Shm_Interface, (void *)0);
	pthread_create(&PLC_Con, NULL, PLC_Interface, (void *)0);

	//pthread_join(init_S, &status);
	pthread_join(Sim_Con, &status);
	pthread_join(Sim_Int, &status);
	pthread_join(PLC_Con, &status);
	
	pthread_mutex_destroy(&DATA_Mutx);

	return 0;
}
