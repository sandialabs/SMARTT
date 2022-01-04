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
# Capture Modbus Traffic
#
# This program captures modbus traffic on port 502 from
# both the loopback network and ethernet adaptor. The 
# traffic is recorded to two files, eth_log.txt and lo_log.txt
# "eth" reffers to ethernet
# "lo" reffers to loopback 
# Currently only 32bit floats are decoded.
# This program is dependant on scapy for python3
# Linux is the recommended OS, but it can run on Windows
# as long as you manually specify the loopback and ethernet adaptor
# when it asks.

# Import the needed stuff
from scapy.all import *
import scapy.contrib.modbus as mb
import struct
import threading
import netifaces
import datetime

# Define lists for storing index of transaction information
# so it can be refferenced to identify return packet values
# register address.
ID = []
Address = []
# Global storage needed esp for loopback, since register
# value requests are seen twice.
global Last_reg
Last_reg = 0

ID2 = []
Address2 = []
global Last_reg2
Last_reg2 = 0

# Open files to log info
lo_file = open('lo_log.txt','w')
eth_file = open('eth_log.txt','w')

# Callbacks for scapy sniff when a packet is captured
def gotpacket_lo(packet):
    #check if packet is Modbus Request
    #packet.show()
    if mb.ModbusADURequest in packet:
        #packet.show()
        # Get layer info to determine what function is called
        layer4 = packet.getlayer(4)

        if layer4.funcCode == 0x10:
            # Write Register function code with values

            layer1 = packet.getlayer(1)
            layer2 = packet.getlayer(2)
            layer3 = packet.getlayer(3)

            # Collect packet info
            IP_src = layer1.src
            IP_dst = layer1.dst
            sport = layer2.sport
            dport = layer2.dport
            
            
            numReg = layer4.quantityRegisters/2
            hexVal = layer4.outputsValue
            addr = layer4.startAddr
            Value = [0] * int(numReg)

            #write transaction information to file and print out to cmd
            date = str(datetime.datetime.now()).split('.')[0]
            s = "[%s] Write Registers IP: %s:%u --> %s:%u Memory Address: %d\n" % (date, IP_src, sport, IP_dst, dport, addr)
            print(s)
            lo_file.write(s)
            
            # Attempt to decode values, sometimes fails due to incomplete packet.
            for i in range(0,int(numReg)):
                try:
                    mypack = struct.pack('>HH',hexVal[i*2],hexVal[i*2+1])
                    Value[i] = struct.unpack('>f',mypack)[0]
                    #Value[i] = struct.unpack('!f', bytes.fromhex('{0:02x}'.format(hexVal[i*2]) + '{0:02x}'.format(hexVal[i*2+1])))[0]
                except:
                    pass
            s = "Values: " + str(Value) + "\n"
            print(s)
            lo_file.write(s)

            
        if layer4.funcCode == 0x3:
            # Request read registers

            layer1 = packet.getlayer(1)
            layer2 = packet.getlayer(2)
            layer3 = packet.getlayer(3)
            
            IP_src = layer1.src
            IP_dst = layer1.dst
            sport = layer2.sport
            dport = layer2.dport

            numReg = layer4.quantity/2
            Trans_ID = layer3.transId
            addr = layer4.startAddr

            # print out info on request
            date = str(datetime.datetime.now()).split('.')[0]
            s = "[%s] Read Registers ID: %u IP: %s:%u --> %s:%u Start Address: %d #Addresses: %d\n" % (date,Trans_ID, IP_src, sport, IP_dst, dport, addr, numReg)
            print(s)
            lo_file.write(s)

            # Save the transaction ID and memory address
            # These are needed on the response packet side to know what address values came from
            if Trans_ID not in ID:
                ID.append(Trans_ID)
                Address.append(addr)

    if mb.ModbusADUResponse in packet:
        # Packet is a modbus response
        #packet.show()
        global Last_reg
        
        layer4 = packet.getlayer(4)

        if layer4.funcCode == 0x3:
            #Read registers response

            layer1 = packet.getlayer(1)
            layer2 = packet.getlayer(2)
            layer3 = packet.getlayer(3)
            IP_src = layer1.src
            IP_dst = layer1.dst
            sport = layer2.sport
            dport = layer2.dport

            bytecount = layer4.byteCount/4
            #print(bytecount)
            hexVal = layer4.registerVal
            Trans_ID = layer3.transId
            
            # Try to find transaction ID in ID list. If its not there,
            # it was probably the last ID and mem address too, esp on loopback
            # Hopefully wont be confused with a bunch of PLCs otherwise need to add
            # filter on dst and src IPs.
            if Trans_ID in ID:
                idx = ID.index(Trans_ID)
                Register = Address[idx]
                del ID[idx]
                del Address[idx]     #Don't want memory killing sized list
                Last_reg = Register
            else:
                Register = Last_reg
            Value = [0] * int(bytecount)
            date = str(datetime.datetime.now()).split('.')[0]
            s = "[%s] Read Registers ID: %u IP: %s:%u --> %s:%u Memory Address: %d\n" % (date, Trans_ID, IP_src, sport, IP_dst, dport, Register)
            print(s)
            #layer4.show()
            lo_file.write(s)

            # Try to decode and print 32bit floats
            
            for i in range(0,int(bytecount)):
                try:
                    mypack = struct.pack('>HH',hexVal[i*2],hexVal[i*2+1])
                    Value[i] = struct.unpack('>f',mypack)[0]
                except:
                    pass
            
            s = "Values: " + str(Value) + "\n"
            print(s)
            lo_file.write(s)

            

