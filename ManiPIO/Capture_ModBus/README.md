# Capture_Modbus

(C) Copyright 2020 National Technology and Engineering Solutions of Sandia, LLC . Under the terms of Contract DE-NA0003525,
there is a non-exclusive license for use of this work by or on behalf of the U.S. Government. 
Export of this program may require a license from the United States Government.

Capture_Modbus is a python script based on scapy that captures and records Modbus traffic on the 
loopback and external networks.

## Installation

Depends on scapy and made for python 3, but should work on python 2.
Scapy likes to use libpcap, so best to install it too. Alternatively
scapy can use tcpdump. Windows is not recommended but possible. Follow the scapy
windows install instructions: [https://scapy.readthedocs.io/en/latest/installation.html#windows]

```bash
sudo apt install libpcap-dev
pip3 install --pre scapy[complete]
```

## Usage

To access the network hardware, Capture_Modbus needs to be run as root.
Follow on screen instructions, point program to hardware to capture from if you 
don't want the defaults.
Program will output files eth_log.txt and lo_log.txt
eth_log is recorded from the ethernet adaptor
lo_log is recorded from the internal loopback

```bash
$ sudo python3 ./Capture_Modbus.py
Network interfaces: ['lo', 'ens33']
Default devices set to: ['lo', 'ens33']
Defaults Okay? [Y/n]: Y

```




