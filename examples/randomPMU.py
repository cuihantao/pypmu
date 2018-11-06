import random

from synchrophasor.frame import ConfigFrame2
from synchrophasor.pmu import Pmu


"""
randomPMU will listen on ip:port for incoming connections.
After request to start sending measurements - random
values for phasors will be sent.
"""


if __name__ == "__main__":

    pmu = Pmu(ip="127.0.0.1", port=1410)
    pmu.logger.setLevel("DEBUG")

    cfg = ConfigFrame2(1410,  # PMU_ID
                       1000000,  # TIME_BASE
                       1,  # Number of PMUs included in data frame
                       "Random Station",  # Station name
                       1410,  # Data-stream ID(s)
                       (True, True, True, True),  # Data format - POLAR; PH - REAL; AN - REAL; FREQ - REAL;
                       3,  # Number of phasors
                       1,  # Number of analog values
                       1,  # Number of digital status words
                       ["VA", "VB", "VC", "ANALOG1", "BREAKER 1 STATUS",
                        "BREAKER 2 STATUS", "BREAKER 3 STATUS", "BREAKER 4 STATUS", "BREAKER 5 STATUS",
                        "BREAKER 6 STATUS", "BREAKER 7 STATUS", "BREAKER 8 STATUS", "BREAKER 9 STATUS",
                        "BREAKER A STATUS", "BREAKER B STATUS", "BREAKER C STATUS", "BREAKER D STATUS",
                        "BREAKER E STATUS", "BREAKER F STATUS", "BREAKER G STATUS"],  # Channel Names
                       [(0, "v"), (0, "v"),
                        (0, "v")],  # Conversion factor for phasor channels - (float representation, not important)
                       [(1, "pow")],  # Conversion factor for analog channels
                       [(0x0000, 0xffff)],  # Mask words for digital status words
                       50,  # Nominal frequency
                       1,  # Configuration change count
                       30)  # Rate of phasor data transmission)

    pmu.set_configuration(cfg)
    pmu.set_header("Hey! I'm randomPMU! Guess what? I'm sending random measurements values!")

    pmu.run()
    stored=[]
    i=0
    while True:


        if pmu.clients:  # Check if there is any connected PDCs
            savedata = input('press 0 if you want to save data, press 1 for sending bad data, normal operation otherwise:')
            if savedata == '0':
# savedata will be replaced with the data that has been sent from hacker.py
                print('Storing Data')
                input1 = random.uniform(215.0, 240.0)
                input2 = random.uniform(-0.1, 0.3)
                input3 = random.uniform(215.0, 240.0)
                input4 = random.uniform(1.9, 2.2)
                input5 = random.uniform(215.0, 240.0)
                input6 = random.uniform(3.0, 3.14)
                pmu.send_data(phasors=[(input1, input2),
                                       (input3, input4),
                                       (input5, input6)],
                              analog=[9.91],
                              digital=[0x0001])
                stored.append(input1)
                stored.append(input2)
                stored.append(input3)
                stored.append(input4)
                stored.append(input5)
                stored.append(input6)
            elif savedata == '1':
#hackerPMU starts injecting stored data. This will be replaced with data from hacker.py
                print('Sending Bad Data')
                pmu.send_data(phasors=[(stored[i], stored[i+1]),
                                       (stored[i+2], stored[i+3]),
                                       (stored[i+4], stored[i+5])],
                              analog=[9.91],
                              digital=[0x0001])
                i+=6
            else:
                print ('Normal Condition')
                pmu.send_data(phasors=[(random.uniform(215.0, 240.0), random.uniform(-0.1, 0.3)),
                                       (random.uniform(215.0, 240.0), random.uniform(1.9, 2.2)),
                                       (random.uniform(215.0, 240.0), random.uniform(3.0, 3.14))],
                              analog=[9.91],
                              digital=[0x0001])

    pmu.join()
