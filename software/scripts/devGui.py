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

import os
import sys
import time
import argparse
import importlib
import rogue

if __name__ == "__main__":

#################################################################

    # Set the argument parser
    parser = argparse.ArgumentParser()

    # Convert str to bool
    argBool = lambda s: s.lower() in ['true', 't', 'yes', '1']

    # Add arguments
    parser.add_argument(
        "--dev",
        type     = str,
        required = False,
        default  = '/dev/datadev_0',
        help     = "path to device",
    )

    parser.add_argument(
        "--pgp4",
        type     = argBool,
        required = False,
        default  = False, # Default: Enable PGP2b
        help     = "False = PGP2b (default), True = PGPv4",
    )

    parser.add_argument(
        "--enLclsI",
        type     = argBool,
        required = False,
        default  = True, # Default: Enable LCLS-I hardware registers
        help     = "Enable LCLS-I hardware registers",
    )

    parser.add_argument(
        "--enLclsII",
        type     = argBool,
        required = False,
        default  = False, # Default: Disable LCLS-II hardware registers
        help     = "Enable LCLS-II hardware registers",
    )

    parser.add_argument(
        "--startupMode",
        type     = argBool,
        required = False,
        default  = False, # Default: False = LCLS-I timing mode
        help     = "False = LCLS-I timing mode, True = LCLS-II timing mode",
    )

    parser.add_argument(
        "--standAloneMode",
        type     = argBool,
        required = False,
        default  = False, # Default: False = using fiber timing
        help     = "False = using fiber timing, True = locally generated timing",
    )

    parser.add_argument(
        "--enableDump",
        type     = argBool,
        required = False,
        default  = True,
        help     = "True to dump .h and pre/post state",
    )

    parser.add_argument(
        "--camType",
        nargs    ='+',
        required = True,
        help     = "List of camera type",
    )

    parser.add_argument(
        "--pollEn",
        type     = argBool,
        required = False,
        default  = True,
        help     = "Enable auto-polling",
    )

    parser.add_argument(
        "--initRead",
        type     = argBool,
        required = False,
        default  = True,
        help     = "Enable read all variables at start",
    )

    parser.add_argument(
        "--defaultFile",
        type     = str,
        required = False,
        default  = None,
        help     = "Sets the default YAML configuration file to be loaded at the root.start()",
    )

    parser.add_argument(
        "--seuDumpDir",
        type     = str,
        required = False,
        default  = None,
        help     = "path to SEU dump directory",
    )

    parser.add_argument(
        "--serverPort",
        type     = int,
        required = False,
        default  = 9099,
        help     = "Zeromq server port",
    )

    parser.add_argument(
        "--releaseZip",
        type     = str,
        required = False,
        default  = None,
        help     = "Sets the default YAML configuration file to be loaded at the root.start()",
    )

    parser.add_argument(
        "--guiType",
        type     = str,
        required = False,
        default  = 'PyDM',
        help     = "Sets the GUI type (PyDM, PyQt, or None)",
    )
    # Get the arguments
    args = parser.parse_args()

    if args.guiType == 'PyDM' or args.guiType == 'PyQt':
        import pyrogue.gui
        import pyrogue.pydm

    #################################################################

    # First see if submodule packages are already in the python path
    try:
        import axi_pcie_core
        import lcls2_pgp_fw_lib
        import lcls_timing_core
        import l2si_core
        import clink_gateway_fw_lib
        import surf

    # Otherwise assume it is relative in a standard development directory structure
    except:

        # Check for release zip file path
        if args.releaseZip is not None:
            pyrogue.addLibraryPath(args.releaseZip + '/python')
        else:
            import setupLibPaths

    # Load the cameralink-gateway package
    import cameralink_gateway

    #################################################################

    with cameralink_gateway.ClinkDevRoot(
            dev            = args.dev,
            pollEn         = args.pollEn,
            initRead       = args.initRead,
            camType        = args.camType,
            defaultFile    = args.defaultFile,
            enLclsI        = (args.enLclsII or not args.startupMode),
            enLclsII       = (args.enLclsII or args.startupMode),
            startupMode    = args.startupMode,
            standAloneMode = args.standAloneMode,
            enableDump     = args.enableDump,
            pgp4           = args.pgp4,
            seuDumpDir     = args.seuDumpDir,
        ) as root:

        ######################
        # Development PyDM GUI
        ######################
        if (args.guiType == 'PyDM'):

            pyrogue.pydm.runPyDM(
                root  = root,
                sizeX = 800,
                sizeY = 1000,
            )

        #################
        # Legacy PyQT GUI
        #################
        elif (args.guiType == 'PyQt'):

            # Create GUI
            appTop = pyrogue.gui.application(sys.argv)
            guiTop = pyrogue.gui.GuiTop()
            guiTop.addTree(root)
            guiTop.resize(800, 1000)

            # Run gui
            appTop.exec_()
            root.stop()

        #################
        # No GUI
        #################
        elif (args.guiType == 'None'):

            # Wait to be killed via Ctrl-C
            print('Running root server.  Hit Ctrl-C to exit')
            try:
                while True:
                    time.sleep(1)
            except:
                pass
            print('Stopping root server...')
            root.stop()

        ####################
        # Undefined GUI type
        ####################
        else:
            raise ValueError("Invalid GUI type (%s)" % (args.guiType) )

    #################################################################
