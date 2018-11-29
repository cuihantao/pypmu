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

pmunumber = 8

if __name__ == "__main__":
    pdc1 = Pdc(pdc_id=7, pmu_ip=iplist[0], pmu_port=1410)

    pdc1.logger.setLevel("DEBUG")

    pdc1.run()  # Connect to PMU

    header = pdc1.get_header()  # Get header message from PMU
    config = pdc1.get_config()  # Get configuration from PMU
    pdc1.start()  # Request to start sending measurements

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
        data1.join()

