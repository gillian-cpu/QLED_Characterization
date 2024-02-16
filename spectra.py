"""
Keithley I-V Sweep + Spectra 
by Gillian Shen, University of Washington

Modified by Helen Kuang


Keithley I-V Sweep
Modified by Gillian Shen, May 2022, from 
Demis D. John, October 2014, Univ. of California Santa Barbara
Program to sweep voltage & measure current on Keithley SMU
Based off Steve Nichols' Script from ~2010, Univ. of California Santa Barbara

"""
#IV-Sweep Credits to:
#https://github.com/demisjohn/Keithley-I-V-Sweep


import pyvisa        # PyVISA module, for GPIB comms
import numpy as np  # enable NumPy numerical analysis
import time          # to allow pause between measurements
import os            # Filesystem manipulation - mkdir, paths etc.
import matplotlib.pyplot as plt # for python-style plottting, like 'ax1.plot(x,y)'
import seabreeze
seabreeze.use('pyseabreeze')
from seabreeze.spectrometers import list_devices, Spectrometer
from datetime import date

import pandas as pd
import math
import matplotlib.cm as cm
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from IPython.display import Image
import matplotlib as mpl
from pylab import cm
mpl.rcParams.update(mpl.rcParamsDefault)

import streamlit as st
st.set_page_config(page_title='Spectra')


def intro():
    st.title('Keithley I-V Sweep + Spectra')
    st.subheader('The Ginger Lab, University of Washington')
    st.caption('Gillian Shen')

def set_params():
    with st.form("Set params"):
        save_file_input = st.checkbox("Save files", value=True)
        sample_name_input = st.text_input("Sample name", value="Commercial_White1")
        
        col1, col2 = st.columns(2)
        with col1:
            sleep_time_input = st.number_input("Sleep time (s)", value=0.05, format='%f')
        with col2:
            current_compliance_input = st.number_input("Current compliance (A)", value=1.0, format='%f')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            start_input = st.number_input("Starting value of voltage sweep (V)", value=0.0, format='%f')
        with col2:
            stop_input = st.number_input("Ending value of voltage sweep (V)", value=10.0, format='%f')
        with col3:
            numpoints_input = st.number_input("Number of points in sweep", value=21)
        spec_int_time_input = st.number_input("Spectrometer integration time (microseconds)", value=1000000.0, format='%f')

        # Every form must have a submit button.
        submitted = st.form_submit_button("Run")
        if submitted:
            body(save_file_input, sample_name_input, sleep_time_input, current_compliance_input, 
                 start_input, stop_input, numpoints_input, spec_int_time_input)
            if save_file_input:
                st.success('All files were downloaded!')

def body(save_file_input, sample_name_input, sleep_time_input, current_compliance_input, 
         start_input, stop_input, numpoints_input, spec_int_time_input):
    #PARAMETERS
    SaveFiles = save_file_input   # Save the plot & data?  Only display if False.
    Sample_Name = sample_name_input        #sample number
    sleep_time = sleep_time_input #seconds
    CurrentCompliance = current_compliance_input    # compliance (max) current (A)
    start = start_input     # starting value of Voltage sweep
    stop = stop_input      # ending value 
    numpoints = numpoints_input  # number of points in sweep

    Spectrometer_integration_time = spec_int_time_input #microseconds

    #--------------------------------------------------------------------------

    today = date.today()
    date_string = date.isoformat(today)
#     date_string

    devices = list_devices()
#     devices
    
    spec = Spectrometer(devices[0])
