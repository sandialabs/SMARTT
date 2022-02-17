import threading
import logging
import queue
import time
import socket
import sys
import os
import zmq
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
from pymodbus.constants import Endian


class Data_Repo(object):
    def __init__(self,SetString):
        Strings = SetString.split(",")
        self.Tags = Strings[::2]
        Mem_Strings = Strings[1::2]
        self.Mem = [int(n) for n in Mem_Strings]
        self.Tag_NoDuplicates = list(set(self.Tags))
        Val = [0.0] * len(self.Tag_NoDuplicates)
        self.Store = dict( zip(self.Tag_NoDuplicates, Val))

    def write(self, Tag, Value):
        self.Store[Tag] = Value

    def read(self, Tag):
        return self.Store[Tag]

    def UDP_TAGS(self):
        return self.Tag_NoDuplicates

#Define class for modbus PLCs
class MB_PLC:

    def __init__(self, IP, Port):
        self.ip = IP
        self.Mem_default = '32_float'
        self.port = Port
        self.client = ModbusClient(IP, port=self.port)
        self.byteOrder = Endian.Big
        self.wordOrder = Endian.Big
        self.mlock = threading.Lock()

    #Define how to connect with PLC
    def connect(self):
        client = self.client
        client.connect()

    #Define how to read values from PLCs
    def read(self, mem_addr, formating=None):
        #define decode options
        def float_64(decode):
            return decode.decode_64bit_float()
        def float_32(decode):
            return decode.decode_32bit_float()
        def float_16(decode):
            return decode.decode_16bit_float()
        def int_64(decode):
            return decode.decode_64bit_int()
        def int_32(decode):
            return decode.decode_32bit_int()
        def int_16(decode):
            return decode.decode_16bit_int()
        def uint_64(decode):
            return decode.decode_64bit_uint()
        def uint_32(decode):
            return decode.decode_32bit_uint()
        def uint_16(decode):
            return decode.decode_16bit_uint()

        #Check formatting and split off bit count
        if formating is None:
            formating = self.Mem_default
        Format = formating.split('_')

        if int(Format[0]) >= 16:  #determine number of registers to read
            count = int(int(Format[0])/16)
        else:
            count = 1

        client = self.client #define client

        try:
            results = client.read_holding_registers(mem_addr,count,unit=1) #read client PLC
        except:
            results = None

        #decoder dictionary
        Decode_dict = { '16_float':float_16, '32_float':float_32, '64_float':float_64, '16_int':int_16, '32_int':int_32, '64_int':int_64, '16_uint':uint_16, '32_uint':uint_32, '64_uint':uint_64 }

        if results is not None:
            #Set up decoder
            decoder = BinaryPayloadDecoder.fromRegisters(results.registers, byteorder=self.byteOrder, wordorder=self.wordOrder)
            
            return Decode_dict[formating](decoder)
            #return decoded value
        else:
            #return a Nonetype
            return results

    #define how to read coils from PLC
    def readcoil(self, mem_addr):
        client = self.client
        self.mlock.acquire()
        result = client.read_coils(mem_addr,1)
        self.mlock.release()
        return result.bits[0]

    #Define how to write to coils
    def writecoil(self, mem_addr, value):
        client = self.client
        self.mlock.acquire()
        client.write_coil(mem_addr, value)
        self.mlock.release()

    #define how to write to registers
    def write(self, mem_addr, value, formating=None):
        #define encode options
        def float_64(build, value):
            build.add_64bit_float(float(value))
        def float_32(build, value):
            build.add_32bit_float(float(value))
        def float_16(build, value):
            build.add_16bit_float(float(value))
        def int_16(build, value):
            build.add_16bit_int(value)
        def int_32(build, value):
            build.add_32bit_int(value)
        def int_64(build, value):
            build.add_64bit_int(value)
        def uint_16(build, value):
            build.add_16bit_uint(value)
        def uint_32(build, value):
            build.add_32bit_uint(value)
        def uint_64(build, value):
            build.add_64bit_uint(value)

        #Catch default format conditions and split bits value to determine register write count
        if formating is None:
            formating = self.Mem_default
        Format = formating.split('_')

        #Catch incorrect formating of ints
        if Format[1] == 'int' or Format[1] == 'uint':
            if type(value) is not int:
                value = int(value)


        if int(Format[0]) >= 16:  #determine number of registers to write
            count = int(Format[0])/16
        else:
            count = 1

        client = self.client #define client

        #start builder for writng to registers
        builder = BinaryPayloadBuilder(byteorder=self.byteOrder, wordorder=self.wordOrder)

        #encoder dictionary
        Encode_dict = { '16_float':float_16, '32_float':float_32, '64_float':float_64, '16_int':int_16, '32_int':int_32, '64_int':int_64, '16_uint':uint_16, '32_uint':uint_32, '64_uint':uint_64 }

        #Encode value with builder
        Encode_dict[formating](builder, value)

        payload = builder.to_registers()
        
        #read/write operations
        
        #error check the write operation
        try:
            Check_write = client.write_registers(mem_addr, payload)
        except:
            Check_write = None
            print('First write failed - IP:%s\n' % self.ip)
            pass
        
        if Check_write is not None:
            while Check_write.isError():
                try:
                    Check_write = client.write_registers(mem_addr, payload)
                except:
                    pass
        else:
            print("Client Not Connected!")


    #define how to close connection to PLC
    def close(self):
        client = self.client
        client.close()

    def __repr__(self):
        return "MB_PLC('{}')".format(self.ip)

