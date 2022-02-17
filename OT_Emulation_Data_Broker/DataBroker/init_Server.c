#include "init_Server.h"
#include "Sem_Stop.h"

void *init_Server(void *arg)
{

    //Simulator variables
    int STOP = 0;
    //JSON file variables
    cJSON *elem, *name;
    char *json_string;
    const cJSON *object = NULL;
    const cJSON *endpoints = NULL;

    //ZMQ variables
    char IP_buffer[256];
    char *tag, *IP, *saveptr;
    int nbytes = 1;
    char IP_buf[256] = "", buffer[256] = "", msg[256 * 10] = "";
    void *responder, *requester;
    int startFlag;
    // Read in JSON file
    json_string = ReadFile("input.json");
    cJSON *root = cJSON_Parse(json_string);
    int n = cJSON_GetArraySize(root);
    
    startFlag = *(int*)arg;

    // Make sure JSON file is read succesfully
    if (!root)
    {
        const char *error_ptr = cJSON_GetErrorPtr();
        if (error_ptr != NULL)
        {
            fprintf(stderr, "Error before: %s\n", error_ptr);
        }
    }
    
    //Start ZMQ server to communicate with Endpoint
    void *context = zmq_ctx_new();
    if (startFlag == 0){
        responder = zmq_socket(context, ZMQ_REP);
        int rc = zmq_bind(responder, "tcp://*:6666");
        assert (rc == 0);
    }

    while (1)
    {

        if (startFlag == 0)
        {
            IP_buffer[0] = 0;
            nbytes = zmq_recv(responder, IP_buffer, sizeof(IP_buffer), 0);
        }

        if (nbytes != -1)
        {
            if (startFlag == 0)
            {
                tag = strtok_r(IP_buffer, ":", &saveptr);
                if (tag != NULL){
                    IP = strtok_r(NULL, ":", &saveptr);
                }else{
                    printf("Endpoint return address is invalid!\n");
                    break;
                }
            }

            endpoints = cJSON_GetObjectItem(root, "endpoints");

            cJSON_ArrayForEach(object, endpoints)
            {
                cJSON *IP_Host = cJSON_GetObjectItem(object, "IP_Host");
                cJSON *node = cJSON_GetObjectItem(object, "node");
                cJSON *IP_PLC = cJSON_GetObjectItem(object, "IP_PLC");
                cJSON *sensor = cJSON_GetObjectItem(object, "sensor");
                cJSON *sensorNames = cJSON_GetObjectItem(object, "sensorNames");
                cJSON *actuator = cJSON_GetObjectItem(object, "actuator");
                cJSON *actuatorNames = cJSON_GetObjectItem(object, "actuatorNames");
                cJSON *scanTime = cJSON_GetObjectItem(object, "scanTime");
                cJSON *TimeMem = cJSON_GetObjectItem(object, "TimeMem");
                cJSON *MemFormat = cJSON_GetObjectItem(object, "MemFormat");
                cJSON *Port = cJSON_GetObjectItem(object, "Port");
                cJSON *Endianess = cJSON_GetObjectItem(object, "Endianess");
                cJSON *MultiPLC = cJSON_GetObjectItem(object, "MultiPLC");

                /* Check to see if everthing needed is there */
                if (!node) node = cJSON_CreateString("WishIHadAName");
                if( !IP_PLC || !IP_Host){
                    printf("Need both IP_PLC and IP_Host in the JSON!!\n");
                    break;
                }
                if ( !sensor ) sensor = cJSON_CreateString("0"); /* sensor and actuator will become holding spots for future additions or revisions */
                if ( !sensorNames ) sensorNames = cJSON_CreateString("NULL");
                if ( !actuator ) actuator = cJSON_CreateString("0");
                if ( !actuatorNames ) actuatorNames = cJSON_CreateString("NULL");
                if ( !scanTime ) scanTime = cJSON_CreateString("0");
                if ( !TimeMem ) TimeMem = cJSON_CreateString("-1");
                if ( !MemFormat ) MemFormat = cJSON_CreateString("32_float");
                if ( !Endianess ) Endianess = cJSON_CreateString("Big,Big");
                if ( !MultiPLC ) MultiPLC = cJSON_CreateString("NULL");
                if ( !Port ) Port = cJSON_CreateString("502");
                
                snprintf(msg, sizeof(msg), "%s:%s:%s:%s:%s:%s:%s:%s:%s:%s:%s:%s:", node->valuestring, IP_PLC->valuestring,
                         sensor->valuestring, sensorNames->valuestring, actuator->valuestring, actuatorNames->valuestring, 
                         scanTime->valuestring, TimeMem->valuestring, MemFormat->valuestring, Endianess->valuestring, Port->valuestring, MultiPLC->valuestring);
                
                if (startFlag == 0)
                {
                    if (strcmp(IP_Host->valuestring, IP) != 0){
                        printf("Sending Initialization to Endpoint: %s\n", IP);
                        zmq_send(responder, msg, sizeof(msg), 0);
                    }
                }else{
                    requester = zmq_socket(context, ZMQ_REQ);
                    snprintf(IP_buf, sizeof(IP_buf), "%s%s%s", "tcp://",IP_Host->valuestring,":6666");
                    zmq_connect(requester, IP_buf);
                    zmq_send(requester, msg, sizeof(msg), 0);
                    zmq_recv(requester, buffer, sizeof(buffer), 0);
                    printf("Received: %s\n", buffer);
                    zmq_close(requester);
                }

                msg[0] = 0;
            }
        }

        if (startFlag == 1){
            
            break;
        }

        //Check stop semaphore
        STOP = Sem_Stop();
        if (STOP > 0 || nbytes == -1)
        {
            break;
        }
    }

    cJSON_Delete(root);
    if (startFlag == 0)
    {
        printf("ZMQ Initialization Server Closed Successfully\n");
        zmq_close(responder);
        zmq_ctx_destroy(context);
        pthread_exit((void *)0);
    }
    else
    {
        zmq_ctx_destroy(context);
        printf("Endpoint Initialization Complete\n");
    }
}

