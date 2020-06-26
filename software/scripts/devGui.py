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
import argparse
import importlib
import rogue
import pyrogue.gui
import pyrogue.pydm

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
        "--hwType",
        type     = str,
        required = False,
        default  = 'kcu1500',
        help     = "kcu1500 or SlacPgpCardG4",
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
        help     = "Sets the GUI type (PyDM or PyQt)",
    )

    # Get the arguments
    args = parser.parse_args()

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

    # Select the hardware type
    if args.hwType == 'kcu1500':
        clDevTarget = cameralink_gateway.ClinkDevKcu1500
    else:
        clDevTarget = cameralink_gateway.ClinkDevSlacPgpCardG4

    #################################################################

    with cameralink_gateway.ClinkDevRoot(
            dev         = args.dev,
            pollEn      = args.pollEn,
            initRead    = args.initRead,
            camType     = args.camType,
            defaultFile = args.defaultFile,
            clDevTarget = clDevTarget,
        ) as root:

        # Dump the address map
        root.saveAddressMap( "addressMapDump.dump" )
        root.saveAddressMap( "addressMapDump.h", headerEn=True )

        ######################
        # Development PyDM GUI
        ######################
        if (args.guiType == 'PyDM'):

            pyrogue.pydm.runPyDM(root=root)

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

        ####################
        # Undefined GUI type
        ####################
        else:
            raise ValueError("Invalid GUI type (%s)" % (args.guiType) )

    #################################################################
