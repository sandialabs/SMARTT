#include "PLC_Interface.h"
#include "Shm_Interface.h"
#include "Sem_Stop.h"

void *PLC_Interface()
{
    //  Socket to talk to clients
    void *context = zmq_ctx_new ();
    void *responder = zmq_socket (context, ZMQ_PULL);
    int rc = zmq_bind (responder, "tcp://*:5555");
    assert (rc == 0);
    
    int n = 0;
    int STOP = 0;
    int nbytes;
    char buffer [MSG_BUFFER];
    char *name, *value, *saveptr;

    while (1) {
        memset(buffer,0,sizeof(MSG_BUFFER));
        nbytes = zmq_recv (responder, buffer, MSG_BUFFER, 0);
        assert (nbytes != -1);
        if (nbytes == -1) //Break if ZMQ problem?? Should have program try to fix itself
		{
			break;
		}
        
        name = strtok_r(buffer, ":", &saveptr); //NEED to use strtok_r or not thread safe!
        value = strtok_r(NULL, ":", &saveptr);  //IE if strtok is used in another thread they could collide

	    pthread_mutex_lock(&DATA_Mutx);

	    for (n = 0; n < MAX_IO; n++)
	    {   
            if (strcmp(UP_DATA[n].Name,name) == 0){
		        UP_DATA[n].Value = strtod(value,NULL);
                break;
            }
	    }   
	    pthread_mutex_unlock(&DATA_Mutx);

        //Check stop semaphore
		STOP = Sem_Stop();
		if (STOP > 0 || nbytes == -1)
		{
			break;
		}
    }
    
zmq_close(responder); 
zmq_ctx_destroy(context);
printf("ZMQ Update Server Closed Successfully \n");
pthread_exit((void *)0);

}