#     spec
    
    # set integration time
    spec.integration_time_micros(Spectrometer_integration_time)
    
    rm = pyvisa.ResourceManager()
    rm.list_resources()
    
    keithley = rm.open_resource('GPIB0::24::INSTR')
    
    #--------------------------------------------------------------------------
    
    # Setup electrodes as voltage source
    keithley.write("*RST")
    #print("reset the instrument")
    time.sleep(0.5)    # add second between
    keithley.write(":SOUR:FUNC:MODE VOLT")
    keithley.write(":SENS:CURR:PROT:LEV " + str(CurrentCompliance))
    keithley.write(":SENS:CURR:RANGE:AUTO 1")   # set current reading range to auto (boolean)
    keithley.write(":OUTP ON")                    # Output on    

    # Loop to sweep voltage, collect spectra
    Voltage=[]
    Current = []
    header_string = 'Wavelengths(nm)'
    Spectra_array = np.zeros((2048,numpoints+1))
    voltage_count=0
    for V in np.linspace(start, stop, num=numpoints, endpoint=True):
        #Voltage.append(V)
        print("Voltage set to: "+str(V)+" V")
        header_string += '\t'+str(V)+"V"

        keithley.write(":SOUR:VOLT " + str(V))
        time.sleep(sleep_time)    # add second between
        data = keithley.query(":READ?")   #returns string with many values (V, I, ...)
        answer = data.split(',')    # remove delimiters, return values into list elements
        I = eval(answer.pop(1)) * 1e3     # convert to number
        Current.append(I)

        vread = eval(answer.pop(0))
        Voltage.append(vread)

        print("--> Current = " + str(Current[-1]) + ' mA')   # print last read value

        #SPECTROMETER
        # get wavelengths
        wavelengths = spec.wavelengths()
        # get intensities
        intensities = spec.intensities()

        if V==0:
            dark_intensities = intensities

        Spectra_array[:,0] = wavelengths
        Spectra_array[:,voltage_count+1] = intensities #-dark_intensities

        voltage_count+=1
        #end for(V)
    keithley.write(":OUTP OFF")     # turn off

    #set to current source, voltage meas
    keithley.write(":SOUR:FUNC:MODE curr")
    keithley.write(":SOUR:CURR " + str(CurrentCompliance))
    keithley.write(":SENS:volt:PROT:LEV " + str(max(Voltage))  )
    keithley.write(":SENS:volt:RANGE:AUTO 1")

    keithley.write("SYSTEM:KEY 23") # go to local control
    #keithley.close()
    
    #--------------------------------------------------------------------------
    
    ###### Plot #####
    
    fig1, ax1 = plt.subplots(figsize=(3, 3), nrows=1, ncols=1)         # new figure & axis

    line1 = ax1.plot(Voltage, Current)
    ax1.set_xlabel('Voltage (V)')
    ax1.set_ylabel('Current (mA)')
    ax1.set_title(f'I-V Curve {Sample_Name}')
#     fig1.show()  # draw & show the plot - unfortunately it often opens underneath other windows

    buf, mid, buf = st.columns([1,3,1])
    with mid:
        st.pyplot(fig1)

    if SaveFiles:
        plt.savefig(f'IV+Spectra/{date_string}{Sample_Name}IV1.png', bbox_inches='tight')
    
    #--------------------------------------------------------------------------
    
    Current=np.asarray(Current).reshape(numpoints,1)
    Voltage=np.asarray(Voltage).reshape(numpoints,1)
    IV = np.append(Voltage,Current,axis=1)
    
#     Spectra_array
    int_time_s = Spectrometer_integration_time/1000000
    if SaveFiles==True:
        np.savetxt(f'IV+Spectra/{date_string}{Sample_Name}_{start}V-{stop}V_{int_time_s}s_spectra.csv', Spectra_array, 
                   fmt='%.18e', delimiter='\t', newline='\n', header=header_string, 
                   footer=f'Integration Time (ms) = {Spectrometer_integration_time}')
        np.savetxt(f'IV+Spectra/{date_string}{Sample_Name}_{start}V-{stop}V_{int_time_s}s_IV.csv', IV, fmt='%.18e', 
                   delimiter='\t', newline='\n', header='Bias Voltage(V)\tCurrent(mA)')
    
    #--------------------------------------------------------------------------
    
    colors = cm.get_cmap('PuBu', 8)
    print(colors(0.56))
    
    #If taking subset of spectra:
    #selected_spectra = np.arange(20,46,5)
    #for k in selected_spectra:
    
#     np.arange(0,numpoints, 5)
    
    #--------------------------------------------------------------------------
    
    plt.rc('font', family='Arial')
    plt.rcParams['axes.linewidth'] = 2
    plt.rc('xtick', labelsize='small')
    plt.rc('ytick', labelsize='small')
    plt.rcParams['font.size'] = 12

    fig = plt.figure(figsize=(5, 3))
    ax = fig.add_axes([0, 0, 1, 1])

    #for k in np.arange(0,numpoints, 5):
    for k in range(numpoints):
        ax.plot(Spectra_array[:,0],Spectra_array[:,k+1],color = colors((k+3)/(numpoints+3)), 
                 label=f'{IV[k,0]}V', linewidth = 1)

    ax.set_xlabel('Wavelength(nm)')
    ax.set_ylabel('Counts')
    ax.set_title(f'Electroluminescence Spectra at Each\n Bias Voltage of {Sample_Name}')
    ax.set_xlim(350,850)
    ax.legend(bbox_to_anchor=(1.4, 1), loc=1, frameon=False, fontsize=10, ncol=2)
#     plt.show()
    st.pyplot(fig)

    
    if SaveFiles==True:
        plt.savefig(f'IV+Spectra/{date_string}{Sample_Name}_{start}V-{stop}V_{int_time_s}sIntegrationTime_Spectra.png', bbox_inches='tight')
    
    
if __name__ == '__main__':
    intro()
    set_params()
    