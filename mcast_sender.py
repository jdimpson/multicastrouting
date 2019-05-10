#!/usr/bin/python

# heavily modified from https://pymotw.com/2/socket/multicast.html

import socket
import struct

from sys  import argv
from time import sleep

multicast_group = '239.255.0.1'
port = 11111
ttl = 10
delay=1

for a in argv:
    n=None
    i=a.find("=")+1
    if i >= 0:
        n=a[i:]
    if a.startswith("group=") or a.startswith("addr"):
        multicast_group = n
    elif a.startswith("port="):
        port = int(n)
    elif a.startswith("ttl="):
        ttl = int(n)
    elif a.startswith("delay="):
        delay=float(n)


server_address = ('', port)
 
print "group={} port={} ttl={} delay={}".format(multicast_group, port, ttl, delay)

group = (multicast_group, port)

# Create the datagram socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Set a timeout so the socket does not block indefinitely when trying
# to receive data.
sock.settimeout(0.2)

# Setting the time-to-live for messages to 1 will make it so that
# they do NOT leave the local network segment.
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', ttl))

try:
    i = 0
    while True:
        mesg = "{}\n".format(i)
        print mesg,
        sent = sock.sendto(mesg, group)
        #try: data, server = sock.recvfrom(16)
        #except socket.timeout: break
        #else: print 'received "%s" from %s' % (data, server)
        i+=1
        sleep(delay)

finally:
    sock.close()
