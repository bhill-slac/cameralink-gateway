#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the 'Camera link gateway'. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the 'Camera link gateway', including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import pyrogue as pr

import rogue.protocols

import XilinxKcu1500Pgp       as kcu1500
import ClinkFeb               as feb
import Application            as app
import surf.protocols.clink   as cl
import surf.protocols.batcher as batcher
import LclsTimingCore         as timingCore

import rogue
import rogue.interfaces.stream

import click

rogue.Version.minVersion('3.7.0') 

class MyCustomMaster(rogue.interfaces.stream.Master):

    # Init method must call the parent class init
    def __init__(self):
        super().__init__()
        self._maxSize = 2048

    # Method for generating a frame
    def myFrameGen(self):
        # First request an empty from from the primary slave
        # The first arg is the size, the second arg is a boolean
        # indicating if we can allow zero copy buffers, usually set to true
        frame = self._reqFrame(self._maxSize, True) # Here we request a frame capable of holding 2048 bytes

        # Create a 2048 byte array with an incrementing value
        ba = bytearray([(i&0xFF) for i in range(self._maxSize)])

        # Write the data to the frame at offset 0
        frame.write(ba,0)
        
        # Send the frame to the currently attached slaves
        self._sendFrame(frame)

class ClinkDev(kcu1500.Core):

    def __init__(self,
            name        = 'ClinkDev',
            description = 'Container for CameraLink Dev',
            dev         = '/dev/datadev_0',# path to PCIe device
            version3    = False,           # true = PGPv3, false = PGP2b
            pollEn      = True,            # Enable automatic polling registers
            initRead    = True,            # Read all registers at start of the system
            numLane     = 4,               # Number of PGP lanes
            camType     = ['Opal1000',None],
            defaultFile = None,
            **kwargs
        ):
        super().__init__(
            name        = name, 
            description = description, 
            dev         = dev, 
            version3    = version3, 
            numLane     = numLane, 
            **kwargs
        )
        
        self.defaultFile = defaultFile
        
        # Set the min. firmware Versions
        self.minPcieVersion = 0x01000200
        self.minFebVersion  = 0x01000200
        
        # PGP Application on PCIe 
        self.add(app.Application(
            memBase  = self._memMap,
            numLane  = numLane,
            expand   = True,
        ))

        # Check if not doing simulation
        if (dev!='sim'): 
            
            # Create arrays to be filled
            self._srp = [None for lane in range(numLane)]
            
            # Create the stream interface
            for lane in range(numLane):
                            
                # SRP
                self._srp[lane] = rogue.protocols.srp.SrpV3()
                pr.streamConnectBiDir(self._dma[lane][0],self._srp[lane])
                         
                # CameraLink Feb Board
                self.add(feb.ClinkFeb(      
                    name       = (f'ClinkFeb[{lane}]'), 
                    memBase    = self._srp[lane], 
                    serial     = [self._dma[lane][2],self._dma[lane][3]],
                    camType    = camType,
                    version3   = version3,
                    enableDeps = [self.Hardware.PgpMon[lane].RxRemLinkReady], # Only allow access if the PGP link is established
                    expand     = False,
                ))         
                
        # Else doing Rogue VCS simulation
        else:
        
            # Create arrays to be filled
            self._frameGen = [None for lane in range(numLane)]
            
            # Create the stream interface
            for lane in range(numLane):        
            
                # Create the frame generator
                self._frameGen[lane] = MyCustomMaster()
                
                # Connect the frame generator
                pr.streamConnect(self._frameGen[lane],self._pgp[lane][1]) 
                    
                # Create a command to execute the frame generator
                self.add(pr.BaseCommand(   
                    name         = f'GenFrame[{lane}]',
                    function     = lambda cmd, lane=lane: self._frameGen[lane].myFrameGen(),
                ))
                
                
        self.add(pr.LocalVariable(
            name        = 'RunState', 
            description = 'Run state status, which is controlled by the StopRun() and StartRun() commands',
            mode        = 'RO', 
            value       = False,
        ))        
        
        @self.command(description  = 'Stops the triggers and blows off data in the pipeline')        
        def StopRun():
            print ('ClinkDev.StopRun() executed')
            
            # Get devices
            trigChDev = self.find(typ=timingCore.EvrV2ChannelReg)
            
            # Turn off the triggering
            for devPtr in trigChDev:
                devPtr.EnableReg.set(False)

            # Update the run state status variable
            self.RunState.set(False)
                
        @self.command(description  = 'starts the triggers and allow steams to flow to DMA engine')        
        def StartRun():
            print ('ClinkDev.StartRun() executed')
            
            # Get devices
            trigChDev = self.find(typ=timingCore.EvrV2ChannelReg)
                
            # Reset all counters
            self.CountReset()
                          
            # Turn on the triggering
            for devPtr in trigChDev:
                devPtr.EnableReg.set(True)  
                
            # Update the run state status variable
            self.RunState.set(True)                 
                
        # Start the system
        self.start(
            pollEn   = self._pollEn,
            initRead = self._initRead,
            timeout  = self._timeout,
        )
        
        # Hide all the "enable" variables
        for enableList in self.find(typ=pr.EnableVariable):
            # Hide by default
            enableList.hidden = True          
        
        # Check if simulation
        if (dev=='sim'):
            # Disable the PGP PHY device (speed up the simulation)
            self.Hardware.enable.set(False)
            self.Hardware.hidden = True
            # Bypass the time AXIS channel
            eventDev = self.find(typ=batcher.AxiStreamBatcherEventBuilder)
            for dev in eventDev:
                dev.Bypass.set(0x1)          
        else:
            # Read all the variables
            self.ReadAll()
            
            # Check for min. PCIe FW version
            fwVersion = self.Hardware.AxiPcieCore.AxiVersion.FpgaVersion.get()
            if (fwVersion < self.minPcieVersion):
                errMsg = f"""
                    PCIe.AxiVersion.FpgaVersion = {fwVersion:#04x} < {self.minPcieVersion:#04x}
                    Please update PCIe firmware using software/scripts/updatePcieFpga.py
                    """
                click.secho(errMsg, bg='red')
                raise ValueError(errMsg)            
                
            # Check for min. FEB FW version
            for lane in range(numLane):
                # Unhide the because dependent on PGP link status
                self.ClinkFeb[lane].enable.hidden  = False
                # Check for PGP link up
                if (self.Hardware.PgpMon[lane].RxRemLinkReady.get() != 0):
                    
                    # Expand for the GUI
                    self.ClinkFeb[lane]._expand = True
                    self.ClinkFeb[lane].ClinkTop._expand = True
                    self.ClinkFeb[lane].TrigCtrl[0]._expand = True
                    self.ClinkFeb[lane].TrigCtrl[1]._expand = True
                    if camType[1] is None:
                        self.ClinkFeb[lane].ClinkTop.Ch[1]._expand = False
                        self.ClinkFeb[lane].TrigCtrl[1]._expand = False
                    
                    # Check for min. FW version
                    fwVersion = self.ClinkFeb[lane].AxiVersion.FpgaVersion.get()
                    if (fwVersion < self.minFebVersion):
                        errMsg = f"""
                            Fpga[lane={lane}].AxiVersion.FpgaVersion = {fwVersion:#04x} < {self.minFebVersion:#04x}
                            Please update Fpga[{lane}] at Lane={lane} firmware using software/scripts/updateFeb.py
                            """
                        click.secho(errMsg, bg='red')
                        raise ValueError(errMsg)
                else:
                    self.Application.AppLane[lane]._expand = False
                    
            # Startup procedures for OPAL1000
            uartDev = self.find(typ=cl.UartOpal1000)
            for dev in uartDev:
                pass
                
            # Startup procedures for Piranha4
            uartDev = self.find(typ=cl.UartPiranha4)
            for dev in uartDev:
                dev.SendEscape()
                dev.SPF.setDisp('0')  
                dev.GCP()

            # Startup procedures for Up900cl12b
            uartDev = self.find(typ=cl.UartUp900cl12b)
            for dev in uartDev:
                clCh = self.find(typ=cl.ClinkChannel)
                for clChDev in clCh:
                    clChDev.SerThrottle.set(30000)
                dev.AM()
                dev.SM.set('f')
                dev.RP()

        # Load the configurations
        if self.defaultFile is not None:
            print(f'Loading {self.defaultFile} Configuration File...')
            self.LoadConfig(self.defaultFile)    

    # Function calls after loading YAML configuration
    def initialize(self):
        super().initialize()    
        self.StopRun()
        self.CountReset()
        
