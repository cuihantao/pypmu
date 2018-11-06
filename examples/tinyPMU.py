from synchrophasor.pmu import Pmu
import socket
import sys
from multiprocessing import Process

"""
tinyPMU will listen on ip:port for incoming connections.
When tinyPMU receives command to start sending
measurements - fixed (sample) measurement will
be sent.
"""
s = socket.socket()
s.bind(('0.0.0.0',12345))
s.listen(5)
if __name__ == "__main__":

    pmu = Pmu(ip="127.0.0.1", port=1410)
    pmu.logger.setLevel("DEBUG")

    pmu.set_configuration()  # This will load default PMU configuration specified in IEEE C37.118.2 - Annex D (Table D.2)
    pmu.set_header()  # This will load default header message "Hello I'm tinyPMU!"

    pmu.run()  # PMU starts listening for incoming connections

    while True:
        if pmu.clients:  # Check if there is any connected PDCs
            pmu.send(pmu.ieee_data_sample)  # Sending sample data frame specified in IEEE C37.118.2 - Annex D (Table D.1)
        c, addr = s.accept()
        print ('Got connection from' , addr)
        print (c.recv(1024))
        message = c.recv(1024)
        if message != None:
            print('Disconnected')
            sys.exit()
        c.close()
    pmu.join()
