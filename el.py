'''
Keithley I-V Sweep + Spectra 
by Gillian Shen, University  of Washington

Modified by Helen Kuang


Keithley I-V Sweep
Modified by Gillian Shen, May 2022, from 
Demis D. John, October 2014, Univ. of California Santa Barbara
Program to sweep voltage & measure current on Keithley SMU
Based off Steve Nichols' Script from ~2010, Univ. of California Santa Barbara

'''
#IV-Sweep Credits to:
#https://github.com/demisjohn/Keithley-I-V-Sweep

import pyvisa        # PyVISA module, for GPIB comms
import numpy as np  # enable NumPy numerical analysis
import time          # to allow pause between measurements
import os            # Filesystem manipulation - mkdir, paths etc.
import matplotlib.pyplot as plt # for python-style plottting, like 'ax1.plot(x,y)'
from datetime import date

import streamlit as st
st.set_page_config(page_title='EL')

def intro():
    st.title('Keithley I-V Sweep + EL')
    st.subheader('The Ginger Lab, University of Washington')
    st.caption('Gillian Shen')
    
def set_params():
    with st.form("Set params"):
        save_file_input = st.checkbox("Save files", value=True)
        sample_name_input = st.text_input("Sample name", value="QLEDcheng")
        
        col1, col2 = st.columns(2)
        with col1:
            sleep_time_input = st.number_input("Sleep time (s)", value=0.5, format='%f')
        with col2:
            current_compliance_input = st.number_input("Current compliance (A)", value=1.0, format='%f')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            start_input = st.number_input("Starting value of voltage sweep (V)", value=0.0, format='%f')
        with col2:
            stop_input = st.number_input("Ending value of voltage sweep (V)", value=5.0, format='%f')
        with col3:
            numpoints_input = st.number_input("Number of points in sweep", value=21)

        # Every form must have a submit button.
        submitted = st.form_submit_button("Run")
        if submitted:
            body(save_file_input, sample_name_input, sleep_time_input, current_compliance_input,
                start_input, stop_input, numpoints_input)
            if save_file_input:
                st.success('All files were downloaded!')

def body(save_file_input, sample_name_input, sleep_time_input, current_compliance_input, 
         start_input, stop_input, numpoints_input):
    
    #PARAMETERS
    SaveFiles = save_file_input   # Save the plot & data?  Only display if False.
    Sample_Name = sample_name_input        #sample number
    sleep_time = sleep_time_input #seconds
    CurrentCompliance = current_compliance_input    # compliance (max) current (A)
    start = start_input     # starting value of Voltage sweep
    stop = stop_input      # ending value 
    numpoints = numpoints_input  # number of points in sweep

    #--------------------------------------------------------------------------
    
    today = date.today()
    date_string = date.isoformat(today)
#     date_string
    
    rm = pyvisa.ResourceManager()
