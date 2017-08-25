from synchrophasor.pmu import Pmu
from synchrophasor.frame import ConfigFrame2
from synchrophasor.file import DataFile

"""
tinyPMU will listen on ip:port for incoming connections.
When tinyPMU receives command to start sending
measurements - fixed (sample) measurement will
be sent.
"""


if __name__ == "__main__":
##TODO: support for non-multistreaming here. Also, replace hard coding with actual values from file.
    pmu = Pmu(ip="0.0.0.0", port=1410)
    pmu.logger.setLevel("DEBUG")

    station_names =  ["Station A", "Station B", "Station C", "Station D", "Station E", "Station F", "Station G", "Station H", "Station I", "Station J",
                                                           "Station K", "Station L", "Station M", "Station N"]
    phasor_ids = [1]*14
    data_format = [(True, True, True, True)] * 14

    channel_names = [["aname!"]] * 14
    ph_units = [[(915527, "v")]] * 14

    an_units = [[]]*14
    dig_units = [[]]*14
    fnom = [60]*14
    cfgcount = [1]*14

    cfg = ConfigFrame2(7734, 1000000, 14, station_names, phasor_ids, data_format,
                                          phasor_ids, [0]*14, [0]*14,
                                         channel_names,
                                         ph_units,
                                         an_units,
                                         dig_units, fnom, cfgcount, 30)


    pmu.set_configuration(cfg)

    pmu.set_header()  # This will load default header message "Hello I'm tinyPMU!"

    data_file = DataFile(1411,pmu,"ieee14_vsc_out.dat", "ieee14_vsc_out.lst", loop=True)

    pmu.run()  # PMU starts listening for incoming connections

    while True:
        if pmu.clients:  # Check if there is any connected PDCs
            data_file.run()
            break

    pmu.join()