char *SimName(void)
{
    // Vars setup
    char *json_string;
    const cJSON *simulator = NULL;
    const cJSON *EXE = NULL;

    // Read in JSON file
    json_string = ReadFile("input.json");
    cJSON *root = cJSON_Parse(json_string);
    int n = cJSON_GetArraySize(root);

    // Make sure JSON file is read succesfully
    if (root == NULL)
    {
        const char *error_ptr = cJSON_GetErrorPtr();
        if (error_ptr != NULL)
        {
            fprintf(stderr, "Error before: %s\n", error_ptr);
        }
    }

    // Read Simulator information
    simulator = cJSON_GetObjectItem(root, "simulator");
    cJSON_ArrayForEach(EXE, simulator){
            cJSON *ExecutableName = cJSON_GetObjectItem(EXE, "executableName");
            if (!ExecutableName){
                printf("Executable Name = Null \n****You need a simulation executable in the JSON!****\n");
                break;
            }else{
                printf("Executable Name = %s \n", ExecutableName->valuestring);
                return ExecutableName->valuestring;
            }
    }
}

char *ReadFile(char *filename)
{
    char *buffer = NULL;
    int string_size, read_size;
    FILE *handler = fopen(filename, "r");

    if (handler)
    {
        // Seek the last byte of the file
        fseek(handler, 0, SEEK_END);
        // Offset from the first to the last byte, or in other words, filesize
        string_size = ftell(handler);
        // go back to the start of the file
        rewind(handler);
        // Allocate a string that can hold it all
        buffer = (char *)malloc(sizeof(char) * (string_size + 1));
        // Read it all in one operation
        read_size = fread(buffer, sizeof(char), string_size, handler);
        // fread doesn't set it so put a \0 in the last position
        // and buffer is now officially a string
        buffer[string_size] = '\0';
        if (string_size != read_size)
        {
            // Something went wrong, throw away the memory and set
            // the buffer to NULL
            free(buffer);
            buffer = NULL;
        }
        // Always remember to close the file.
        fclose(handler);
    }
    return buffer;
}