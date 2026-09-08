##################################################################################################################################################################################
#This script is only for single channel measurments, completely dependent on the file format and the Siglent SDS1104X-E being used as the scope
#
#
#
#
#
#
#
#
# < -> little endian byte order
# 8s -> 8-byte character array/string
# I -> 4-byte unsigned int
# 32s -> 32-byte character
# d -> 8-byte double
# Q -> 8-byte unsigned int
#
#SPLG 0005 example
#first sector 16781312
#second sector 16783872
#third sector 16786432
#fourth sector 16788992
#last sector 16791552
#
#
###################################################################################################################################################################################
import csv
import struct
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pyvisa
import csv

Scope_IP_Address = "100.64.11.133"
NTP_Server_IP_Address = "100.64.8.3"

input_filename = "splg0005.slg"
output_filename = "SS1 Capture Test.csv"
plot_name = output_filename.removesuffix('.csv')


input_path = r"C:\Users\KDick\Desktop\NTP_SCOPE\Captured_Slgs\\" + input_filename
output_path = r"C:\Users\KDick\Desktop\NTP_SCOPE\CSVs\\" + output_filename

#example for inbound event (T0 at IDF and T1 CWP event ringing)






def connection_to_scope():
    rm = pyvisa.ResourceManager()
    print(rm.list_resources())
    scope = rm.open_resource(f'TCPIP0::{Scope_IP_Address}::INSTR')
    print(scope.query('*IDN?'))

    scope.write('STOP')


    print(scope.query('MMEMory:CATalog?'))



    

    scope.close()
    rm.close()


def reading_slg_file(file_path):
    global zero_adc_code, value_per_adc_code, vpos_val, sector_number_per_channel, sample_rate, NTP_time
    FORMAT_STRING = '<8s I 32s 32s 32s 20s I I d d d Q Q Q Q Q I I I I I I I I 152s 256s I I d d d d I I 8s 200s I I d d d d I I 8s 200s'
    with open(file_path, 'rb') as f:
        data = f.read(struct.calcsize(FORMAT_STRING))
    unpacked = struct.unpack(FORMAT_STRING, data)

    sector_number_per_channel = unpacked[7]
    sample_rate = unpacked[9]
    NTP_time = datetime(unpacked[17], unpacked[18], unpacked[19], unpacked[20], unpacked[21], unpacked[22], unpacked[23] * 1000)
    vpos_val = unpacked[30]
    value_per_adc_code = unpacked[31]
    zero_adc_code = unpacked[32]

        
    parsed_data = {
        #first section (product info)
        "file_type": unpacked[0].decode('ascii').rstrip('\x00'),
        "file_version": unpacked[1],
        "model_number": unpacked[2].decode('ascii').rstrip('\x00'),
        "serial_number": unpacked[3].decode('ascii').rstrip('\x00'),
        "software_version": unpacked[4].decode('ascii').rstrip('\x00'),
        "reserved_after_product_info": unpacked[5],
        #second section (record info)
        "channels_enabled": unpacked[6],
        "sector_number_per_channel": unpacked[7],
        "tdiv_value": unpacked[8],
        "sample_rate (Sa/s)": unpacked[9],
        "total_recorded_length (s)": unpacked[10],
        "number_of_data_points_per_channel": unpacked[11],
        "start_sector_offset": unpacked[12],
        "end_sector_offset": unpacked[13],
        "file_offset_of_first_data_point": unpacked[14],
        "file_offset_of_last_data_point": unpacked[15],
        "bits_number_of_data": unpacked[16],
        "Year": unpacked [17],
        "Month": unpacked [18],
        "Day": unpacked [19],
        "Hour": unpacked [20],
        "Minute": unpacked [21],
        "Second": unpacked [22],
        "Millisecond": unpacked [23],
        "reserved_after_record_info": unpacked [24],
        #third section (channel info)
        "large_reserved_block": unpacked [25],
        "channel1_on_off_status": unpacked[26],
        "probe_index": unpacked[27],
        "custom_probe": unpacked[28],
        "V/div": unpacked[29],
        "vpos_val offset": unpacked[30],
        "value_per_adc_code": unpacked[31],
        "zero_adc_code": unpacked[32],
        "type_of_unit": unpacked[33],
        "unit_of_channel": unpacked[34].decode('ascii').rstrip('\x00'),
        "reserved_after_channel1_info": unpacked[35],
    }

    print(parsed_data)



