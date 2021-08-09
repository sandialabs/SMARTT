#!/bin/bash

gcc DataBroker.c Sim_Control.c Sem_Interface.c Sem_Stop.c Shm_Interface.c UDP_Server.c PLC_Interface.c cJSON.c init_Server.c -lpthread -lzmq -o DB