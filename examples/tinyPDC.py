"""
tinyPDC will connect to pmu_ip:pmu_port and send request
for header message, configuration and eventually
to start sending measurements.
"""

from synchrophasor.pdc import Pdc
from synchrophasor.frame import DataFrame
from multiprocessing import Process, Pipe, Queue

iplist = []
iplist.append('127.0.0.1')
iplist.append('127.0.0.2')
iplist.append('127.0.0.3')
iplist.append('127.0.0.4')
iplist.append('127.0.0.5')
iplist.append('127.0.0.6')
iplist.append('127.0.0.7')
iplist.append('127.0.0.8')

pmunumber = 8

if __name__ == "__main__":
    pdc1 = Pdc(pdc_id=7, pmu_ip=iplist[0], pmu_port=1410)
    pdc2 = Pdc(pdc_id=7, pmu_ip=iplist[1], pmu_port=1410)
    pdc3 = Pdc(pdc_id=7, pmu_ip=iplist[2], pmu_port=1410)
    #    pdc4 = Pdc(pdc_id=7, pmu_ip=iplist[3], pmu_port=1410)

    pdc1.logger.setLevel("DEBUG")
    pdc2.logger.setLevel("DEBUG")
    pdc3.logger.setLevel("DEBUG")
    #    pdc4.logger.setLevel("DEBUG")

    pdc1.run()  # Connect to PMU
    pdc2.run()  # Connect to PMU
    pdc3.run()  # Connect to PMU
    #    pdc4.run()  # Connect to PMU

    header = pdc1.get_header()  # Get header message from PMU
    config = pdc1.get_config()  # Get configuration from PMU
    header = pdc2.get_header()  # Get header message from PMU
    config = pdc2.get_config()
    header = pdc3.get_header()  # Get header message from PMU
    config = pdc3.get_config()

    pdc1.start()  # Request to start sending measurements
    pdc2.start()  # Request to start sending measurements
    pdc3.start()  # Request to start sending measurements

    while True:

        Test = []

        result_queue = Queue()
        result_queue1 = Queue()
        result_queue2 = Queue()

        data1 = Process(target=pdc1.get_msg, args=(result_queue,))

        data1.start()
        results = result_queue.get()
        if type(results) == DataFrame:
            print(results.get_measurements())
        data1.terminate()

        data2 = Process(target=pdc2.get_msg, args=(result_queue1,))
        data2.start()
        results1 = result_queue1.get()
        if type(results1) == DataFrame:
            print(results1.get_measurements())
        data2.terminate()

        data3 = Process(target=pdc3.get_msg, args=(result_queue2,))
        data3.start()
        results2 = result_queue2.get()
        if type(results2) == DataFrame:
            print(results2.get_measurements())
        data3.terminate()
