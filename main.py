import math
import threading
import time
import BlynkLib
import RPi.GPIO as GPIO
import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import os
import ES2EEPROMUtils
import random

#store the state of the buzzer
buzzerBool=False

# create the spi bus
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)

# create the cs (chip select)
cs = digitalio.DigitalInOut(board.D5)

# create the mcp object
mcp = MCP.MCP3008(spi, cs)

# create an analog input channel on pin 0
chan = AnalogIn(mcp, MCP.P0)

#Buzzer connection
buzzer=None

# keeps the current sleep rate or the rate of checking temparature
samplingrate = 5

#boolen to stop the
state=False

# The blynk authorisation
blynk_auth = '-p4vKFfb4pHdytVusqfRVPPh0OFwgvxR'

blynk = BlynkLib.Blynk(blynk_auth)
eeprom = ES2EEPROMUtils.ES2EEPROM()

# Setup method to setup the board of pins of the Pi
def setup():
    #SWITCH OFF WARNINGS
    GPIO.setwarnings(False)

    #SETUP GPIO OF THE BUZZER
    GPIO.setup(15, GPIO.OUT)

    # Setup regular GPIO
    GPIO.setup([17,27], GPIO.IN, pull_up_down = GPIO.PUD_UP )



    # Setup debouncing and callbacks
    GPIO.add_event_detect(17, GPIO.RISING, callback=btn_change_time_interval, bouncetime=200)
    GPIO.add_event_detect(27, GPIO.RISING, callback=btn_start_stop, bouncetime=200)

# This method creates an event listener to listen for events in the Blynk application
@blynk.VIRTUAL_WRITE(4)
def my_button_handler(value):
    global state
    if(value[0]=='0'):
      state=False
    else:
      state=True

# Method to listen for events when the user chages the sampling rate
@blynk.VIRTUAL_WRITE(5)
def my_switch_handler(value):
    global samplingrate
    if(value[0]=='1'):
       samplingrate=2

    elif(value[0]=='2'):
       samplingrate=5

    elif(value[0]=='3'):
       samplingrate=10

# Here we use this method to continuously write our data to the terminal of the Blynk app
def writeToBlynkTerminal(time, sysTime, temp):
    global blynk
    output = '{} {} {}\n'.format(time,sysTime,temp)

    blynk.virtual_write(2,temp)
    blynk.virtual_write(0,output)

# Clears the data in displayed on the terminal of the Blynk app
def clearTerminal():
    print("Clearing terminal!!!")
    blynk.virtual_write(0,'clr')
    os.system('clear')

# Used to change the sampling rate through a button press, this is implementation fro project A
def btn_change_time_interval(channel):
    global samplingrate
    # change smapling rate when the user presses the button
    if (samplingrate == 10):
        samplingrate = 2
    elif (samplingrate == 2):
        samplingrate = 5
    else:
        samplingrate = 10
    print("Changed Smapling Rate to: ",samplingrate)

# this method calculates the temperature read from the thermostat and returns it
def tempCalc (value) :
    # Calculate the temp using the output from the ADC
    tempC = value *(190/65536) -40
    return math.trunc( tempC /4.53)
    
    return value*1000.0*0.010*0.500


# This method is self-explanatory. It writes data to the EEPROM for storage
def writeToEEPROm(time,secs, temp):
    # fetching samples and temperatures
    samples, tempArrays = readFromEEPROM()
    date_time = datetime.datetime.strptime(time,"%H:%M%S")
    secs_time = datetime.datetime.strptime(secs,"%H:%M:%S")

    #change to seconds
    t = date_time.total_seconds()
    s = secs_time.total_seconds()

    # add to array
    tempArrays.append(t)
    tempArrays.append(s)
    tempArrays.appemd(temp)

    if len(tempArray>20):
       del tempArray[0:2] #delete  first array

    #clear EEPROM
    eeprom.clear(4096)
    eeprom.write_block(0, [samples+1])
 
    #write to EEprom
    eeprom.write_block(tempArrays)

# This is also self-explanatory. It reads data previously stored from the EEPROM
def readFromEEPROM():
    global eeprom
    # get the Number of temperature/sample values in  eeprom
    numberOfSamples = eeprom.read_block(0, [4])

    # get the temperature values from the eeprom
    temp_value = eeprom.read_block(1,numberOfSamples)

    # Array of temperatures
    return  numberOfSamples,temp_value

# This method performs most of the fundamental operations required by the system. And print the data to the Terminal
def print_temp1 ():
    global samplingrate
    global state

    samplingrate = 5
    start = True
    t = time.localtime()
    #blynk.virtual_write(4,"2")
    while True :
        if(state==False):
            print("System off!!!")
            break
        if(start):
            time.sleep(samplingrate)
            temp=tempCalc(chan.voltage)
            t = time.localtime()
            print ('{: <12} {: <12} {: <5}'.format(str(time.strftime("%H:%M:%S",t)),str(time.strftime("%H:%M:%S", time.localtime(0-60*60*1))), temp))
            writeToBlynkTerminal(str(time.strftime("%H:%M:%S",t)),str(time.strftime("%H:%M:%S",time.localtime(0-60*60*1))),temp)
            start=False
            trigger_buzzer(temp)
            #time.sleep(samplingrate)

        elif(True):
            x=time.localtime()
            temp=tempCalc(chan.voltage)
            print ('{: <12} {: <12} {: <5}'.format(str(time.strftime("%H:%M:%S",x)),str(time.strftime("%H:%M:%S", time_dif(x,t))), temp))
            writeToBlynkTerminal(str(time.strftime("%H:%M:%S",x)), str(time.strftime("%H:%M:%S",time_dif(x,t))), temp)

            trigger_buzzer(temp)

        # sleep for the required sampling rate
        time.sleep(samplingrate)


def time_dif(current_time,start_time):
    x_=(current_time.tm_hour*60*60+current_time.tm_min*60)+current_time.tm_sec
    y_=(start_time.tm_hour*60*60+start_time.tm_min*60)+start_time.tm_sec

    return time.localtime(x_-y_-60*60*1)

# Method used to read start and stop button input
def btn_start_stop(channel):
    global  state

    if(state):
        state=False
    else:
        state=True

# Method to trigger the buzzer when a certain threshold is reached
def trigger_buzzer(temp):
    global  buzzerBool
    if(temp>25):
        #sound buzzer
        GPIO.output(15, GPIO.HIGH)
    else:
        GPIO.output(15, GPIO.LOW)

    pass



# The main methos which is the entry point to the system. Press the green button in the gutter to run the script.
if __name__ == '__main__':
    try:
        setup()
        boolean = False
        while True:
            if(boolean == False and state==True):
                clearTerminal()
                print("System on!!!")
                x = threading.Thread(target=print_temp1)
                x.start()
                boolean=True
            elif(state==False):
                boolean = False

            blynk.run()
            pass
    except Exception as e:

        print(e)
    finally:
        GPIO.cleanup()
