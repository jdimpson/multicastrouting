#!/usr/bin/python

# heavily modified from https://pymotw.com/2/socket/multicast.html

import socket
import struct
import sys
from sys import argv

multicast_group = '239.255.0.1'
port = 11111
quiet = False

for a in argv:
    n=None
    i=a.find("=")+1
    if i >= 0:
        n=a[i:]
    if a.startswith("group=") or a.startswith("addr"):
        multicast_group = n
    elif a.startswith("port="):
        port = int(n)
    elif a.startswith("quiet"):
        quiet=True

server_address = ('', port)

print "group={} port={} {}".format(multicast_group, port, "quiet" if quiet else "")

# Create the socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind to the server address
sock.bind(server_address)

# Tell the operating system to add the socket to the multicast group
# on all interfaces.
group = socket.inet_aton(multicast_group)
mreq = struct.pack('4sL', group, socket.INADDR_ANY)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

try:
    # Receive/respond loop
    i=0
    while True:
        data, address = sock.recvfrom(1024)
        if not quiet: print data,
        #print i,address
        i+=1
finally:
    # ensure that IGMP leave message gets sent
    sock.close()

