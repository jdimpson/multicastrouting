#!/usr/bin/python

# heavily modified from https://pymotw.com/2/socket/multicast.html

import socket
import struct
import sys
from threading import Thread,Event
from Queue import Queue
from time import time
from sys import argv

try:
    from statistics import mean,stdev
except ImportError as e:
    havestats = False
else:
    havestats = True

class mcast_joiner(object):

    def __init__(self,group,port,collect_stats=False):
        self.collect_stats = collect_stats
        self.records = []
        self.intervals = []
        self.sizes = []
        self.missing = {}
        self.report = {}
        self.port = port
        self.group = group
        self.q = Queue()
        self.ev = Event()
        self.ev.set()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        server_address = ('', self.port)
        self.sock.bind(server_address)

        # Tell the operating system to add the socket to the multicast group
        # on all interfaces.
        pgroup = socket.inet_aton(self.group)
        mreq = struct.pack('4sL', pgroup, socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # TODO: set timeout behaviour, although maybe not as import 
        # now that thread is daemon

        self.t = Thread(target=self.run)
        self.t.daemon = True
        self.t.start()

    def run(self):
        try:
            # Receive/respond loop
            i=0
            while self.ev.is_set():
                data, address = self.sock.recvfrom(1024)
                self.q.put((i,data,address,time()))
                i+=1
        finally:
            # ensure that IGMP leave message gets sent
            self.sock.close()
            self.sock = None
        return

    def close(self):
        self.ev.clear()
        self.t = None

    def __iter__(self):
        return self

    def __next__(self):
        n = self.q.get()
        if self.collect_stats:
            self.records.append(n)
        return n

    def updatestats(self):
        if "packets" in self.report:
            startp = self.report["packets"]
        else:
            startp = 0

        if "lastrec" in self.report: 
            lastseq = int(self.report["lastrec"][1].rstrip())
            lasttime = self.report["lastrec"][3]
        else:
            lastseq=int(self.records[0][1].rstrip())
            lasttime=self.records[0][3]

        if "cumsize" in self.report:
            cumsize = self.report["cumsize"]
        else:
            cumsize = 0

        if "firstrec" not in self.report:
            self.report["firstrec"] = self.records[0]        

        if "highestseq" in self.report:
            highestseq = self.report["highestseq"]
        else:
            highestseq = int(self.records[0][1].rstrip())

        for n in self.records[startp:]:
            i,seq,address,time = n
            size = len(seq)
            cumsize += size
            self.sizes.append(size)

            seq = int(seq.rstrip())
            if "firstseq" not in self.report:
                self.report["firstseq"] = seq
            if seq > lastseq + 1:
                for i in xrange(lastseq+1, seq):
                    self.missing[i] = "missing"

            if seq in self.missing:
                if self.missing[seq] == "missing":
                    self.missing[seq] = "late"
                elif self.missing[seq].startswith("received"):
                    self.missing[seq] = "received, duplicate"
                else:
                    self.missing[seq] = "WTF?"
            else:
                self.missing[seq] = "received"
                lastseq = seq
            if seq > highestseq: highestseq = seq

            tdiff = time - lasttime
            lasttime = time
            self.intervals.append(tdiff)

            self.report["lastrec"] = n

        self.report["highestseq"] = highestseq
        self.report["totaltime"] = self.report["lastrec"][3] - self.report["firstrec"][3]
        self.report["cumsize"] = cumsize
        if havestats:
            self.report["averageinterval"] = mean(self.intervals[1:])
            self.report["jitter"] = stdev(self.intervals[1:])
        self.report["packets"] = len(self.records)
        self.report["bps"] = self.report["cumsize"]*8 / self.report["totaltime"]
        self.report["pps"] = self.report["packets"] / self.report["totaltime"]
  
    def next(self):
        return self.__next__()

if __name__ == "__main__":
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

    print "group={} port={} {}".format(multicast_group, port, "quiet" if quiet else "")

    mj = mcast_joiner(group=multicast_group,port=port,collect_stats=True)
    i=0
    try:
        mj.connect()
        print "ready!"
        for d in mj:
            if not quiet: print d[3],d[1],
            i+=1
            if i % 50 == 0:
                mj.updatestats()
                for k in ["cumsize", "totaltime", "packets", "bps", "pps","averageinterval","jitter","firstseq","highestseq" ]:
                    if k in mj.report:
                        if isinstance(mj.report[k],float):
                            v=round(mj.report[k],5)
                        else:
                            v=mj.report[k]
                        print "{k: <16}: {v}".format(k=k,v=v)
                for h in xrange(mj.report["firstseq"],mj.report["highestseq"]+1):
                    if h in mj.missing:
                        x=mj.missing[h]
                        if x != "received":
                            print "{}: {}".format(h,x)
                print "\n\n"
    except KeyboardInterrupt as e:
        mj.close()