def initialization():
    context = zmq.Context()
    reciever = context.socket(zmq.REP)
    reciever.bind("tcp://*:6666")
    
    msgFromServer = reciever.recv()
    msg = str(msgFromServer,'UTF-8')
    data = msg.split(":")
    reply = bytes(str(data[0])+" has initialized",'utf-8')
    reciever.send(reply)
    reciever.close()
    
    IP_PLCs = data[1].split(",")
    nPLC = len(IP_PLCs)
    if nPLC > 1 and data[11] == "NULL":
        logging.info("Config Error!\nMultiple PLCs with no MultiPLC JSON config!!")
        sys.exit(0)
    
    Endian_Key = data[9].split(",")
    Format_Key = data[8].split(",")
    sensor_name_key = data[3].split(",")
    actuator_name_key = data[5].split(",")

    MultiPLC = data[11].split(";")
    #parse multiPLC
    if MultiPLC[0] != "NULL":
        for val in MultiPLC:
            key = val.split("=")
            Loc = key[1].split(",")
            if key[0].lower() == "s":
                Sensor_Loc = [int(n) for n in Loc]
            if key[0].lower() == "a":
                Actuator_Loc = [int(n) for n in Loc]
    else:
        if sensor_name_key == "NULL":
            Sensor_Loc = 0
        else:
            Sensor_Loc = int(len(sensor_name_key)/2)
        if actuator_name_key == "NULL":
            Actuator_Loc = 0
        else:
            Actuator_Loc = int(len(actuator_name_key)/2)
    
    # parse endianness
    if (len(Endian_Key)/2) <= nPLC and len(Endian_Key) >= 2:
        Byte_order = Endian_Key[::2]
        Word_order = Endian_Key[1::2]
        Byte_order.extend([Byte_order[-1] for i in range(nPLC - len(Byte_order))])
        Word_order.extend([Word_order[-1] for i in range(nPLC - len(Word_order))])
    elif len(Endian_Key) % 2:
        logging.info("Config Error!\nEndianness setting must be a pair! ByteOrder,WordOrder (Big,Big) ")
    else:
        Byte_order = Endian_Key[::2]
        Word_order = Endian_Key[1::2]

    # parse format
    if len(Format_Key) <= nPLC:
        Mem_Format = Format_Key
        Mem_Format.extend([Format_Key[-1] for i in range(nPLC - len(Format_Key))])
    else:
        Mem_Format = Format_Key

    #port port port
    Port_Key = data[10].split(",")
    if len(Port_Key) <= nPLC:
        Port = [int(n) for n in Port_Key]
        Port.extend([Port[-1] for i in range(nPLC - len(Port))])
    else:
        Port = [int(n) for n in Port_Key]
    
    #Time Memory location
    Time_Mem_Key = data[7].split(",")
    if len(Time_Mem_Key) <= nPLC:
        Time_Mem = [int(n) for n in Time_Mem_Key]
        Time_Mem.extend([-1 for i in range(nPLC - len(Time_Mem))])
    else:
        Time_Mem = [int(n) for n in Time_Mem_Key]

    #Scan Times
    scanTime_Key = data[6].split(",")
    if len(Time_Mem_Key) <= nPLC:
        scanTime = [float(n) for n in scanTime_Key]
        scanTime.extend([0 for i in range(nPLC - len(scanTime))])
    else:
        scanTime = [float(n) for n in scanTime_Key]

    #Parse the sensor and actuator names and memory locations
    if sensor_name_key[0] != "NULL" and len(sensor_name_key) > 1:
        Sensor_Tags = sensor_name_key[::2]
        Sensor_Mem = sensor_name_key[1::2]
    else:
        Sensor_Tags = None
        Sensor_Mem = -1
    if actuator_name_key[0] != "NULL" and len(actuator_name_key) > 1:
        Actuator_Tags = actuator_name_key[::2]
        Actuator_Mem = actuator_name_key[1::2]
    else:
        Actuator_Tags = None
        Actuator_Mem = -1

    data = data[1:len(data)-1]
    return IP_PLCs, nPLC, Sensor_Loc, Actuator_Loc, Byte_order, Word_order, Mem_Format, Port, Time_Mem, scanTime, Sensor_Tags, Sensor_Mem, Actuator_Tags, Actuator_Mem, data

