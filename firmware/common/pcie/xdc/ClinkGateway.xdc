##############################################################################
## This file is part of 'Camera link gateway'.
## It is subject to the license terms in the LICENSE.txt file found in the 
## top-level directory of this distribution and at: 
##    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
## No part of 'Camera link gateway', including this file, 
## may be copied, modified, propagated, or distributed except according to 
## the terms contained in the LICENSE.txt file.
##############################################################################

set_property USER_SLR_ASSIGNMENT SLR0 [get_cells {U_Hardware}]
set_property USER_SLR_ASSIGNMENT SLR1 [get_cells {U_Application}]

set_clock_groups -asynchronous -group [get_clocks -of_objects [get_pins U_axilClk/O]] -group [get_clocks -of_objects [get_pins U_Core/U_AxiPciePhy/U_AxiPcie/inst/pcie3_ip_i/inst/gt_top_i/phy_clk_i/bufg_gt_userclk/O]]