#     rm.list_resources()

    keithley = rm.open_resource('GPIB0::24::INSTR')
    keithley2 = rm.open_resource('GPIB1::24::INSTR') #photocurrent measure
    
    #--------------------------------------------------------------------------
    
    # Setup electrodes as voltage source
    keithley.write("*RST")
    #print("reset the instrument")
    time.sleep(0.5)    # add second between
    keithley.write(":SOUR:FUNC:MODE VOLT")
    keithley.write(":SENS:CURR:PROT:LEV " + str(CurrentCompliance))
    keithley.write(":SENS:CURR:RANGE:AUTO 1")   # set current reading range to auto (boolean)
    keithley.write(":OUTP ON")                    # Output on    

    #Configuring Keithley 2 for photocurrent measurement. Same as above except without voltage source mode
    keithley2.write("*RST")

    #Measuring photocurrent
    keithley2.write(":SENS:CURR:PROT:LEV " + str(CurrentCompliance))
    keithley2.write(":SENS:CURR:RANGE:AUTO 1")   # set current reading range to auto (boolean)

    keithley2.write(":OUTP ON")                    # Output on

    # Loop to sweep voltage, collect photocurrent
    Voltage=[]
    Current = []
    Photocurrent = []
    voltage_count=0

    for V in np.linspace(start, stop, num=numpoints, endpoint=True):
        #Voltage.append(V)
        print("Voltage set to: "+str(V)+" V")
        keithley.write(":SOUR:VOLT " + str(V))
        time.sleep(sleep_time)    # add second between
        data = keithley.query(":READ?")   #returns string with many values (V, I, ...)
        answer = data.split(',')    # remove delimiters, return values into list elements
        I = eval(answer.pop(1)) * 1e3     # convert to number
        Current.append(I)

        vread = eval(answer.pop(0))
        Voltage.append(vread)
        print("--> Current = " + str(Current[-1]) + ' mA') 

        #Now photocurrent
        data2 = keithley2.query(":READ?")   #returns string with many values (V, I, ...)
        answer2 = data2.split(',')    # remove delimiters, return values into list elements
        PhotocurrentI = eval(answer2.pop(1)) * 1e3     # convert to number
        if V == 0:
            Dark_photocurrent = PhotocurrentI
        Photocurrent.append(PhotocurrentI-Dark_photocurrent)
        print("--> Photocurrent = " + str(Photocurrent[-1]) + ' mA')   # print last read value

        voltage_count+=1
        #end for(V)
    keithley.write(":OUTP OFF")     # turn off
    keithley.write("SYSTEM:KEY 23") # go to local control
    #keithley.close()

    #keithley2.write(":OUTP OFF")     # turn off
    #keithley2.write("SYSTEM:KEY 23") # go to local control
    #keithley2.close()

    
#     #set to current source, voltage meas
#     keithley.write(":SOUR:FUNC:MODE curr")
#     keithley.write(":SOUR:CURR " + str(CurrentCompliance))
#     keithley.write(":SENS:volt:PROT:LEV " + str(max(Voltage))  )
#     keithley.write(":SENS:volt:RANGE:AUTO 1")
    
    
    #--------------------------------------------------------------------------
    
    ###### Plot #####
    
    fig1, ax1 = plt.subplots(nrows=1, ncols=1)         # new figure & axis

    line1 = ax1.plot(Voltage, Current)
    ax1.set_xlabel('Voltage (V)')
    ax1.set_ylabel('Current (mA)')
    ax1.set_title(f'I-V Curve {Sample_Name}')
#     fig1.show()  # draw & show the plot - unfortunately it often opens underneath other windows
    st.pyplot(fig1)

    if SaveFiles:
        plt.savefig(f'IV+Spectra/{date_string}{Sample_Name}IV2.png', bbox_inches='tight')
    
    #--------------------------------------------------------------------------
    
    ###### Plot #####
    
    fig1, ax1 = plt.subplots(nrows=1, ncols=1)         # new figure & axis

    line1 = ax1.plot(Voltage, Photocurrent)
    ax1.set_xlabel('Voltage (V)')
    ax1.set_ylabel('Photocurrent (mA)')
    ax1.set_title(f'Bias vs. Photocurrent Curve {Sample_Name}')
#     fig1.show()
    st.pyplot(fig1)

    if SaveFiles:
        plt.savefig(f'IV+Spectra/{date_string}{Sample_Name}Bias_Photocurrent.png', bbox_inches='tight')
    
    #--------------------------------------------------------------------------
    
    Current=np.asarray(Current).reshape(numpoints,1)
    Voltage=np.asarray(Voltage).reshape(numpoints,1)
    Photocurrent = np.asarray(Photocurrent).reshape(numpoints,1)
    #Photovoltage = np.asarray(Photovoltage).reshape(numpoints,1)
    IV = np.append(Voltage,Current,axis=1)
    IV_photocurrent = np.append(IV,Photocurrent,axis=1)
    #IV_photoIV = np.append(IV_photocurrent,Photovoltage,axis=1)
    
    if SaveFiles:
        np.savetxt(f'IV+Spectra/{date_string}{Sample_Name}_IV+photocurrent.csv', IV_photocurrent, 
                   fmt='%.18e', delimiter='\t', newline='\n', header='Bias(V)\tCurrent(mA)\tPhotocurrent(mA)')
        
#     IV_photocurrent
    
        
if __name__ == '__main__':
    intro()
    set_params()
    