class Connector:
    def __init__(self,PLC,serAdd,Data,Lock,Event):
        self.PLC = PLC
        self.serAdd = serAdd
        self.Data = Data
        self.Lock = Lock
        self.Event = Event
        self.Time_Mem = -1
        self.Scan_Time = 0.1
        self.actuator = False
        self.sensor = False
        self.SensorTags = []
        self.SensorMem = []
        self.ActuatorTags = []
        self.ActuatorMem = []
        self.Actuator_String = ''
        self.Sensor_String = ''
        self.thread = None

    def Set(self, **kwargs):
        #uses dictionary to parse kargs
        options = {
            'Time_Mem':self.Time_Mem,
            'Scan_Time':self.Scan_Time,
            'actuator':self.actuator,
            'sensor':self.sensor,
            'SensorTags':self.SensorTags,
            'SensorMem':self.SensorMem,
            'ActuatorTags':self.ActuatorTags,
            'ActuatorMem':self.ActuatorMem,
            'Actuator_String':self.Actuator_String,
            'Sensor_String':self.Sensor_String }
        options.update(kwargs)

        #Parse Actuator strings
        if len(options['Actuator_String']) > 1:
            Act_Keys = options['Actuator_String'].split(',')
            options['ActuatorTags'] = Act_Keys[::2]
            Act_Mem_Strings = Act_Keys[1::2]
            options['ActuatorMem'] = [int(n) for n in Act_Mem_Strings]
            options['actuator'] = True

        #Parse Sensor strings
        if len(options['Sensor_String']) > 1:
            Sen_Keys = options['Sensor_String'].split(',')
            options['SensorTags'] = Sen_Keys[::2]
            Sen_Mem_Strings = Sen_Keys[1::2]
            options['SensorMem'] = [int(n) for n in Sen_Mem_Strings]
            options['sensor'] = True

        #set options 
        self.Time_Mem = options['Time_Mem']
        self.Scan_Time = options['Scan_Time']
        self.SensorTags = options['SensorTags']
        self.SensorMem = options['SensorMem']
        self.ActuatorTags = options['ActuatorTags']
        self.ActuatorMem = options['ActuatorMem']
        self.actuator = options['actuator']
        self.sensor = options['sensor']
    
    #define the thread that will run PLC comms
    def Agent(self):

        #initalize some values
        if self.sensor:
            Sensor_data = [0.0] * len(self.SensorTags)
        if self.actuator:
            Actuator_data = [0.0] * len(self.ActuatorTags)
        
        #connect to the PLC
        self.PLC.connect()

        #  ZMQ socket to talk to server
        if self.actuator:
            context = zmq.Context()
            DB = context.socket(zmq.PUSH)
            serverAddress = self.serAdd.get(block=True)
            DB.connect("tcp://"+serverAddress+":5555")
            logging.info("Successfully connected to server: " + serverAddress)
        
        #Setup timing mechanism
        time_end = time.time()

        while not self.Event.is_set():

            #gather data if sensor is active
            if self.sensor:
                #get data lock and release
                with self.Lock:
                    for i in range(len(self.SensorTags)):
                        Sensor_data[i] = self.Data.read(self.SensorTags[i])
                    Time_stamp = self.Data.read("Time")
                
                #write out to PLC
                for i in range(len(self.SensorTags)):
                    self.PLC.write(int(self.SensorMem[i]),Sensor_data[i])
                
                #write out Time if requested
                if self.Time_Mem != -1:
                    self.PLC.write(int(self.Time_Mem),Time_stamp)
            
            #perform scan time delay if requested
            if self.Scan_Time != 0:
                    time1 = 0
                    while time1 < self.Scan_Time and not self.Event.is_set():
                        time1 = time.time() - time_end
            
            if self.actuator:
                #gather and report data from PLC
                for i in range(int(len(self.ActuatorTags))):
                    Actuator_data[i] = self.PLC.read(int(self.ActuatorMem[i]))
                    if Actuator_data[i] is not None:
                        acutation_signal = bytes(self.ActuatorTags[i]+":"+str(Actuator_data[i])+" ",'utf-8')
                        DB.send(acutation_signal,zmq.NOBLOCK)
                    else:
                        print("Read Failure on IP: %s" % self.PLC.ip)

            time_end = time.time()
        
        #close up shop
        self.PLC.close()
        #if actuator, then close connection
        if self.actuator:
            DB.close()
        #Inform everyone we have closed up
        logging.info('Thread stopped for PLC IP:%s' % self.PLC.ip)
        sys.exit(0)

    #Define how to start the connector thread
    def run(self):
        self.thread = threading.Thread(target=self.Agent)
        self.thread.daemon = True
        self.thread.start()
    #Define how to stop Event thread
    def stop(self):
        self.Event.set()
        self.thread.join()
    #wait for Event to finish
    def wait(self):
        self.thread.join()

    def __repr__(self):
        return "Connector('{},{},{},{},{}')".format(self.PLC,self.serAdd,self.Data,self.Lock,self.Event)
               
