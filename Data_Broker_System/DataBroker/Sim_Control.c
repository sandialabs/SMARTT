#include "Sim_Control.h"
#include "Sem_Stop.h"

void User_Control(void){
    
    sem_t *stop;
	stop = sem_open("/stop", O_CREAT, 0644, 0);

    char invar;

    while(1){
        printf("***Enter X to stop simulation***\n\n");
        fflush(stdin);
        
        scanf("%c", &invar);
        
        if (invar == 'x' || invar == 'X'){
            printf("Stopping Simulator\n");
            sem_post(stop);
            break;
        }

    }
}


void *Sim_Control(){
    
    pid_t pid;
    char *args[2];
    args[0] = "ans_runtime_15mar21";
    args[1] = NULL;
    
    /* fork process */
    pid = fork();
    

    switch(pid){
        case -1:
            /* Fork failed*/
            perror("Fork failed");
            break;
        case 0:
            execv("ans_runtime_15mar21",args);
            printf("Simulator has failed to load! \n");
            break;
        default:
            printf("Simulator running\n");
            User_Control();
            break;
    }
    kill(pid,SIGTERM);

pthread_exit((void *)0);
}