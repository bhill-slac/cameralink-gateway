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
import rogue
import click

import cameralink_gateway as clDev
import axipcie

import lcls2_pgp_fw_lib.hardware.shared as shared

import ClinkFeb               as feb
import surf.protocols.batcher as batcher
import surf.protocols.clink   as cl
import l2si_core              as l2si


###################################################
# https://jira.slac.stanford.edu/browse/ESROGUE-459
###################################################
rogue.Version.minVersion('4.11.1')
rogue.Version.maxVersion('999.999.999')
# rogue.Version.exactVersion('4.11.1')

class ClinkDevRoot(shared.Root):

    def __init__(self,
                 dataDebug      = False,
                 dev            = '/dev/datadev_0',# path to PCIe device
                 enLclsI        = True,
                 enLclsII       = False,
                 startupMode    = False, # False = LCLS-I timing mode, True = LCLS-II timing mode
                 standAloneMode = False, # False = using fiber timing, True = locally generated timing
                 pgp3           = False, # true = PGPv3, false = PGP2b
                 pollEn         = True,  # Enable automatic polling registers
                 initRead       = True,  # Read all registers at start of the system
                 numLanes       = 4,     # Number of PGP lanes
                 camType        = None,
                 defaultFile    = None,
                 clDevTarget    = clDev.ClinkDevKcu1500,
                 **kwargs):

        # Set the firmware Version lock = firmware/targets/shared_version.mk
        self.FwVersionLock = 0x04060000

        # Set number of lanes to min. requirement
        if numLanes > len(camType):
            laneSize = len(camType)
        else:
            laneSize = numLanes

        # Set local variables
        self.camType        = [camType[i] for i in range(laneSize)]
        self.defaultFile    = defaultFile
        self.dev            = dev
        self.startupMode    = startupMode
        self.standAloneMode = standAloneMode

        # Check for simulation
        if dev == 'sim':
            kwargs['timeout'] = 100000000 # 100 s
        else:
            kwargs['timeout'] = 5000000 # 5 s

        # Pass custom value to parent via super function
        super().__init__(
            dev         = dev,
            pgp3        = pgp3,
            pollEn      = pollEn,
            initRead    = initRead,
            numLanes    = laneSize,
            **kwargs)

        # Unhide RemoteVariableDump and other useful commands
        self.RemoteVariableDump.hidden = False
        self.DumpCfgVars.hidden = False

        # Create memory interface
        self.memMap = axipcie.createAxiPcieMemMap(dev, 'localhost', 8000)

        # Instantiate the top level Device and pass it the memory map
        self.add(clDevTarget(
            name     = 'ClinkPcie',
            memBase  = self.memMap,
            numLanes = laneSize,
            pgp3     = pgp3,
            enLclsI  = enLclsI,
            enLclsII = enLclsII,
            expand   = True,
        ))

        # Create DMA streams
        self.dmaStreams = axipcie.createAxiPcieDmaStreams(dev, {lane:{dest for dest in range(4)} for lane in range(laneSize)}, 'localhost', 8000)

        # Check if not doing simulation
        if (dev!='sim'):

            # Create arrays to be filled
            self._srp = [None for lane in range(laneSize)]

            # Create the stream interface
            for lane in range(laneSize):

                # SRP
                self._srp[lane] = rogue.protocols.srp.SrpV3()
                pr.streamConnectBiDir(self.dmaStreams[lane][0],self._srp[lane])

                # CameraLink Feb Board
                self.add(feb.ClinkFeb(
                    name       = (f'ClinkFeb[{lane}]'),
                    memBase    = self._srp[lane],
                    serial     = self.dmaStreams[lane][2],
                    camType    = self.camType[lane],
                    version3   = pgp3,
                    enableDeps = [self.ClinkPcie.Hsio.PgpMon[lane].RxRemLinkReady], # Only allow access if the PGP link is established
                    expand     = True,
                ))

        # Else doing Rogue VCS simulation
        else:
            self.roguePgp = shared.RogueStreams(numLanes=laneSize, pgp3=pgp3)

            # Create arrays to be filled
            self._frameGen = [None for lane in range(laneSize)]

            # Create the stream interface
            for lane in range(laneSize):

                # Create the frame generator
                self._frameGen[lane] = MyCustomMaster()

                # Connect the frame generator
                print(self.roguePgp.pgpStreams)
                self._frameGen[lane] >> self.roguePgp.pgpStreams[lane][1]

                # Create a command to execute the frame generator
                self.add(pr.BaseCommand(
                    name         = f'GenFrame[{lane}]',
                    function     = lambda cmd, lane=lane: self._frameGen[lane].myFrameGen(),
                ))

                # Create a command to execute the frame generator. Accepts user data argument
                self.add(pr.BaseCommand(
                    name         = f'GenUserFrame[{lane}]',
                    function     = lambda cmd, lane=lane: self._frameGen[lane].myFrameGen,
                ))

        # Create arrays to be filled
        self._dbg = [None for lane in range(laneSize)]
        self.unbatchers = [rogue.protocols.batcher.SplitterV1() for lane in range(laneSize)]

        # Create the stream interface
        for lane in range(laneSize):
            # Debug slave
            if dataDebug:
                # Connect the streams
                self.dmaStreams[lane][1] >> self.unbatchers[lane] >> self._dbg[lane]

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
            eventBuilder = self.find(typ=batcher.AxiStreamBatcherEventBuilder)
            trigger      = self.find(typ=l2si.TriggerEventBuffer)

            # Turn off the triggering
            for devPtr in trigger:
                devPtr.MasterEnable.set(False)

            # Flush the downstream data/trigger pipelines
            for devPtr in eventBuilder:
                devPtr.Blowoff.set(True)

            # Update the run state status variable
            self.RunState.set(False)

        @self.command(description  = 'starts the triggers and allow steams to flow to DMA engine')
        def StartRun():
            print ('ClinkDev.StartRun() executed')

            # Get devices
            eventBuilder = self.find(typ=batcher.AxiStreamBatcherEventBuilder)
            trigger      = self.find(typ=l2si.TriggerEventBuffer)

            # Reset all counters
            self.CountReset()

            # Arm for data/trigger stream
            for devPtr in eventBuilder:
                devPtr.Blowoff.set(False)

            # Turn on the triggering
            for devPtr in trigger:
                devPtr.MasterEnable.set(True)

            # Update the run state status variable
            self.RunState.set(True)

    def start(self, **kwargs):
        super().start(**kwargs)

        # Hide all the "enable" variables
        for enableList in self.find(typ=pr.EnableVariable):
            # Hide by default
            enableList.hidden = True

        # Check if simulation
        if (self.dev=='sim'):
            pass

        else:
            # Dump the address map
            self.saveAddressMap( "dump/addressMapDump.dump" )
            self.saveAddressMap( "dump/addressMapDump.h", headerEn=True )

            # Dump the state of the hardware before configuration
            self.ReadAll()
            self.remoteVariableDump('dump/regdump-pre-config.txt', True, False );
            self.SaveState('dump/state-dump-pre-config.yml')

            # Check for PCIe FW version
            fwVersion = self.ClinkPcie.AxiPcieCore.AxiVersion.FpgaVersion.get()
            if (fwVersion != self.FwVersionLock):
                errMsg = f"""
                    PCIe.AxiVersion.FpgaVersion = {fwVersion:#04x} != {self.FwVersionLock:#04x}
                    Please update PCIe firmware using software/scripts/updatePcieFpga.py
                    """
                click.secho(errMsg, bg='red')
                raise ValueError(errMsg)

            # Check for FEB FW version
            for lane in range(self.numLanes):
                # Unhide the because dependent on PGP link status
                self.ClinkFeb[lane].enable.hidden = False
                self.ClinkPcie.Hsio.TimingRx.TriggerEventManager.enable.hidden = False
                # Check for PGP link up
                if (self.ClinkPcie.Hsio.PgpMon[lane].RxRemLinkReady.get() != 0):
                    # Check for FW version
                    fwVersion = self.ClinkFeb[lane].AxiVersion.FpgaVersion.get()
                    if (fwVersion != self.FwVersionLock):
                        errMsg = f"""
                            Fpga[lane={lane}].AxiVersion.FpgaVersion = {fwVersion:#04x} != {self.FwVersionLock:#04x}
                            Please update Fpga[{lane}] at Lane={lane} firmware using software/scripts/updateFeb.py
                            """
                        click.secho(errMsg, bg='red')
                        raise ValueError(errMsg)
                else:
                    self.ClinkPcie.Application.AppLane[lane]._expand = False

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

            # Useful pointer
            timingRx = self.ClinkPcie.Hsio.TimingRx

            # Start up the timing system
            if self.startupMode:

                # Set the default to  LCLS-I mode
                defaultFile = ["config/defaults_LCLS-II.yml",self.defaultFile]

                # Startup in LCLS-II mode
                if self.standAloneMode:
                    timingRx.ConfigureXpmMini()
                else:
                    timingRx.ConfigLclsTimingV2()

            else:

                # Set the default to  LCLS-I mode
                defaultFile = ["config/defaults_LCLS-I.yml",self.defaultFile]

                # Startup in LCLS-I mode
                if self.standAloneMode:
                    timingRx.ConfigureTpgMiniStream()
                else:
                    timingRx.ConfigLclsTimingV1()

            # Read all the variables
            self.ReadAll()

            # Load the YAML configurations
            print(f'Loading {defaultFile} Configuration File...')
            self.LoadConfig(defaultFile)

            # Dump the state of the hardware after configuration
            self.ReadAll()
            self.remoteVariableDump('dump/regdump-post-config.txt', True, False );
            self.SaveState('dump/state-dump-post-config.yml')

    # Function calls after loading YAML configuration
    def initialize(self):
        super().initialize()
        self.StopRun()
        self.CountReset()
