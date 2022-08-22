"""
Created on Mon Aug 1, 2022

@author: Helen Kuang

Base code by Gillian Shen
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math
import matplotlib.cm as cm
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from IPython.display import Image
import matplotlib as mpl
from pylab import cm
import time 
from datetime import date

import matplotlib as mpl
mpl.rcParams.update(mpl.rcParamsDefault)

import streamlit as st


# When dev_mode is True, the app will be written with development comments.
# Keep this variable False when app is rebooted for public use.
dev_mode = False

st.set_page_config(page_title='QLED')

def intro():
    st.title('QLED Testing Postprocessing')
    st.subheader('The Ginger Lab, University of Washington')
    st.caption('Gillian Shen, Helen Kuang')
                

def pre(spectra_input, IV_photo_input):
    global date_string
    today = date.today()
    date_string = date.isoformat(today)
    
#     st.write(date_string)
    global Spectra
    global IV_EL
    global phototopic
    global numpoints
#     global Sample_Name
        
    Spectra = pd.read_csv(spectra_input, sep='\t',skipfooter=1)
    Spectra = Spectra.to_numpy()

    IV_EL = pd.read_csv(IV_photo_input, sep='\t')
    IV_EL = IV_EL.to_numpy()
    
    #Phototopic curve
    phototopic = pd.read_csv(f'StranksPhototopicLuminosityFunction.csv',header=None).to_numpy()
        
    numpoints = len(IV_EL)
#     Sample_Name = 'CommercialWhite1'
    
    plt.rc('font', family='Arial')
    plt.rcParams['axes.linewidth'] = 2
    plt.rc('xtick', labelsize='small')
    plt.rc('ytick', labelsize='small')
    plt.rcParams['font.size'] = 12
    
    
    #https://matplotlib.org/3.5.0/tutorials/colors/colormaps.html
    #https://matplotlib.org/3.5.0/tutorials/colors/colormap-manipulation.html

    global colors
    colors = cm.get_cmap('PuBu', 8)
#     st.write(colors(0.56))
    
    global D_input, A_LED_input, A_phd_input
    
    st.sidebar.header("Adjust Settings")

    D_input = st.sidebar.number_input("Distance between photodetector and LED (mm)", value=20.0, format='%f')
    A_LED_input = st.sidebar.number_input("Active area of LED (mm^2)", value=15.0, format='%f')
    A_phd_input = st.sidebar.number_input("Active area of photodetector (mm^2)", value=100.0, format='%f')
    
    ######################################################

#Infer QE of photodiode at a specific wavelength using interpolation
#X~wavelength, Y~Photodiode QE
def interpolate(Xmin,Xmax,Y1,Y2,currentXval):
    frac = (currentXval-Xmin)/(Xmax-Xmin)
    y = frac*(Y2-Y1)+Y1
    return y
    
#Finding lower and upper bounds for interpolation from photodiode array data. 
#Upper bound index will really just turn out to be lower bound +1
def upper_lower(wavelength,array):
    min_index=0
    for i in range(len(array)):
        if array[i,0]<wavelength:
            min_index+=1
            #max_index+=1
    result = min_index-1
    return result
    
# Computes for Cs
@st.cache
def slow_computation(Cs):
    for a in range(numpoints):
        C_numerator = 0
        C_denominator = 0
        for b in range(2047): 
            Xcurrent = normalized_EL_Spectra[b,0]
            Xmin_index = upper_lower(Xcurrent,photodiode_data)
            Xmin = photodiode_data[Xmin_index,0]
            Xmax = photodiode_data[Xmin_index+1,0]
            Ymin = photodiode_data[Xmin_index,2]/100
            Ymax = photodiode_data[Xmin_index+1,2]/100
            QE = interpolate(Xmin,Xmax,Ymin,Ymax,Xcurrent)
            dlambda = normalized_EL_Spectra[b+1,0]-normalized_EL_Spectra[b,0]*1e-9
            C_numerator+=normalized_EL_Spectra[b,a+1]*QE*dlambda
            C_denominator+=normalized_EL_Spectra[b,a+1]*dlambda
        C=C_numerator/C_denominator
        Cs[a]=C

    return Cs
    
# Computes for Ks
@st.cache
def slow_computation2(Ks, phototopic_scaling):
    for a in range(numpoints):
        K_numerator = 0
        K_denominator = 0
        for b in range(2047): 
            if normalized_EL_Spectra[b,0]>np.amin(phototopic[:,0]) and normalized_EL_Spectra[b,0]<np.amax(phototopic[:,0]):
                Xcurrent = normalized_EL_Spectra[b,0]
                Xmin_index = upper_lower(Xcurrent,phototopic)
                Xmin = phototopic[Xmin_index,0]
                Xmax = phototopic[Xmin_index+1,0]
                Ymin = phototopic[Xmin_index,1]
                Ymax = phototopic[Xmin_index+1,1]
                response = interpolate(Xmin,Xmax,Ymin,Ymax,Xcurrent)
                dlambda = normalized_EL_Spectra[b+1,0]-normalized_EL_Spectra[b,0]*1e-9
                K_numerator+=response*phototopic_scaling*normalized_EL_Spectra[b,a+1]*h*c*dlambda/(Xcurrent*1e-9)
                K_denominator+=normalized_EL_Spectra[b,a+1]*dlambda
        K=K_numerator/K_denominator
        Ks[a]=K
    return Ks

def preprocess_data():
    global photodiode_data

    photodiode_file = "PhotodiodeE_000"
    f = open(photodiode_file+'.qsdat', "r")
    
#     st.write(f.read())

    #Converting Data portion of .qsdat file to txt form for pandas
    stringA = "Wavelength("
    stringB = 'END DATA'
    file0 = open(photodiode_file+".qsdat", "r")
    file1 = open(photodiode_file+".txt", "w")
    i=0
    j=0
    k=0
    for line in file0:  
        i+=1
        if stringA in line:
#             print("Data starts line", i)
#             st.write("Data starts line", i)
            j+=1
        if stringB in line:
#             print("Data ends line", i)
#             st.write("Data ends line", i)
            k+=1   
        if j==1 and k==0:
            file1 = open(photodiode_file+".txt", "a")
            file1.write(line)
            file1.close()
    
    photodiode_data = pd.read_csv(photodiode_file+".txt", delimiter='\t')
#     st.write(photodiode_data)

    photodiode_data=photodiode_data.to_numpy()
    
    
    ##########################################################
    # before 6
    
    global D, A_LED, A_phd, Omega_phd, Selected_EL_Spectrum, normalized_EL_Spectrum, normalized_EL_Spectra
    
#     D = 10 #mm distance between sample and photodetector
#     #A_LED = 4.5 #mm^2
#     A_LED = math.pi*4**2 #mm^2
#     A_phd = 100 #mm^2
#     #treating the LED as a point source as it is much smaller than the photodetector active area
    D = D_input
    A_LED = A_LED_input
    A_phd = A_phd_input
    
    
    #angle subtended by the photodetector
    Omega_phd = 2*math.pi*(1-math.cos(math.sqrt(A_phd/math.pi)/D))
#     Omega_phd #units sr (The steradian or square radian is the SI unit of solid angle)
#     st.write(Omega_phd)
    
    #Selecting max EL spectrum to normalize and continue with calculation
    Selected_EL_Spectrum = numpoints-1
    normalized_EL_Spectrum = Spectra[:,Selected_EL_Spectrum+1]/np.amax(Spectra[:,Selected_EL_Spectrum+1])
    normalized_EL_Spectra=Spectra.copy()
    for i in range(numpoints-1): #This is because the 0V column is entirely zeros
        normalized_EL_Spectra[:,i+2] = Spectra[:,i+2]/np.amax(Spectra[:,i+2])
        
        
    ##########################################################
    # before 8
    
    global e, h, c, calculated_QEs
    
    e=1.602176634e-19 #[C]
    h=6.62607015e-34 #[J.s]
    c=299792458 #[m.s-1]
    
    #Now attempting to convert from responsivity to quantum efficiency of the photodetector:
    calculated_QEs = photodiode_data[:,3]*h*c/(e*photodiode_data[:,0]*1e-9)
    
    
    ##########################################################
    # before 9
    
    global Cs, IV_EL, Phi_phd_array
    
    #Doing out the integrals in to calculate C
    Cs = np.zeros((numpoints,))
    
    Cs = slow_computation(Cs)
    
    #Note there are some negative C values and this is most likely due to negative spectrum 
    #readings from dark-subtracted spectra?
    
    Phi_phd_array = np.zeros((numpoints,))
    for a in range(numpoints):
        Phi_phd = IV_EL[a,2]/(1000*(Omega_phd*Cs[a])*e)
        Phi_phd_array[a,]=Phi_phd #[photons.s-1.sr-1]
        
    #Adding a column to IV_EL for photon flux:
    IV_EL = np.append(IV_EL, np.zeros((numpoints,1)), axis=1)
    IV_EL[:,3]=Phi_phd_array #[photons.s-1.sr-1]
    
    ##########################################################
    # before 10
        
    #Average energy per photon
    E_photon_array = np.zeros((numpoints,))
    for a in range(numpoints):
        E_numerator = 0
        E_denominator = 0
        for b in range(2047):
            dlambda = normalized_EL_Spectra[b+1,0]-normalized_EL_Spectra[b,0]*1e-9
            wavelength = normalized_EL_Spectra[b,0]*1e-9
            E_numerator+=normalized_EL_Spectra[b,a+1]*h*c*dlambda/wavelength
            E_denominator+=normalized_EL_Spectra[b,a+1]*dlambda
        E_photon=E_numerator/E_denominator   #[J/photon]
        E_photon_array[a]=E_photon
    
#     st.write(E_photon_array)

    R_prime = IV_EL[:,3]*E_photon_array  #Radiant Intensity [W.sr-1]
#     st.write(R_prime)

    R = R_prime/(A_LED*1e-6)
#     st.write(R) #Radiance [W.sr-1.m-2]

    
    #Adding a column to IV_EL for radiance:
    IV_EL = np.append(IV_EL, np.zeros((numpoints,1)), axis=1)
    IV_EL[:,4]=R #columns: V, I, Iphd, Photon Flux, Radiance
    
    ##########################################################
    # before 11
        
    #Lambertian distribution leads to photon flux
    phi = math.pi*Phi_phd_array  #[photons.s-1]
    
    EQE_array = np.zeros((numpoints,))
    for a in range(numpoints):
        EQE = phi[a]/(IV_EL[a,1]/(1000*e))
        EQE_array[a] = EQE*100 #%
#     st.write(EQE_array)
    
    IV_EL = np.append(IV_EL, np.zeros((numpoints,1)), axis=1)
    IV_EL[:,5]=EQE_array #columns: V, I, Iphd, Photon Flux, Radiance, EQE
    
    #Adding a column for J [mA.cm-2]
    IV_EL = np.append(IV_EL, np.zeros((numpoints,1)), axis=1)
    IV_EL[:,6]=IV_EL[:,1]/(A_LED*1e-2) #columns: V, I, Iphd, Photon Flux, Radiance, EQE, J
    
    
    ##########################################################
    # before 16
    
    global Ks, L_prime
    
    #The above is normalized - it needs to be scaled by ~683.002 lm·W-1 before being used in further calcs 
    phototopic_scaling = 683.002 #lm·W-1
    
    #In order to take into account the perception of light by the human eye we weight the S(𝜆) by the
    #photopic function 𝑃(𝜆).
    Ks = np.zeros((numpoints,))
    Ks = slow_computation2(Ks, phototopic_scaling)
    
    
#     st.write(Ks) #lm.s.photon^-1
    
    #Luminous intensity 
    L_prime = np.zeros((numpoints,))
    for a in range(numpoints):
        L_prime[a] = Phi_phd_array[a]*Ks[a]
#     st.write(L_prime)

    ##Cross checking using second method of calculation
#     L_prime2 = np.zeros((numpoints,))
#     for a in range(numpoints):
#         L_prime2[a] = Ks[a]*IV_EL[a,2]*1e-3/(e*Cs[a]*Omega_phd)
    
    IV_EL = np.append(IV_EL, np.zeros((numpoints,1)), axis=1)
    IV_EL[:,7]=L_prime #columns: V, I, Iphd, Photon Flux, Radiance, EQE, J, Luminous intensity (cd)
    
    
    ##########################################################
    # before 17
    
    L= L_prime/(A_LED*1e-6) #[cd.m-2]
    
    IV_EL = np.append(IV_EL, np.zeros((numpoints,1)), axis=1)
    IV_EL[:,8]=L #columns: V, I, Iphd, Photon Flux, Radiance, EQE, J, Luminous intensity (cd), Luminance (cd/m^2),
    
    
    ##########################################################
    # before 19
        
    #columns: V, I, Iphd, Photon Flux, Radiance, EQE, J, Luminous intensity (cd), Luminance (cd/m^2),
    #luminous efficacy 
    eta_current = np.zeros((numpoints,))
    eta_lum = np.zeros((numpoints,))
    for a in range(numpoints):
        eta_c= Ks[a]*IV_EL[a,2]/(e*IV_EL[a,1]*Cs[a]*Omega_phd)
        eta_current[a]=eta_c
        eta_l= math.pi*Ks[a]*IV_EL[a,2]*1e-3/(e*Cs[a]*Omega_phd*IV_EL[a,0]*IV_EL[a,1]*1e-3)
        eta_lum[a]=eta_l
    
#     #Cross checking using second calculation method
#     eta_current2=L_prime/(IV_EL[:,1]*1e-3)
    
#     #Cross checking using second method
#     eta_lum2 = L_prime*math.pi/(IV_EL[:,0]*IV_EL[:,1]*1e-3)
    
    IV_EL = np.append(IV_EL, np.zeros((numpoints,1)), axis=1)
    IV_EL[:,9]=eta_current 
    #columns: V, I, Iphd, Photon Flux, Radiance, EQE, J, Luminous intensity (cd), Luminance (cd/m^2), 
    #eta_current (cd/A), eta_lum (lm/electricalW)
    
    IV_EL = np.append(IV_EL, np.zeros((numpoints,1)), axis=1)
    IV_EL[:,10]=eta_lum #columns: V, I, Iphd, Photon Flux, Radiance, EQE, J, Luminous intensity (cd), Luminance (cd/m^2),
    
    
    ##########################################################

def graph2():
    if dev_mode:
        st.write("graph2")
    fig = plt.figure(figsize=(3, 3))
    ax = fig.add_axes([0, 0, 1, 1])

    ax.plot(IV_EL[:,0],IV_EL[:,2],linewidth=2)

    ax.set_xlabel('Bias Voltage(V)')
    ax.set_ylabel('Photocurrent(mA)')
    ax.set_title(f'EL Characteristics of\n {Sample_Name}')
    st.pyplot(fig)
    
    if save_figs:
        plt.savefig(f'{date_string}{Sample_Name}_Voltage_v_Photocurrent.png', bbox_inches='tight')
    
    
def graph3():
    if dev_mode:
        st.write("graph3")
    fig = plt.figure(figsize=(3, 3))
    ax = fig.add_axes([0, 0, 1, 1])

    for k in range(numpoints):
        ax.plot(Spectra[:,0],Spectra[:,k+1],color = colors(k/numpoints), 
                 label=f'{"{:.1f}".format(IV_EL[k,0])}V', linewidth = 0.5)
    
    ax.set_xlabel('Wavelength(nm)')
    ax.set_ylabel('Counts')
    ax.set_title(f'Electroluminescence Spectra at Each\n Bias Voltage of {Sample_Name}')
    
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0, frameon=False, fontsize=10, ncol=3)

    st.pyplot(fig)

    if save_figs:
        plt.savefig(f'{date_string}{Sample_Name}_EL_Spectra_per_Voltage.png', bbox_inches='tight')
    
    ####################################################
    
    
def graph4():
    if dev_mode:
        st.write("graph4")
    fig = plt.figure(figsize=(3, 3))
    ax = fig.add_axes([0, 0, 1, 1])

    ax.plot(photodiode_data[:,0],photodiode_data[:,3],linewidth=2)

    ax.set_xlabel('Wavelength(nm)')
    ax.set_ylabel('Responsivity (A/W)')
    ax.set_title('Responsivity Function of Photodiode E')
    st.pyplot(fig)
    
    if save_figs:
        plt.savefig(f'{date_string}{Sample_Name}_Wavelength_v_Responsivity.png', bbox_inches='tight')
    
    
    ##########################################################

def graph5():
    if dev_mode:
        st.write("graph5")
    fig = plt.figure(figsize=(3, 3))
    ax = fig.add_axes([0, 0, 1, 1])

    ax.plot(photodiode_data[:,0],photodiode_data[:,2],linewidth=2)

    ax.set_xlabel('Wavelength($\lambda$)')
    ax.set_ylabel('EQE(%)')
    ax.set_title('Wavelength dependent EQE of device\n measured by Photodiode E?')
    st.pyplot(fig)
    
    if save_figs:
        plt.savefig(f'{date_string}{Sample_Name}_Wavelength_v_EQE.png', bbox_inches='tight')
    
#     ##########################################################

def graph7():
    if dev_mode:
        st.write("graph7")
    fig = plt.figure(figsize=(3, 3))
    ax = fig.add_axes([0, 0, 1, 1])

    for k in range(numpoints):
        ax.plot(normalized_EL_Spectra[:,0],normalized_EL_Spectra[:,k+1],color = colors(k/numpoints), 
                 label=f'{IV_EL[k,0]}V', linewidth = 1)

    ax.set_xlabel('Wavelength(nm)')
    ax.set_ylabel('Counts')
    ax.set_title(f'Normalized Electroluminescence Spectra at Each\n Bias Voltage of {Sample_Name}')
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0, frameon=False, fontsize=10, ncol=3)
    st.pyplot(fig)
    
    if save_figs:
        plt.savefig(f'{date_string}{Sample_Name}_Norm_EL_Spectra_per_Voltage.png', bbox_inches='tight')
    
    
    ##########################################################
    

def graph9():
    if dev_mode:
        st.write("graph9")
    fig = plt.figure(figsize=(3, 3))
    ax = fig.add_axes([0, 0, 1, 1])

    ax.plot(IV_EL[:,0],IV_EL[:,3],linewidth=2)

    ax.set_xlabel('Bias Voltage(V)')
    ax.set_ylabel('Photon flux ($photon.s^{-1}.sr^{-1}$)')
    ax.set_title(f'Incident Photon Flux on Photodiode\nfrom {Sample_Name}')
    st.pyplot(fig)
    
    if save_figs:
        plt.savefig(f'{date_string}{Sample_Name}_Voltage_v_Photon_Flux.png', bbox_inches='tight')
    
    
    ##########################################################    
    
def graph10():
    if dev_mode:
        st.write("graph10")
    fig = plt.figure(figsize=(3, 3))
    ax = fig.add_axes([0, 0, 1, 1])

    ax.plot(IV_EL[:,0],IV_EL[:,4],linewidth=2)

    ax.set_xlabel('Bias Voltage(V)')
    ax.set_ylabel('Radiance ($W.sr^{-1}.m^{-2}$)')
    ax.set_title(f'LED Radiance vs. Voltage \nfor {Sample_Name}')
    st.pyplot(fig)
    
    if save_figs:
        plt.savefig(f'{date_string}{Sample_Name}_Voltage_v_Radiance.png', bbox_inches='tight')
    
    
    ##########################################################
    
    
def graph12(EQE, x_lo, x_hi, y_lo, y_hi):
    if dev_mode:
        st.write("graph12")
    fig = plt.figure(figsize=(3, 3))
    ax = fig.add_axes([0, 0, 1, 1])

    ax.plot(IV_EL[:,6]/1000,IV_EL[:,5],linewidth=2)

    ax.set_xlabel('Current Density (A/$cm^{-2}$)')
    ax.set_ylabel('EQE(%)')
    ax.set_title(f'LED EQE vs. Current Density \nfor {Sample_Name}')
    
    
    if x_lo < 0.0 or x_hi > 0.0:
        ax.set_xlim(x_lo,x_hi)
    
    if y_lo < 0.0 or y_hi > 0.0:
        ax.set_ylim(y_lo,y_hi)
        
#     ax.set_xlim(x_lo,x_hi)
#     ax.set_ylim(y_lo,y_hi)
 
    ax.set_yscale(EQE)
    ax.set_xscale('log') #as opposed to 'linear'
    st.pyplot(fig)
    
    if save_figs:
        plt.savefig(f'{date_string}{Sample_Name}_Current_v_EQE.png', bbox_inches='tight')
    
    ##########################################################
    

def graph15():
    if dev_mode:
        st.write("graph15")
    fig = plt.figure(figsize=(3, 3))
    ax = fig.add_axes([0, 0, 1, 1])

    ax.plot(phototopic[:,0],phototopic[:,1],linewidth=2)

    ax.set_xlabel('Wavelength(nm)')
    ax.set_ylabel('Phototopic factor')
    ax.set_title('Phototopic response of the human eye to light')
    st.pyplot(fig)
    
    if save_figs:
        plt.savefig(f'{date_string}{Sample_Name}_Wavelength_v_Phototopic_factor.png', bbox_inches='tight')
    
    ##########################################################

    
def graph17():
    if dev_mode:
        st.write("graph17")
    fig = plt.figure(figsize=(3, 3))
    ax = fig.add_axes([0, 0, 1, 1])

    ax.plot(IV_EL[:,6]/1000,IV_EL[:,8],linewidth=2)

    ax.set_xlabel('Current Density (A/$cm^{-2}$)')
    ax.set_ylabel('Luminance (cd/$m^{-2}$)')
    ax.set_title(f'Luminance vs. Current Density \nfor {Sample_Name}')
    st.pyplot(fig)
    
    if save_figs:
        plt.savefig(f'{date_string}{Sample_Name}_Current_v_Luminance.png', bbox_inches='tight')

    
def graph22(x_lo, x_hi, y_lo, y_hi):
    if dev_mode:
        st.write("graph22")
    fig = plt.figure(figsize=(3, 3))
    ax = fig.add_axes([0, 0, 1, 1])

    ax.plot(IV_EL[:,6]/1000,IV_EL[:,10],linewidth=2)

    ax.set_xlabel('Current Density (A/$cm^{-2}$)')
    ax.set_ylabel('Luminous Efficacy (lm/W)')
    ax.set_title(f'Luminous Efficacy vs. Current Density \nfor {Sample_Name}')
    
    if x_lo < 0.0 or x_hi > 0.0:
        ax.set_xlim(x_lo,x_hi)
    
    if y_lo < 0.0 or y_hi > 0.0:
        ax.set_ylim(y_lo,y_hi)

    ax.set_xscale('log') #as opposed to 'linear'
    st.pyplot(fig)
    
    if save_figs:
        plt.savefig(f'{date_string}{Sample_Name}_Current_v_Luminous_Efficacy.png', bbox_inches='tight')
    
    ##########################################################
    
def graph26(current, luminance, start_voltage, x_lo, x_hi, cd_y_lo, cd_y_hi, l_y_lo, l_y_hi):
    if dev_mode:
        st.write("graph26")
    #Now plotting a JVL curve
    
    # default graph -------------------------------------------------------------------------------
    fig, ax1 = plt.subplots(figsize=(4, 4))
    ax2 = ax1.twinx()
    
#     st.write(IV_EL)
    line1, = ax1.plot(IV_EL[:,0],IV_EL[:,6],linewidth=2, color ='green', label = 'Current Density')
    line2, = ax2.plot(IV_EL[:,0],IV_EL[:,8],linewidth=2, label = 'Luminance')
    
    #----------------------------------------------------------------------------------------------
    
    # default x limits
    left, right = plt.xlim()
    
    # find the point to start plotting
    idx = 0
    for x in range(0, numpoints):
        if IV_EL[x,0] >= start_voltage:
            break
            
        idx +=1
    
    fig, ax1 = plt.subplots(figsize=(4, 4))
    ax2 = ax1.twinx()
    line1, = ax1.plot(IV_EL[idx:,0],IV_EL[idx:,6],linewidth=2, color ='green', label = 'Current Density')
    line2, = ax2.plot(IV_EL[idx:,0],IV_EL[idx:,8],linewidth=2, label = 'Luminance')
    
    
    ax1.legend(handles=[line1, line2], fontsize = 10)

    ax1.set_xlabel(r'Voltage (V)', labelpad=10)
    ax1.set_ylabel('Current density (mA$.cm^{-2}$)', labelpad=10)
    ax1.set_title(f'JVL curve \nfor {Sample_Name}', fontsize = 14)
    ax2.set_ylabel('Luminance (cd.$m^{-2}$)')
    
    # default x range
    ax1.set_xlim(left, right)
    
    if x_lo < 0.0 or x_hi > 0.0:
        ax1.set_xlim(x_lo,x_hi)
    
    if cd_y_lo < 0.0 or cd_y_hi > 0.0:
        ax1.set_ylim(cd_y_lo,cd_y_hi)
        
    if l_y_lo < 0.0 or l_y_hi > 0.0:
        ax2.set_ylim(l_y_lo,l_y_hi)
        
    
    ax1.set_yscale(current)
    ax2.set_yscale(luminance)
    st.pyplot(fig)
    
    if save_figs:
        plt.savefig(f'{date_string}{Sample_Name}_JVL_curve.png', bbox_inches='tight')


######################################

def graph30(increment):
    if dev_mode:
        st.write("graph30")
    fig = plt.figure(figsize=(3, 3))
    ax = fig.add_axes([0, 0, 1, 1])
    selected_spectra = np.arange(0,numpoints,increment)
    for k in selected_spectra:
        ax.plot(Spectra[:,0],Spectra[:,k+1],color = colors(k/numpoints), 
                 label=f'{IV_EL[k,0]}V', linewidth = 1)
    ax.set_xlabel('Wavelength(nm)')
    ax.set_ylabel('Counts')
    ax.set_title(f'Electroluminescence Spectra at Each\n Bias Voltage of {Sample_Name}')
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0, frameon=False, fontsize=10, ncol=3)
    st.pyplot(fig)
    #plt.savefig(f'IV+Spectra/{date_string}{Sample_Name}_Spectra.png')
    
    if save_figs:
        plt.savefig(f'{date_string}{Sample_Name}_Selected_EL_Spectra_per_Voltage.png', bbox_inches='tight')
    

def sidebar_controls():
    st.sidebar.header("Select the plots to show:")
    
    g26 = st.sidebar.checkbox("Current and Luminance vs. Voltage", value=True)
    if g26:
        col1, col2 = st.sidebar.columns(2, gap="medium")
        with col1:
            current26 = st.select_slider('Current', options=['log','linear'], value='log')
        with col2:
            luminance26 = st.select_slider('Luminance', options=['log','linear'], value='log')
            
        start_volt_input = st.sidebar.number_input("Start graphing at voltage (V)", value=0.0, format='%f', key=0)
            
        # x range
        col1, col2 = st.sidebar.columns(2, gap="small")
        with col1:
            x_lo_input = st.number_input("x min", format='%f', key=0)
        with col2:
            x_hi_input = st.number_input("x max", format='%f', key=0)
        
        # current density
        col1, col2 = st.sidebar.columns(2, gap="small")
        with col1:
            cd_y_lo_input = st.number_input("Current density y min", format='%f')
        with col2:
            cd_y_hi_input = st.number_input("Current density y max", format='%f')
            
        # luminance
        col1, col2 = st.sidebar.columns(2, gap="small")
        with col1:
            l_y_lo_input = st.number_input("Luminance y min", format='%f')
        with col2:
            l_y_hi_input = st.number_input("Luminance y max", format='%f')
        
        
        buf, mid, buf = st.columns([1,4,1])
        with mid:
            graph26(current26, luminance26, start_volt_input,
                    x_lo_input, x_hi_input, 
                    cd_y_lo_input, cd_y_hi_input, 
                    l_y_lo_input, l_y_hi_input)
    
    
    g12 = st.sidebar.checkbox("EQE% vs. Current Density", value=True)
    if g12:
        col1, buf = st.sidebar.columns(2, gap="medium")
        with col1:
            EQE12 = st.select_slider('EQE%', options=['log','linear'], value='linear')
            
        col1, col2 = st.sidebar.columns(2, gap="small")
        with col1:
            x_lo_input = st.number_input("x min", format='%f', key=1)
        with col2:
            x_hi_input = st.number_input("x max", format='%f', key=1)
        
        col1, col2 = st.sidebar.columns(2, gap="small")
        with col1:
            y_lo_input = st.number_input("y min", format='%f', key=1)
        with col2:
            y_hi_input = st.number_input("y max", format='%f', key=1)
        
        buf, mid, buf = st.columns([1,3,1])
        with mid:
            graph12(EQE12, x_lo_input, x_hi_input, y_lo_input, y_hi_input)
    
    g17 = st.sidebar.checkbox("Luminance vs Current Density", value=True)
    if g17:
        buf, mid, buf = st.columns([1,3,1])
        with mid:
            graph17()
    
    g22 = st.sidebar.checkbox("Luminance Efficacy vs Current Density", value=True)
    if g22:
        col1, col2 = st.sidebar.columns(2, gap="small")
        with col1:
            x_lo_input = st.number_input("x min", format='%f', key=2)
        with col2:
            x_hi_input = st.number_input("x max", format='%f', key=2)
        
        col1, col2 = st.sidebar.columns(2, gap="small")
        with col1:
            y_lo_input = st.number_input("y min", format='%f', key=2)
        with col2:
            y_hi_input = st.number_input("y max", format='%f', key=2)
            
        buf, mid, buf = st.columns([1,3,1])
        with mid:
            graph22(x_lo_input, x_hi_input, y_lo_input, y_hi_input)
    
    g3 = st.sidebar.checkbox("Electroluminescence (EL) Spectra", value=True)
    if g3:
        graph3()
        
    g30 = st.sidebar.checkbox("Selected EL Spectra", value=True)
    if g30:
        increment = st.sidebar.slider("EL spectra at each __ voltage", min_value=1, max_value=15, value=5)
        graph30(increment)
        
    g7 = st.sidebar.checkbox("Normalized EL Spectra", value=False)
    if g7:
        graph7()
    
    g2 = st.sidebar.checkbox("Photocurrent vs. Voltage")
    if g2:
        buf, mid, buf = st.columns([1,3,1])
        with mid:
            graph2()
        
    g9 = st.sidebar.checkbox("Photon Flux vs. Voltage")
    if g9:
        buf, mid, buf = st.columns([1,3,1])
        with mid:
            graph9()
        
    g10 = st.sidebar.checkbox("Radiance vs. Voltage")
    if g10:
        buf, mid, buf = st.columns([1,3,1])
        with mid:
            graph10()
        

    st.sidebar.write("")
    st.sidebar.header("Calibration Plots")
    
    g5 = st.sidebar.checkbox("Photodetector EQE vs. Wavelength")
    if g5:
        buf, mid, buf = st.columns([1,3,1])
        with mid:
            graph5()
        
    g4 = st.sidebar.checkbox("Responsivity vs. Wavelength")
    if g4:
        buf, mid, buf = st.columns([1,3,1])
        with mid:
            graph4()
        
    g15 = st.sidebar.checkbox("Phototopic Function of the Human Eye (Phototopic Factor vs. Wavelength)")
    if g15:
        buf, mid, buf = st.columns([1,3,1])
        with mid:
            graph15()
     
    st.sidebar.write("")
    st.sidebar.write("")

    
if __name__ == '__main__':
    intro()
    
    with st.expander('Uploads', expanded=True):
        Sample_Name = st.text_input('Sample name', 'CommercialWhite1')
        save_figs = st.checkbox("Save selected graphs")

        f1, f2 = st.columns(2)
        with f1:
            spectra_input = st.file_uploader("Upload a spectra CSV")
        with f2:
            IV_photo_input = st.file_uploader("Upload an IV+photocurrent CSV")
#         photo_data_input = st.file_uploader("Upload photodetector data CSV")
        
        placeholder = st.empty()
        test = placeholder.button("USE DEFAULT FILES")

    if "load_state" not in st.session_state:
        st.session_state.load_state = False
        
    if spectra_input and IV_photo_input is not None:
        st.session_state.load_state = False
        placeholder.empty()
#         try:
        if dev_mode:
            st.write("Displaying plots based on your uploads:")
        pre(spectra_input, IV_photo_input)
        preprocess_data()
        sidebar_controls()
        
#         except:
#             st.error("Check your uploads for errors/formatting issues!")
    
    if (test or st.session_state.load_state):
        if dev_mode:
            st.write("Displaying plots based on default data:")
        st.session_state.load_state = True
        a = '2022-05-24Commercial_White1_spectra.csv'
        b = '2022-05-24Commercial_White1IV+photocurrent.csv'
#         c = 'StranksPhototopicLuminosityFunction.csv'
        
        pre(a, b)
        preprocess_data()
        sidebar_controls()
        