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
import socket
import sys
import os

bufferSize          = 128*1000
serverAddressPort   = ("255.255.255.255", 8000)
# Create a UDP socket at client side
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPClientSocket.bind(serverAddressPort)

def main():
    while True:
        msgFromServer = UDPClientSocket.recvfrom(bufferSize)
        #msg = "Message from Server {}".format(msgFromServer[0])
        msg = str(msgFromServer[0],'UTF-8')
        print(msg)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        UDPClientSocket.close()
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