def UDP_Client(Data,Event,serAdd,Lock,nPLCs):

    bufferSize          = 128*1000
    serverAddressPort   = ("255.255.255.255", 8000)
    # Create a UDP socket at client side
    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPClientSocket.bind(serverAddressPort)
    UDPClientSocket.settimeout(30)

    #grab tag names from Data class
    with Lock:
        Tags = Data.UDP_TAGS()

    #initalize values
    nTags = len(Tags)
    Values = [0.0] * nTags
    Time_Stamp = 0.0
    First_Time = True

    while not event.is_set():
        #recieve message from UDP
        msgFromServer,address = UDPClientSocket.recvfrom(bufferSize)
        #check if its the first update to pass the server IP to PLC threads
        if First_Time:
            for i in range(nPLCs):
                serAdd.put(address[0]) #there has to be a better way to do this
            First_Time = False

        #Decode message
        msg = str(msgFromServer,'UTF-8')
        msg_split = msg.split()

        #See if a stop was requested
        if msg_split[0] == "STOP":
            event.set()
            logging.info("UDP Client was sent stop request from DataBroker.")
            break

        #get and store values from msg
        for i in range(nTags):
            try:
                IDX = msg_split.index(Tags[i])
                Values[i] = float(msg_split[IDX+1])
                Time_Stamp = float(msg_split[IDX+2])
            except:
                logging.info("Tag: %s not in UDP message..." % Tags[i])
        
        #plop data in data repo
        with Lock:
            for i in range(nTags):
                Data.write(Tags[i],Values[i])
                Data.write("Time",Time_Stamp)

    UDPClientSocket.close()
    logging.info("UDP Client received event. Exiting")
    sys.exit(0)

