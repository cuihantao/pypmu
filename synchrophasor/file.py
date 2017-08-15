
import logging
import linecache
import multiprocessing

from threading import Thread
from multiprocessing import Queue
from time import sleep
from synchrophasor.frame import *

class DataFile(object):
    """Contains variables needed by methods performing file operations.
    Currently reads/writes simultaneously. The read thread should fill a buffer, while
    the send thread will transmit the data at the data rate. If the read function
    does not see new lines of data within the timeout period, it will stop"""
    ##TODO: Support for multiple class instances of PMU's for multiport streaming
    def __init__(self, port, pmu, datFile, lstFile, timeout=10):
        self.set_pmu(pmu)
        self.set_ports(port)
        self.set_dat_file(datFile)
        self.set_lst_file(lstFile)
        self.get_col_indexes(lstFile)
        self.data_format = self.pmu.cfg2.get_data_format()
        self.send = False
        self.buffer = True
        self.timeout = timeout
        self.buffer = Queue() ##TODO: multiple client support

        self.data_rate = self.pmu.cfg2.get_data_rate()
        if self.data_rate > 0:
            self.delay = 1.0 / self.data_rate
        else:
            self.delay = -self.data_rate

    def run(self):
        """Starts the data reading/sending process."""
        readThread = Thread(target=self.read_data_file,)
        sendThread = Thread(target=self.send_data_file,)
        self.send = True
        readThread.start()
        sendThread.start()

        readThread.join()
        sendThread.join()
        print("Main thread complete.")

    def read_data_file(self):
        """Reads a line of data from file provided. Starts send data function as a child
        process that sends the slice of data as it is being read. """
        index = 2
        time = 0.0

        while self.send:
            line = linecache.getline(self.datFile, index)
            if line == "":
                linecache.checkcache(self.datFile)        ##Refreshes file contents
                sleep(0.1)
                time += 0.1
                if time > self.timeout:
                    print("Timeout. Data not received in ", self.timeout, " seconds...")
                    self.buffer.put("")
                    break
            else:
                self.buffer.put(line)
                index += 1
        print("read thread complete.")

    def send_data_file(self):
        """Child process of read_data_file. Uses column indexes and slice of data
        to construct and send a data frame."""
        while self.send:
            line = self.buffer.get()
            line = line.split()
            if len(line) != self.num_col:
                if len(line) == 0:
                    print("End of file transmission.")
                    break
                else:
                    raise Exception("The data string does not correspond to the number of variables.")
            alist2 = []
            phasors = []
            stat = [("ok", True, "timestamp", False, False, False, 0, "<10", 0)] * self.num_pmu

            if self.pmu.cfg2._multistreaming:
                for k in range(self.num_pmu):
                    if self.data_format[0]:##polar
                        phasors.append((float(line[self.vmIndexes[k]]), float(line[self.amIndexes[k]])))
                    else:
                        phasors.append((float(line[self.amIndexes[k]]), float(line[self.vmIndexes[k]])))
                        freq = float(line[self.wBusFreqIndexes[k]])
                for j in range(len(phasors)):
                    alist = []
                    alist.append(phasors[j])
                    alist2.append(alist)
                    alist = []
                self.pmu.send_data(alist2, [[]]*14, [[]]*14, [0]*14, [0]*14, stat)
                sleep(self.delay)
            else:
                if self.data_format[0]:
                    phasors = (float(line[self.vmIndexes[0]]), float(line[self.amIndexes[0]]))
                else:
                    phasors = (float(line[self.amIndexes[0]]), (float(line[self.vmIndexes[0]])))
                freq = line[self.wBusFreqIndexes[0]]
                self.pmu.send_data(phasors)
                sleep(self.delay)
        print("Write thread complete.")

    def get_col_indexes(self, lstFile):
        """Using lst file, retrieves indexes of columns that corerspond to
        variables present in the dat file."""
        self.vmIndexes = []
        self.amIndexes = []
        self.wBusFreqIndexes = []
        self.xtBusFreqIndexes = []
        self.thetaBusIndexes = []
        self.vmBusIndexes = []

        for i in range(self.num_col):## get indexes
            line = linecache.getline(lstFile, i)
            if "vm PMU" in line:
                self.vmIndexes.append(i-1)
            elif "am PMU" in line:
                self.amIndexes.append(i-1)
            elif "w BusFreq" in line:
                self.wBusFreqIndexes.append(i-1)
            elif "xt BusFreq" in line:
                self.xtBusFreqIndexes.append(i-1)
            elif "theta Bus" in line:
                self.thetaBusIndexes.append(i-1)
            elif "vm Bus" in line:
                self.vmBusIndexes.append(i-1)

    def set_pmu(self, pmu):
        self.pmu = pmu
        self.num_pmu = pmu.cfg2.get_num_pmu()

    def set_ports(self, ports):
        self.ports = ports
        if ports < self.num_pmu:
            raise Exception("Cannot be more ports than PMU's")

    def set_dat_file(self, datFile):
        """datFile is a string with the name of the file in use."""
        if datFile[len(datFile)-3:len(datFile)] != "dat":
            raise Exception(".dat filetype is required")
        self.datFile = datFile

        dat = open(datFile, "r")
        self.num_col = int(dat.readline())##number of columns, AKA num of vars
        dat.close()

    def set_lst_file(self, lstFile):
        """string representing name of .lst file wtih variables"""
        if lstFile[len(lstFile)-3:len(lstFile)] != "lst":
            raise Exception("lst filetype required.")
        self.lstFile = lstFile

    @staticmethod
    def parse_cfg(lstFile):
        """Reads the lst file and retrieves information needed for config and
        sending the data."""