def gotpacket_eth(packet):
    #Same as gotpacket_lo but different logs to eth_log.txt
    #check if packet is Modbus Request
    if mb.ModbusADURequest in packet:
        #packet.show()
        # Get layer info to determine what function is called
        layer4 = packet.getlayer(4)

        if layer4.funcCode == 0x10:
            # Write Register function code with values

            layer1 = packet.getlayer(1)
            layer2 = packet.getlayer(2)
            layer3 = packet.getlayer(3)

            # Collect packet info
            IP_src = layer1.src
            IP_dst = layer1.dst
            sport = layer2.sport
            dport = layer2.dport
            
            
            numReg = layer4.quantityRegisters/2
            hexVal = layer4.outputsValue
            addr = layer4.startAddr
            Value = [0] * int(numReg)

            #write transaction information to file and print out to cmd
            date = str(datetime.datetime.now()).split('.')[0]
            s = "[%s] Write Registers IP: %s:%u --> %s:%u Memory Address: %d\n" % (date, IP_src, sport, IP_dst, dport, addr)
            print(s)
            eth_file.write(s)
            
            # Attempt to decode values, sometimes fails due to incomplete packet.
            for i in range(0,int(numReg)):
                try:
                    mypack = struct.pack('>HH',hexVal[i*2],hexVal[i*2+1])
                    Value[i] = struct.unpack('>f',mypack)[0]
                    #Value[i] = struct.unpack('!f', bytes.fromhex('{0:02x}'.format(hexVal[i*2]) + '{0:02x}'.format(hexVal[i*2+1])))[0]
                except:
                    pass
            s = "Values: " + str(Value) + "\n"
            print(s)
            eth_file.write(s)

            
        if layer4.funcCode == 0x3:
            # Request read registers

            layer1 = packet.getlayer(1)
            layer2 = packet.getlayer(2)
            layer3 = packet.getlayer(3)
            
            IP_src = layer1.src
            IP_dst = layer1.dst
            sport = layer2.sport
            dport = layer2.dport

            numReg = layer4.quantity/2
            Trans_ID = layer3.transId
            addr = layer4.startAddr

            # print out info on request
            date = str(datetime.datetime.now()).split('.')[0]
            s = "[%s] Read Registers ID: %u IP: %s:%u --> %s:%u Start Address: %d #Addresses: %d\n" % (date, Trans_ID, IP_src, sport, IP_dst, dport, addr, numReg)
            print(s)
            eth_file.write(s)

            # Save the transaction ID and memory address
            # These are needed on the response packet side to know what address values came from
            if Trans_ID not in ID:
                ID.append(Trans_ID)
                Address.append(addr)

    if mb.ModbusADUResponse in packet:
        # Packet is a modbus response
        #packet.show()
        global Last_reg
        
        layer4 = packet.getlayer(4)

        if layer4.funcCode == 0x3:
            #Read registers response

            layer1 = packet.getlayer(1)
            layer2 = packet.getlayer(2)
            layer3 = packet.getlayer(3)
            IP_src = layer1.src
            IP_dst = layer1.dst
            sport = layer2.sport
            dport = layer2.dport

            bytecount = layer4.byteCount/4
            #print(bytecount)
            hexVal = layer4.registerVal
            Trans_ID = layer3.transId
            
            # Try to find transaction ID in ID list. If its not there,
            # it was probably the last ID and mem address too, esp on loopback
            # Hopefully wont be confused with a bunch of PLCs otherwise need to add
            # filter on dst and src IPs.
            if Trans_ID in ID:
                idx = ID.index(Trans_ID)
                Register = Address[idx]
                del ID[idx]
                del Address[idx]     #Don't want memory killing sized list
                Last_reg = Register
            else:
                Register = Last_reg
            Value = [0] * int(bytecount)
            date = str(datetime.datetime.now()).split('.')[0]
            s = "[%s] Read Registers ID: %u IP: %s:%u --> %s:%u Memory Address: %d\n" % (date, Trans_ID, IP_src, sport, IP_dst, dport, Register)
            print(s)
            #layer4.show()
            eth_file.write(s)

            # Try to decode and print 32bit floats
            
            for i in range(0,int(bytecount)):
                try:
                    mypack = struct.pack('>HH',hexVal[i*2],hexVal[i*2+1])
                    Value[i] = struct.unpack('>f',mypack)[0]
                except:
                    pass
            
            s = "Values: " + str(Value) + "\n"
            print(s)
            eth_file.write(s)

