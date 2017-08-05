from synchrophasor.pmu import Pmu
from synchrophasor.frame import ConfigFrame2

"""
tinyPMU will listen on ip:port for incoming connections.
When tinyPMU receives command to start sending
measurements - fixed (sample) measurement will
be sent.
"""


if __name__ == "__main__":

    pmu = Pmu(ip="127.0.0.1", port=1411)
    pmu.logger.setLevel("DEBUG")

    station_names =  ["Station A", "Station B", "Station C", "Station D", "Station E", "Station F", "Station G", "Station H", "Station I", "Station J",
                                                           "Station K", "Station L", "Station M", "Station N"]
    phasor_ids = [1]*14
    data_format = [(True, True, True, True)] * 14
    #channel_names = [["These","Names","Are","For","Testing","Purposes","Only",
    #                 "Please","Disregard","These","Names","That","Are","Here"]]
    channel_names = ["aname!"]
    channel_names2 = []
    for i in range(14):
        channel_names2.append(channel_names)
    ph_units = [(915527, "v")]
    ph_units2 = []
    for i in range(14):
        ph_units2.append(ph_units)
    an_units = [[]]*14
    dig_units = [[]]*14
    print(an_units)
    fnom = [50]*14
    cfgcount = [1]*14

    cfg = ConfigFrame2(7734, 1000000, 14, station_names, phasor_ids, data_format,
                                          phasor_ids, [0]*14, [0]*14,
                                         channel_names2,
                                         ph_units2,
                                         #[(1, "pow"), (1, "rms"), (1, "peak")], [(0x0000, 0xffff)],
                                         an_units,
                                         dig_units, fnom, cfgcount, 30)

    pmu.set_configuration(cfg)

    pmu.set_header()  # This will load default header message "Hello I'm tinyPMU!"

    pmu.run()  # PMU starts listening for incoming connections

    while True:
        if pmu.clients:  # Check if there is any connected PDCs
            pmu.send_data_file("ieee14_vsc_wtg_out.lst", "ieee14_vsc_wtg_out.dat")

    pmu.join()
