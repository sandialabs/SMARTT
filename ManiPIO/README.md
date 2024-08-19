# ManiPIO

ManiPIO reads an input script to construct complex Events on ICS networks.

The classes for Events are made to handle ICS with the support of ICS classes structured in the way that the modbus
class is written. The critical functions the Event and trigger classes need are: .connect(), .close(), .write(), and .read()
the MB_PLC class formalizes how these functions need to work. This should allow flexibilty to add new ICS protocols, however the script 
constructor that reads input files is a little more rigid and only uses the modbus PLC class as of now. Minor modifications to the script reader
would allow more ICS classes by adding a PLC 'type' option.


## Installation

ManiPIO is dependent on [pymodbus](https://pymodbus.readthedocs.io/en/latest/).

```bash
pip install pymodbus
```

## Usage

ManiPIO is run from commandline.
It was written in python 3, and it is recommended to use it with python 3
ManiPIO requires an input script which is given in the commandline.

```bash
python3 ManiPIO.py Script.txt
```

## Input Scripts

Input scripts allow you to define PLCs and create Event objects.
Three objects are definable with these variables, **bold** means required:
 - PLC
    - **IP**
    - Port
    - WordOrder
    - ByteOrder
 - Event
    - **PLC**
    - **Mem**
    - **Values**
    - Format
    - Timing (required if type ramp)
    - Delay
    - Persist
 - Trigger
    - **Event**
    - **PLC**
    - **Mem**
    - **Values**
    - **Conditions**

 After defining the objects, you start them with the 'Start' declaration.
 > Start  
 > Event 1, Event 2, Trigger 1

### Input scripts have these rules to follow:
 - '#' at the beginning of a line denote a comment
    - You cannot comment after an input (e.g. 'values:1,2,3 #can't comment here')
 - Spaces indicate the end of an object
 - You must define a PLC before you use it in an Event or Trigger
 - Start the definition of the object with the type and its index number
 >PLC 1
 - Then define its variables with the syntax Variable:Value
 >IP:127.0.0.1
 - These variables accept lists:
    - Values
    - Mem
    - Timing
    - Format
    - Conditions
- Lists must be seperated with commas and can appear as either:
> Values:100,-100,100  
> Values:[100,-100,100]
- For PLCs and Events, reffer to their index numbers
> Event:1    
> PLC:2
- Start also reffers to the index of Events or triggers, but it uses a space between the type of object and its index number.
- Start entries at seperated with commas

### Example Script

```
# <--comments start with # and comments can only be on a line that starts as a comment
#
# Each component is seperated with a blank line
#
# NameofValue:Value is convention
# NameofValue:[Value,Value] is acceptible for lists
# But so is NameofValue:Value,Value only the comma is needed between values
#
# Event names come after their number and are only for your convenice,
# Trigger and Start will only reffer to their index number.
# Index numbers of all components MUST be in order, AND may not skip numbers
# because the reader indexes them itself, and you need to keep track of them!
# Timing is all in seconds, and nothing is case sensitive.

# PLCs start with "PLC" then the index number
# With the next line being the IP of the PLC
PLC 1 Name of PLC
IP:127.0.0.1 
# The port and Word and Byte order are optional inputs for the PLC.
# Port will default to Modbus 502
Port:502
# Word and Byte order default to Big, the input must either be Big or Little
# refering to the endianness of the memory registers.
WordOrder:Big
ByteOrder:Big

# PLCs used must be created BEFORE using them in an Event or trigger
# You don't need to create them all at the beginning, just before you use them in a function

#
Event 1 Name of Event
# You can comment within functions
# just don't leave a space
PLC:1
# Define the PLC the Event will communicated with (only one PLC allowed per Event)
mem:2050
# memory addresses of PLC that will be written
Values:100,200
# values you want to write to the PLC
# these change intent depending on the type of Event.
# Ramp Events mean you need at least 2 values that the ramp will slope between.
# Single Events are static values writen to memory, a list of values implies
# these different values will be written to their corrisponding list of memory addresses.
timing:30
# Timing also changes meaning depending on Event type
# Ramp type Events make timing = dt (Value[1]-Value[2])/dt = dx/dt
# You can have a list of timing values and this changes the dt between ramp transitions
# For single Events, timing only takes on meaning when in conjuction with the persist option
# timing with persist=True indicates the time between rewrites of the data to the memory register
type:ramp
# Type has 2 options, ramp or single
delay:0
# delay pauses the start of an Event for the given number of seconds
# if used with trigger, it will delay the beginning of an Event
persist:false
#persist will make Events loop forever

Event 2 
PLC:1
mem:2048
values:-100,100
timing:30
type:ramp
delay:0
persist:false

Trigger 1 
# define the Event the trigger will start after conditions are met 
# only one Event per trigger allowed 
Event:2
# trigger PLCs start with defining which PLC to look at
PLC:1 
# then define which memory registers to read
mem:2050
# Now define the values to compair to 
values:150
# and define how to compair the values
# conditions follow: (PLC register value) [<>] (trigger value)
conditions:>

# Start tells the constructor this is the end of definitions and which things to start
# you probably wont want all your Events to start, since some maybe triggered
# So after declaring 'start', list which Events and triggers you want to start
start 
Event 1, Trigger 1
# These follow the syntax of [Event or Trigger] [index number], [next Event/trigger] [index]
# The important parts the constructor is looking for are commas between items, and spaces between the type of 
# thing to start and their index number. Only 'Trigger' and 'Event' followed by a space and integer index number are valid objects.

```



