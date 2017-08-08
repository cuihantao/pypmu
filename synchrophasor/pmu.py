import socket
import logging
import linecache

from select import select
from threading import Thread
from multiprocessing import Queue
from multiprocessing import Process
from sys import stdout
from time import sleep
from synchrophasor.frame import *


__author__ = "Stevan Sandi"
__copyright__ = "Copyright (c) 2016, Tomo Popovic, Stevan Sandi, Bozo Krstajic"
__credits__ = []
__license__ = "BSD-3"
__version__ = "1.0.0-alpha"


class Pmu(object):

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(stdout)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


    def __init__(self, pmu_id=7734, data_rate=30, port=4712, ip="127.0.0.1",
                 method="tcp", buffer_size=2048, set_timestamp=True):

        self.port = port
        self.ip = ip

        self.socket = None
        self.listener = None
        self.set_timestamp = set_timestamp
        self.buffer_size = buffer_size

        self.ieee_cfg2_sample = ConfigFrame2(pmu_id, 1000000, 1, "Station A", 7734, (False, False, True, False),
                                             4, 3, 1,
                                             ["VA", "VB", "VC", "I1", "ANALOG1", "ANALOG2", "ANALOG3",
                                              "BREAKER 1 STATUS", "BREAKER 2 STATUS", "BREAKER 3 STATUS",
                                              "BREAKER 4 STATUS", "BREAKER 5 STATUS", "BREAKER 6 STATUS",
                                              "BREAKER 7 STATUS", "BREAKER 8 STATUS", "BREAKER 9 STATUS",
                                              "BREAKER A STATUS", "BREAKER B STATUS", "BREAKER C STATUS",
                                              "BREAKER D STATUS", "BREAKER E STATUS", "BREAKER F STATUS",
                                              "BREAKER G STATUS"],
                                             [(915527, "v"), (915527, "v"), (915527, "v"), (45776, "i")],
                                             [(1, "pow"), (1, "rms"), (1, "peak")], [(0x0000, 0xffff)],
                                             60, 22, data_rate)

        self.ieee_data_sample = DataFrame(pmu_id, ("ok", True, "timestamp", False, False, False, 0, "<10", 0),
                                          [(14635, 0), (-7318, -12676), (-7318, 12675), (1092, 0)], 2500, 0,
                                          [100, 1000, 10000], [0x3c12], self.ieee_cfg2_sample)

        self.ieee_command_sample = CommandFrame(pmu_id, "start", None)

        self.cfg1 = self.ieee_cfg2_sample
        self.cfg1.__class__ = ConfigFrame1   # Casting CFG2 to CFG1
        self.cfg2 = self.ieee_cfg2_sample
        self.cfg3 = None
        self.header = HeaderFrame(pmu_id, "Hi! I am tinyPMU!")

        self.method = method
        self.clients = []
        self.client_buffers = []


    def set_id(self, pmu_id):

        self.cfg1.set_id_code(pmu_id)
        self.cfg2.set_id_code(pmu_id)
        # self.cfg3.set_id_code(id)

        # Configuration changed - Notify all PDCs about new configuration
        self.send(self.cfg2)
        # self.send(self.cfg3)

        self.logger.info("[%d] - PMU Id changed.", self.cfg2.get_id_code())


    def set_configuration(self, config=None):

        # If none configuration given IEEE sample configuration will be loaded
        if not config:
            self.cfg1 = self.ieee_cfg2_sample
            self.cfg1.__class__ = ConfigFrame1  # Casting CFG-2 to CFG-1
            self.cfg2 = self.ieee_cfg2_sample
            self.cfg3 = None  # TODO: Configuration frame 3

        elif type(config) == ConfigFrame1:
            self.cfg1 = config

        elif type(config) == ConfigFrame2:
            self.cfg2 = config
            if not self.cfg1:  # If CFG-1 not set use current data stream configuration
                self.cfg1 = config
                self.cfg1.__class__ = ConfigFrame1

        elif type(config) == ConfigFrame3:
            self.cfg3 = ConfigFrame3

        else:
            raise PmuError("Incorrect configuration!")

        self.logger.info("[%d] - PMU configuration changed.", self.cfg2.get_id_code())


    def set_header(self, header=None):

        if isinstance(header, HeaderFrame):
            self.header = header
        elif isinstance(header, str):
            self.header = HeaderFrame(self.cfg2.get_id_code(), header)
        else:
            PmuError("Incorrect header setup! Only HeaderFrame and string allowed.")

        # Notify all connected PDCs about new header
        self.send(self.header)

        self.logger.info("[%d] - PMU header changed.", self.cfg2.get_id_code())


    def set_data_rate(self, data_rate):

        self.cfg1.set_data_rate(data_rate)
        self.cfg2.set_data_rate(data_rate)
        # self.cfg3.set_data_rate(data_rate)
        self.data_rate = data_rate

        # Configuration changed - Notify all PDCs about new configuration
        self.send(self.cfg2)
        # self.send(self.cfg3)

        self.logger.info("[%d] - PMU reporting data rate changed.", self.cfg2.get_id_code())


    def set_data_format(self, data_format):

        self.cfg1.set_data_format(data_format, self.cfg1.get_num_pmu())
        self.cfg2.set_data_format(data_format, self.cfg2.get_num_pmu())
        # self.cfg3.set_data_format(data_format, self.cfg3.get_num_pmu())

        # Configuration changed - Notify all PDCs about new configuration
        self.send(self.cfg2)
        # self.send(self.cfg3)

        self.logger.info("[%d] - PMU data format changed.", self.cfg2.get_id_code())


    def send(self, frame):

        if not isinstance(frame, CommonFrame) and not isinstance(frame, bytes):
            raise PmuError("Invalid frame type. send() method accepts only frames or raw bytes.")

        for buffer in self.client_buffers:
            buffer.put(frame)


    def send_data(self, phasors=[], analog=[], digital=[], freq=0, dfreq=0,
                  stat=("ok", True, "timestamp", False, False, False, 0, "<10", 0), soc=None, frasec=None):
        #TODO: I broke this, going to put a bandaid on this until I get an internet connection
        i = 0
        # PH_UNIT conversion
        #print("initial parameter for phasors: ", phasors)
        if phasors and self.cfg2.get_num_pmu() > 1:  # Check if multistreaming:
            #print("inside if that checks if multistreaming")
            if not (self.cfg2.get_num_pmu() == len(self.cfg2.get_data_format()) == len(phasors)):
                raise PmuError("Incorrect input. Please provide PHASORS as list of lists with NUM_PMU elements.")
            for df in self.cfg2.get_data_format():
                if not df[1]:  # Check if phasor representation is integer
                    print("2nd if not")
                    phasors[i] = map(lambda x: int(x / (0.00001 * self.cfg2.get_ph_units()[i])), phasors[i])
                    print("phasors in send data method: ", phasors)
                elif not self.cfg2.get_data_format()[1]:
                    phasors = map(lambda x: int(x / (0.00001 * self.cfg2.get_ph_units())), phasors)
                    print("phasors in send data method: ", phasors)
                i += 1
                if i > self.cfg2.get_num_pmu():
                    i = 0
                    break
        # AN_UNIT conversion
        if analog and self.cfg2.get_num_pmu() > 1:  # Check if multistreaming:
            if not (self.cfg2.get_num_pmu() == len(self.cfg2.get_data_format()) == len(analog)):
                raise PmuError("Incorrect input. Please provide analog ANALOG as list of lists with NUM_PMU elements.")

            for df in self.cfg2.get_data_format():
                if not df[2]:  # Check if analog representation is integer
                    analog[i] = map(lambda x: int(x / self.cfg2.get_analog_units()[i]), analog[i])
                i += 1
                if i > self.cfg2.get_num_pmu():
                    i = 0
                    break
        elif not self.cfg2.get_data_format()[2]:
            analog = map(lambda x: int(x / self.cfg2.get_analog_units()), analog)
        data_frame = DataFrame(self.cfg2.get_id_code(), stat, phasors, freq, dfreq, analog, digital, self.cfg2)
        #print(self.client_buffers)

        for buffer in self.client_buffers:
            buffer.put(data_frame)

    def run(self):

        if not self.cfg1 and not self.cfg2 and not self.cfg3:
            raise PmuError("Cannot run PMU without configuration.")

        # Create TCP socket, bind port and listen for incoming connections
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.ip, self.port))
        self.socket.listen(5)

        self.listener = Thread(target=self.acceptor)  # Run acceptor thread to handle new connection
        self.listener.daemon = True
        self.listener.start()


    def acceptor(self):

        while True:
            print("acceptor method")
            self.logger.info("[%d] - Waiting for connection on %s:%d", self.cfg2.get_id_code(), self.ip, self.port)

            # Accept a connection on the bound socket and fork a child process to handle it.
            conn, address = self.socket.accept()

            # Create Queue which will represent buffer for specific client and add it o list of all client buffers
            buffer = Queue()
            self.client_buffers.append(buffer)

            process = Process(target=self.pdc_handler, args=(conn, address, buffer, self.cfg2.get_id_code(),
                                                             self.cfg2.get_data_rate(), self.cfg1, self.cfg2,
                                                             self.cfg3, self.header, self.buffer_size,
                                                             self.set_timestamp, self.logger.level))
            process.daemon = True
            process.start()
            self.clients.append(process)

            # Close the connection fd in the parent, since the child process has its own reference.
            conn.close()


    def join(self):

        while self.listener.is_alive():
            self.listener.join(0.5)


    @staticmethod
    def pdc_handler(connection, address, buffer, pmu_id, data_rate, cfg1, cfg2, cfg3, header,
                    buffer_size, set_timestamp, log_level):

        # Recreate Logger (handler implemented as static method due to Windows process spawning issues)
        logger = logging.getLogger(address[0]+str(address[1]))
        logger.setLevel(10)
        handler = logging.StreamHandler(stdout)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        print("pdc handler")
        logger.info("[%d] - Connection from %s:%d", pmu_id, address[0], address[1])

        # Wait for start command from connected PDC/PMU to start sending
        sending_measurements_enabled = False

        # Calculate delay between data frames
        if data_rate > 0:
            delay = 1.0 / data_rate
        else:
            delay = -data_rate
            print(delay)

        try:
            while True:

                command = None
                received_data = b""
                readable, writable, exceptional = select([connection], [], [], 0)  # Check for client commands

                if readable:
                    """
                    Keep receiving until SYNC + FRAMESIZE is received, 4 bytes in total.
                    Should get this in first iteration. FRAMESIZE is needed to determine when one complete message
                    has been received.
                    """
                    while len(received_data) < 4:
                        received_data += connection.recv(buffer_size)

                    bytes_received = len(received_data)
                    total_frame_size = int.from_bytes(received_data[2:4], byteorder="big", signed=False)

                    # Keep receiving until every byte of that message is received
                    while bytes_received < total_frame_size:
                        message_chunk = connection.recv(min(total_frame_size - bytes_received, buffer_size))
                        if not message_chunk:
                            break
                        received_data += message_chunk
                        bytes_received += len(message_chunk)

                    # If complete message is received try to decode it
                    if len(received_data) == total_frame_size:
                        try:
                            received_message = CommonFrame.convert2frame(received_data)  # Try to decode received data

                            if isinstance(received_message, CommandFrame):
                                command = received_message.get_command()
                                logger.info("[%d] - Received command: [%s] <- (%s:%d)", pmu_id, command,
                                            address[0], address[1])
                            else:
                                logger.info("[%d] - Received [%s] <- (%s:%d)", pmu_id,
                                            type(received_message).__name__, address[0], address[1])
                        except FrameError:
                            logger.warning("[%d] - Received unknown message <- (%s:%d)", pmu_id, address[0], address[1])
                    else:
                        logger.warning("[%d] - Message not received completely <- (%s:%d)", pmu_id, address[0], address[1])

                if command:
                    if command == "start":
                        sending_measurements_enabled = True
                        print("\n**start sending activated**\n")
                        logger.info("[%d] - Start sending -> (%s:%d)", pmu_id, address[0], address[1])

                    elif command == "stop":
                        logger.info("[%d] - Stop sending -> (%s:%d)", pmu_id, address[0], address[1])
                        sending_measurements_enabled = False

                    elif command == "header":
                        if set_timestamp: header.set_time()
                        connection.sendall(header.convert2bytes())
                        logger.info("[%d] - Requested Header frame sent -> (%s:%d)",
                                    pmu_id, address[0], address[1])

                    elif command == "cfg1":
                        if set_timestamp: cfg1.set_time()
                        connection.sendall(cfg1.convert2bytes())
                        logger.info("[%d] - Requested Configuration frame 1 sent -> (%s:%d)",
                                    pmu_id, address[0], address[1])

                    elif command == "cfg2":
                        if set_timestamp: cfg2.set_time()
                        connection.sendall(cfg2.convert2bytes())
                        logger.info("[%d] - Requested Configuration frame 2 sent -> (%s:%d)",
                                    pmu_id, address[0], address[1])

                    elif command == "cfg3":
                        if set_timestamp: cfg3.set_time()
                        connection.sendall(cfg3.convert2bytes())
                        logger.info("[%d] - Requested Configuration frame 3 sent -> (%s:%d)",
                                    pmu_id, address[0], address[1])

                if sending_measurements_enabled and not buffer.empty():

                    data = buffer.get()
                    if isinstance(data, CommonFrame):  # If not raw bytes convert to bytes
                        if set_timestamp: data.set_time()
                        data = data.convert2bytes()
                    print("data in pdc handler:", data)
                    sleep(delay)
                    connection.sendall(data)
                    logger.debug("[%d] - Message sent at [%f] -> (%s:%d)",
                                 pmu_id, time(), address[0], address[1])

        except Exception as e:
            print(e)
        finally:
            connection.close()
            logger.info("[%d] - Connection from %s:%d has been closed.", pmu_id, address[0], address[1])

    def send_data_file(self, filename1, filename2):##for use with Hantao Cui's Andes.

        if filename1[len(filename1)-3:len(filename1)] != "lst" or filename2[len(filename2)-3:len(filename2)] != "dat":
            raise Exception("Usage: .lst file, .dat file, stat, cfg")
        ##TODO: Remove lazy hardcoding to default values for send_data func call
        phasors = []
        index = 2
        num_pmu = self.cfg2.get_num_pmu()
        id_code = self.cfg2.get_id_code()
        data_format = self.cfg2.get_data_format()
        phasor_num = self.cfg2.get_phasor_num()
        analog_num = self.cfg2.get_analog_num()
        digital_num = self.cfg2.get_digital_num()
        stat = ("ok", True, "timestamp", False, False, False, 0, "<10", 0)
        stat2 = []
        for i in range(num_pmu):
            stat2.append(stat)
        #print(len(stat))
        #print(stat)
        alist2 = []

        vmIndexes = []
        amIndexes = []
        wBusFreqIndexes = []
        xtBusFreqIndexes = []
        thetaBusIndexes = []
        vmBusIndexes = []

        # lst = open(filename1, "r")
        dat = open(filename2, "r")
        ##print(lst.read())
        num_lines = int(dat.readline())##number of columns, AKA num of vars
        # lst.close()
        dat.close()

        for i in range(num_lines):## get indexes
            line = linecache.getline(filename1, i)
            if "vm PMU" in line:
                vmIndexes.append(i-1)
            elif "am PMU" in line:
                amIndexes.append(i-1)
            elif "w BusFreq" in line:
                wBusFreqIndexes.append(i-1)
            elif "xt BusFreq" in line:
                xtBusFreqIndexes.append(i-1)
            elif "theta Bus" in line:
                thetaBusIndexes.append(i-1)
            elif "vm Bus" in line:
                vmBusIndexes.append(i-1)

        while True:##value retrieval. loop inside while represents 1 line of data, 1 data frame, 1 phasor per pmu?.
            if self.cfg2._multistreaming:
                line = linecache.getline(filename2, index)
                line = line.split()
                if len(line) == 0:
                    break
                for k in range(num_pmu):
                    if data_format[0]:##polar
                        phasors.append((float(line[vmIndexes[k]]), float(line[amIndexes[k]])))
                    else:
                        phasors.append((float(line[amIndexes[k]]), float(line[vmIndexes[k]])))
                        freq = float(line[wBusFreqIndexes[k]])
                for j in range(len(phasors)):
                    alist = []
                    alist.append(phasors[j])
                    alist2.append(alist)
                    alist = []
                if index > 2:
                    del alist2[:len(alist2)-14]
                #print(alist2)
                self.send_data(alist2, [[]]*14, [[]]*14, [0]*14, [0]*14, stat2)
                alist2 = []
            else:
                line = linecache.getline(filename2, index)
                line = line.split()
                if len(line) == 0:
                    break
                if data_format[0]:
                    phasors = (float(line[vmIndexes[0]]), float(line[amIndexes[0]]))
                else:
                    phasors = (float(line[amIndexes[0]]), (float(line[vmIndexes[0]])))
                freq = line[wBusFreqIndexes[0]]
                #print(phasors)
                self.send_data(phasors)
            index += 1
            #print("iteration ", index-2)
            alist2 = []


class PmuError(BaseException):
    pass