def parse_data(file_path, sector_number_per_channel):
    global byte_buffer
    initial_data_sector_address = 16781312
    initial_data_address = 16781372

    byte_buffer = bytearray()
    with open(file_path, "rb") as f:
        for i in range(sector_number_per_channel):
            f.seek(initial_data_address + (i * 2560))
            chunk = f.read(2500)
            byte_buffer.extend(chunk)
        
    try:
        null_index = byte_buffer.index(0x00)
        del byte_buffer[null_index:]
    except ValueError:
        pass
    #print(byte_buffer)




def convert_data_to_voltage(byte_buffer, zero_adc_code, value_per_adc_code, vpos_val):
    #reference: voltage = (data − zero_adc_code) ∙ value_per_adc_code − vpos_val
    global voltage_sample_buffer
    voltage_sample_buffer = []
    for i in range(len(byte_buffer)):
        voltage = (byte_buffer[i] - zero_adc_code) * value_per_adc_code - vpos_val
        voltage_sample_buffer.append(voltage)
    print("poo")
    #print(voltage_sample_buffer)


def calculate_time_data(voltage_sample_buffer, sample_rate, NTP_time):
    global formatted_time_buffer, NTP_time_buffer
    #reference: time_value = data_index/sample_rate
    #reference: where -> data_index = sector_index ∙ 2500 + data_index_in_sector
    time_sample_buffer = []
    NTP_time_buffer = []
    
    for i in range(len(voltage_sample_buffer)):
        time = (i / sample_rate)
        time_sample_buffer.append(time)
        NTP_time_buffer.append(NTP_time + timedelta(seconds=time))
    print("poo")
    formatted_time_buffer = [dt.strftime("%Y-%m-%d %H:%M:%S.%f") for dt in NTP_time_buffer]
    #print(formatted_time_buffer)






def plot_waveform(voltage_buffer, NTP_buffer, plot_name):
    
    fig, ax = plt.subplots()
    ax.plot(NTP_buffer, voltage_buffer, label="Waveform")
    ax.set_xlabel('Time')
    ax.set_ylabel('Voltage (v)')
    ax.set_title(plot_name)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S.%f'))
    annot = ax.annotate("", xy=(0,0), xytext=(10, 10), textcoords="offset points", bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.9))
    annot.set_visible(False)

    num_dates = mdates.date2num(NTP_buffer)

    def hover(event):
        if event.inaxes == ax:
            idx = (np.abs(num_dates - event.xdata)).argmin()

            exact_time = NTP_buffer[idx]
            y_val = voltage_buffer[idx]

            time_str = exact_time.strftime('%Y-%m-%d %H:%M:%S.%f')

            annot.xy = (event.xdata, event.ydata)
            annot.set_text(f"Time: {time_str}\nVolt: {y_val:.4f}V")
            annot.set_visible(True)
            fig.canvas.draw_idle()
        else:
            if annot.get_visible():
                annot.set_visible(False)
                fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", hover)
    plt.show()


def create_csv_file(voltage_sample_buffer, NTP_time_buffer, output_filename):
    with open(output_filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Time", "Voltage"])
        for time, voltage in zip(NTP_time_buffer, voltage_sample_buffer):
            writer.writerow([time, voltage])







###############################################################


#connection_to_scope()


reading_slg_file(input_path)
parse_data(input_path, sector_number_per_channel)
convert_data_to_voltage(byte_buffer, zero_adc_code, value_per_adc_code, vpos_val)
calculate_time_data(voltage_sample_buffer, sample_rate, NTP_time)
create_csv_file(voltage_sample_buffer, NTP_time_buffer, output_path)
plot_waveform(voltage_sample_buffer, NTP_time_buffer, plot_name)