if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")

    pipeline = queue.Queue(maxsize=100)
    serverAddress = queue.Queue(maxsize=10)

    event = threading.Event()
    Lock = threading.Lock()

    # Initialize system
    IP_PLCs, nPLC, Sensor_Loc, Actuator_Loc, Byte_order, Word_order, Mem_Format, Port, Time_Mem_I, scanTime_I, Sensor_Tags, Sensor_Mem, Actuator_Tags, Actuator_Mem, data = initialization()

    Sensor_Data = Data_Repo(data[2])
    Sensor_Data.write("Time",0.0)

    PLC = []
    Comms = []

    for i in range(nPLC):
        #Init PLC
        PLC.append(MB_PLC(IP_PLCs[i],Port[i]))
        PLC[i].Mem_default = Mem_Format[i]
        
        #set endianness
        if Byte_order[i].lower() == 'little':
            PLC[i].byteOrder = Endian.Little
        else:
            PLC[i].byteOrder = Endian.Big
        
        if Word_order[i].lower() == 'little':
            PLC[i].wordOrder = Endian.Little
        else:
            PLC[i].wordOrder = Endian.Big

        #Init connectors
        Comms.append(Connector(PLC[i],serverAddress,Sensor_Data,Lock,event))

        #Determine how to split the tags and memory locations
        if nPLC == 1:
            S_Tags = Sensor_Tags
            S_Mem = Sensor_Mem
            if S_Tags is not None:
                Sen = True
            else:
                Sen = False
            A_Tags = Actuator_Tags
            A_Mem = Actuator_Mem
            if A_Tags is not None:
                Act = True
            else:
                Act = False
        else:
            if Sensor_Loc[i] != 0:
                Sen = True
                S_IDX = sum(Sensor_Loc[0:i])
                S_Tags = Sensor_Tags[S_IDX:(S_IDX+Sensor_Loc[i])]
                S_Mem = Sensor_Mem[S_IDX:(S_IDX+Sensor_Loc[i])]
            else:
                Sen = False
                S_Tags = None
                S_Mem = -1

            if Actuator_Loc[i] != 0:
                Act = True
                A_IDX = sum(Actuator_Loc[0:i])
                A_Tags = Actuator_Tags[A_IDX:(A_IDX+Actuator_Loc[i])]
                A_Mem = Actuator_Mem[A_IDX:(A_IDX+Actuator_Loc[i])]
            else:
                Act = False
                A_Tags = None
                A_Mem = -1
            
        #set up comms with these tags and other settings
        Comms[i].Set(Time_Mem = Time_Mem_I[i],Scan_Time = scanTime_I[i],actuator = Act,sensor = Sen,SensorTags = S_Tags,SensorMem = S_Mem,ActuatorTags = A_Tags,ActuatorMem = A_Mem)
        
    #setup UDP thread
    UDP_Thread = threading.Thread(target=UDP_Client, args=(Sensor_Data,event,serverAddress,Lock,nPLC))
    UDP_Thread.daemon = True

    try:
        #Start threads and wait for completion
        UDP_Thread.start()
        for c in Comms:
            c.run()

        UDP_Thread.join()
        time.sleep(2)
    
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            event.set()
            sys.exit(0)
        except SystemExit:
            event.set()
            os._exit(0)