# Set up threads for each sniff call
# enable keyboard interupts to stop and close files
def lo_thread():
    try:
        sniff(iface=interface[0], filter="port 502", prn=gotpacket_lo)
    except KeyboardInterrupt:
        lo_file.close()

def eth_thread():
    try:
        sniff(iface=interface[1], filter="port 502", prn=gotpacket_eth)
    except KeyboardInterrupt:
        eth_file.close()

if __name__ == "__main__":
    #scan for network adaptors
    faces = netifaces.interfaces()
    print("Network interfaces: " + str(faces))
    interface = [None, None]
    # See if any network adaptor names match what we expect for loopback and ethernet
    for i in range(len(faces)):
        if "lo" in faces[i]:
            interface[0] = faces[i]
        if "ens" in faces[i] and interface[1] is None:
            interface[1] = faces[i]
        
    Pass_check = False
    Enable_rec = [True, True]
    
    # Ask user if found defaults are okay, if not ask them for
    # the correct adaptor names.
    if interface[0] is not None and interface[1] is not None:
        print("Default devices set to: " + str(interface))
        Defaults = input("Defaults Okay? [Y/n]: ") or None
        if Defaults is None or Defaults == "Y" or Defaults == "y":
            pass
        else:
            print("Network Devices: " + str(faces))
            interface[0] = input("Loopback Device: ") or None
            interface[1] = input("Ethernet Device: ") or None
            Pass_check = True

    # Check that we have interface names, ask about them if we havent already
    # Disable recording if we dont have an interface name and already asked.
    if interface[0] is None:
        if Pass_check:
            print("No Loopback device. Loopback recording disabled.")
            Enable_rec[0] = False
        else:
            print("No loopback device found!\n Enter device name from list, or hit enter to disbale loopback recording.")
            print("Network Devices: " + str(faces))
            interface[0] = input("Loopback Device: ") or None
            if interface[0] is None:
                Enable_rec[0] = False
                print("No Loopback device. Loopback recording disabled.")

    if interface[1] is None:
        if Pass_check:
            print("No ethernet device. Ethernet recording disabled.")
            Enable_rec[1] = False
        else:
            print("No ethernet device found!\n Enter device name from list, or hit enter to disbale ethernet recording.")
            print("Network Devices: " + str(faces))
            interface[1] = input("Ethernet Device: ") or None
            if interface[1] is None:
                Enable_rec[1] = False
                print("No ethernet device. Ethernet recording disabled.")

    # If we have target adaptors, start threads
    if Enable_rec[0]:
        lo_rec = threading.Thread(target=lo_thread, daemon=True)
        lo_rec.start()
    
    if Enable_rec[1]:
        eth_rec = threading.Thread(target=eth_thread, daemon=True)
        eth_rec.start()
    
    # If the thread exists we need to join
    if Enable_rec[0]:
        lo_rec.join()

    if Enable_rec[1]:
        eth_rec.join()

