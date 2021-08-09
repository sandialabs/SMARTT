# Copyright 2021 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
import concurrent.futures
import logging
import queue
import threading
import time
import socket
import sys
import os
import zmq


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
    
    data = data[1:len(data)-1]
    return data

def contInit():
    #find IP of host
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8',1)) #We can make this more robust if needed
    local_ip = s.getsockname()[0]

    # Create a UDP socket at client side
    bufferSize          = 128*1000
    serverAddressPort   = ("255.255.255.255", 8000)
    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPClientSocket.bind(serverAddressPort)
    msgFromServer,serverAddress = UDPClientSocket.recvfrom(bufferSize)
    UDPClientSocket.close()

    #  Socket to talk to server
    context = zmq.Context()
    reciever = context.socket(zmq.REQ)
    reciever.connect("tcp://"+serverAddress[0]+":6666")
    My_IP = bytes("IP:"+str(local_ip),'utf-8')
    print("IP:"+str(local_ip))
    reciever.send(My_IP)
    
    msgFromServer = reciever.recv()
    msg = str(msgFromServer,'UTF-8')
    data = msg.split(":")
    reciever.close()
    
    data = data[1:len(data)-1]
    return data


def sensor(queue,event,init):
    from pymodbus.client.sync import ModbusTcpClient
    from pymodbus.constants import Endian
    from pymodbus.payload import BinaryPayloadBuilder
    
    #f = open("log.txt","a")
    try:
        PLC_IP = init[0]
        sensor = int(init[1])
        sensorTags = init[2].split(",")

        PLC = ModbusTcpClient(PLC_IP,502) 
        print("Modbus sensor successfully connected")
        

    except:
        print("Sensor initialization Failed")
        event.set()

    while not event.is_set() or not queue.empty():

        if sensor == 1: 
            for i in range(int(len(sensorTags)/2)):

                try:
                    data = queue.get(block=True,timeout=2)
                    builder = BinaryPayloadBuilder(byteorder=Endian.Big,wordorder=Endian.Big)
                    builder.add_32bit_float(float(data[1]))
                    payload = builder.build()
                    sensor_mem = queue.get(block=True,timeout=2)
                except:
                    event.set()

                try:
                    PLC.write_registers(int(sensor_mem),payload,skip_encode=True,unit=1)
                except:
                    logging.info("ModbusTCP write fail")
                


            try:
                builder = BinaryPayloadBuilder(byteorder=Endian.Big,wordorder=Endian.Big)
                builder.add_32bit_float(float(data[2]))
                payload = builder.build()
                PLC.write_registers(2048,payload,skip_encode=True,unit=1)
                
            except:
                logging.info("ModbusTCP write fail")
              
            logging.info("Simulation Time: %s", data[2],)
            #f.write("Simulation Time: "+str(data[2]))
    event.set()
    logging.info("Sensor received event. Exiting")
    #f.close()

def actuator(queue,event,init,serAdd):
    from pymodbus.client.sync import ModbusTcpClient
    from pymodbus.constants import Endian
    from pymodbus.payload import BinaryPayloadDecoder
    
    try:
        PLC_IP = init[0]
        actuator = int(init[3])
        actuatorTags = init[4].split(",")
        scanTime = float(init[5])

        PLC = ModbusTcpClient(PLC_IP,502) 
        print("Modbus actuator successfully connected")
        
        #  ZMQ socket to talk to server
        context = zmq.Context()
        DB = context.socket(zmq.PUSH)
        serverAddress = serAdd.get(block=True)
        DB.connect("tcp://"+serverAddress+":5555")
        print("Successfully connected to server: " + serverAddress)

    except:
        print("Actuator initialization failed")
        event.set()

    while not event.is_set():
        if actuator == 1:
            try:
                for i in range(int(len(actuatorTags)/2)):
                    actuator_mem = actuatorTags[i*2+1]
                    value = PLC.read_holding_registers(address=int(actuator_mem),count=2)
                    decoder = BinaryPayloadDecoder.fromRegisters(value.registers, byteorder=Endian.Big, wordorder=Endian.Big)
                    value_f = decoder.decode_32bit_float()
                    acutation_signal = bytes(actuatorTags[i*2]+":"+str(value_f),'utf-8')
                    DB.send(acutation_signal,zmq.NOBLOCK)
            except:
                logging.info("ModbusTCP read fail")
                #DB.send(b"Failed to Read Actuator")
                #reply = DB.recv()
        else:
            DB.send(b"Failed to Read Actuator")
            
        time.sleep(scanTime)

    DB.close()
    logging.info("Actuator received event. Exiting")

def UDP_Client(queue,event,init,serAdd):

    bufferSize          = 128*1000
    serverAddressPort   = ("255.255.255.255", 8000)
    # Create a UDP socket at client side
    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPClientSocket.bind(serverAddressPort)
    UDPClientSocket.settimeout(3)

    n = 0
    tag = init.split(",")

    while not event.is_set():
        try:
            msgFromServer,address = UDPClientSocket.recvfrom(bufferSize)
            if n == 0:
                serAdd.put(address[0])
                n = n + 1
            msg = str(msgFromServer,'UTF-8')
            data = msg.split()
            #print(data)
            for ii in range(int(len(tag)/2)):
                for i in range(len(data)):
                    if data[i] == tag[ii*2]:
                        queue.put(data[i:i+3])
                        queue.put(tag[ii*2+1])
                        break
        except:
            event.set()

    UDPClientSocket.close()
    logging.info("UDP Client received event. Exiting")

if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")

    pipeline = queue.Queue(maxsize=100)
    serverAddress = queue.Queue(maxsize=10)

    event = threading.Event()
    #os.remove("log.txt")
    if os.path.exists("log.txt"):
        data = contInit()
    else:
        data = initialization()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            executor.submit(UDP_Client, pipeline,event,data[2],serverAddress)
            executor.submit(sensor, pipeline,event,data)
            executor.submit(actuator,pipeline,event,data,serverAddress)
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            event.set()
            sys.exit(0)
        except SystemExit:
            event.set()
            os._exit(0)
