from synchrophasor.pmu import Pmu
from synchrophasor.frame import ConfigFrame2
from synchrophasor.file import DataFile

"""
tinyPMU will listen on ip:port for incoming connections.
When tinyPMU receives command to start sending
measurements - fixed (sample) measurement will
be sent.
"""

case_name = 'WECC_OSI'
bus_range = slice(0, 181)

dat = case_name + '_out.dat'
lst = case_name + '_out.lst'


def bus_names_from_lst(lst):
    """Extract bus names from Andes lst file"""
    names = list()
    with open(lst, 'r') as f:
        raw_data = f.read()
    raw_data = raw_data.split('\n')

    for line in raw_data:
        if '$\\theta\\' in line:
            tmp1 = line.split('theta')[1]
            names.append(tmp1.split(',')[0].strip())

    return names, len(names)


if __name__ == "__main__":
    # TODO: support for non-multistreaming here. Also, replace hard coding with actual values from file.
    pmu = Pmu(ip="0.0.0.0", port=1410)
    pmu.logger.setLevel("DEBUG")

    # station_names =  ["Station A", "Station B", "Station C", "Station D", "Station E", "Station F", "Station G", "Station H", "Station I", "Station J",
    #                                                        "Station K", "Station L", "Station M", "Station N"]
    # station_names = ["Station " + str(i) for i in range(nBus)]

    station_names, nBus = bus_names_from_lst(lst)
    station_names = station_names[bus_range]
    nbus = len(station_names)

    phasor_ids = [1]*nBus
    data_format = [(True, True, True, True)] * nBus

    channel_names = [["aname!"]] * nBus
    ph_units = [[(915527, "v")]] * nBus

    an_units = [[]]*nBus
    dig_units = [[]]*nBus
    fnom = [60]*nBus
    cfgcount = [1]*nBus

    cfg = ConfigFrame2(7734, 1000000, nBus, station_names, phasor_ids, data_format,
                                          phasor_ids, [0]*nBus, [0]*nBus,
                                         channel_names,
                                         ph_units,
                                         an_units,
                                         dig_units, fnom, cfgcount, 30)


    pmu.set_configuration(cfg)

    pmu.set_header()  # This will load default header message "Hello I'm tinyPMU!"

    data_file = DataFile(1411, pmu, dat, lst, loop=True)

    pmu.run()  # PMU starts listening for incoming connections

    while True:
        if pmu.clients:  # Check if there is any connected PDCs
            data_file.run()
            break

    pmu.join()
