-------------------------------------------------------------------------------
-- File       : AppLane.vhd
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- This file is part of 'Camera link gateway'.
-- It is subject to the license terms in the LICENSE.txt file found in the 
-- top-level directory of this distribution and at: 
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
-- No part of 'Camera link gateway', including this file, 
-- may be copied, modified, propagated, or distributed except according to 
-- the terms contained in the LICENSE.txt file.
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;

use work.StdRtlPkg.all;
use work.AxiPkg.all;
use work.AxiLitePkg.all;
use work.AxiStreamPkg.all;
use work.AppPkg.all;

entity AppLane is
   generic (
      TPD_G           : time             := 1 ns;
      AXI_BASE_ADDR_G : slv(31 downto 0) := x"00C0_0000");
   port (
      -- AXI-Lite Interface
      axilClk         : in  sl;
      axilRst         : in  sl;
      axilReadMaster  : in  AxiLiteReadMasterType;
      axilReadSlave   : out AxiLiteReadSlaveType;
      axilWriteMaster : in  AxiLiteWriteMasterType;
      axilWriteSlave  : out AxiLiteWriteSlaveType;
      -- PGP Streams (axilClk domain)
      pgpIbMaster     : out AxiStreamMasterType;
      pgpIbSlave      : in  AxiStreamSlaveType;
      pgpObMasters    : in  AxiStreamQuadMasterType;
      pgpObSlaves     : out AxiStreamQuadSlaveType;
      -- Trigger Event streams (axilClk domain)
      trigMaster      : in  AxiStreamMasterType;
      trigSlave       : out AxiStreamSlaveType;
      -- DMA Interface (dmaClk domain)
      dmaClk          : in  sl;
      dmaRst          : in  sl;
      dmaIbMaster     : out AxiStreamMasterType;
      dmaIbSlave      : in  AxiStreamSlaveType;
      dmaObMaster     : in  AxiStreamMasterType;
      dmaObSlave      : out AxiStreamSlaveType);
end AppLane;

architecture mapping of AppLane is

   constant NUM_AXIL_MASTERS_C : positive := 1;

   constant AXIL_CONFIG_C : AxiLiteCrossbarMasterConfigArray(NUM_AXIL_MASTERS_C-1 downto 0) := genAxiLiteConfig(NUM_AXIL_MASTERS_C, AXI_BASE_ADDR_G, 20, 16);

   signal axilWriteMasters : AxiLiteWriteMasterArray(NUM_AXIL_MASTERS_C-1 downto 0);
   signal axilWriteSlaves  : AxiLiteWriteSlaveArray(NUM_AXIL_MASTERS_C-1 downto 0) := (others => AXI_LITE_WRITE_SLAVE_EMPTY_SLVERR_C);
   signal axilReadMasters  : AxiLiteReadMasterArray(NUM_AXIL_MASTERS_C-1 downto 0);
   signal axilReadSlaves   : AxiLiteReadSlaveArray(NUM_AXIL_MASTERS_C-1 downto 0)  := (others => AXI_LITE_READ_SLAVE_EMPTY_SLVERR_C);

   signal sifClMaster : AxiStreamMasterType;
   signal sifClSlave  : AxiStreamSlaveType;

   signal eventMaster : AxiStreamMasterType;
   signal eventSlave  : AxiStreamSlaveType;

   signal txMaster : AxiStreamMasterType;
   signal txSlave  : AxiStreamSlaveType;

   signal appObMaster : AxiStreamMasterType;
   signal appObSlave  : AxiStreamSlaveType;

begin

   -----------------------
   -- DMA to HW ASYNC FIFO
   -----------------------
   U_DMA_to_HW : entity work.AxiStreamFifoV2
      generic map (
         -- General Configurations
         TPD_G               => TPD_G,
         INT_PIPE_STAGES_G   => 1,
         PIPE_STAGES_G       => 0,
         SLAVE_READY_EN_G    => true,
         VALID_THOLD_G       => 1,
         -- FIFO configurations
         BRAM_EN_G           => true,
         GEN_SYNC_FIFO_G     => false,
         FIFO_ADDR_WIDTH_G   => 9,
         -- AXI Stream Port Configurations
         SLAVE_AXI_CONFIG_G  => DMA_AXIS_CONFIG_C,
         MASTER_AXI_CONFIG_G => DMA_AXIS_CONFIG_C)
      port map (
         -- Slave Port
         sAxisClk    => dmaClk,
         sAxisRst    => dmaRst,
         sAxisMaster => dmaObMaster,
         sAxisSlave  => dmaObSlave,
         -- Master Port
         mAxisClk    => axilClk,
         mAxisRst    => axilRst,
         mAxisMaster => pgpIbMaster,
         mAxisSlave  => pgpIbSlave);

   -- --------------------
   -- -- AXI-Lite Crossbar
   -- --------------------
   -- U_AXIL_XBAR : entity work.AxiLiteCrossbar
      -- generic map (
         -- TPD_G              => TPD_G,
         -- NUM_SLAVE_SLOTS_G  => 1,
         -- NUM_MASTER_SLOTS_G => NUM_AXIL_MASTERS_C,
         -- MASTERS_CONFIG_G   => AXIL_CONFIG_C)
      -- port map (
         -- axiClk              => axilClk,
         -- axiClkRst           => axilRst,
         -- sAxiWriteMasters(0) => axilWriteMaster,
         -- sAxiWriteSlaves(0)  => axilWriteSlave,
         -- sAxiReadMasters(0)  => axilReadMaster,
         -- sAxiReadSlaves(0)   => axilReadSlave,
         -- mAxiWriteMasters    => axilWriteMasters,
         -- mAxiWriteSlaves     => axilWriteSlaves,
         -- mAxiReadMasters     => axilReadMasters,
         -- mAxiReadSlaves      => axilReadSlaves);

   ----------------------------------
   -- Event Builder
   ----------------------------------         
   U_EventBuilder : entity work.AxiStreamBatcherEventBuilder
      generic map (
         TPD_G         => TPD_G,
         NUM_SLAVES_G  => 2,
         AXIS_CONFIG_G => DMA_AXIS_CONFIG_C)
      port map (
         -- Clock and Reset
         axisClk         => axilClk,
         axisRst         => axilRst,
         
         -- AXI-Lite Interface (axisClk domain)
         axilReadMaster  => axilReadMaster,
         axilReadSlave   => axilReadSlave,
         axilWriteMaster => axilWriteMaster,
         axilWriteSlave  => axilWriteSlave,
         
         -- axilReadMaster  => axilReadMasters(0),
         -- axilReadSlave   => axilReadSlaves(0),
         -- axilWriteMaster => axilWriteMasters(0),
         -- axilWriteSlave  => axilWriteSlaves(0),         
         
         -- AXIS Interfaces
         sAxisMasters(0) => trigMaster,
         sAxisMasters(1) => pgpObMasters(1),
         sAxisSlaves(0)  => trigSlave,
         sAxisSlaves(1)  => pgpObSlaves(1),
         mAxisMaster     => eventMaster,
         mAxisSlave      => eventSlave);

   -------------------------------------
   -- Burst Fifo before interleaving MUX
   -------------------------------------
   U_FIFO : entity work.AxiStreamFifoV2
      generic map (
         -- General Configurations
         TPD_G               => TPD_G,
         INT_PIPE_STAGES_G   => 1,
         PIPE_STAGES_G       => 1,
         SLAVE_READY_EN_G    => true,
         VALID_THOLD_G       => 128,  -- Hold until enough to burst into the interleaving MUX
         VALID_BURST_MODE_G  => true,
         -- FIFO configurations
         BRAM_EN_G           => true,
         GEN_SYNC_FIFO_G     => true,
         FIFO_ADDR_WIDTH_G   => 9,
         -- AXI Stream Port Configurations
         SLAVE_AXI_CONFIG_G  => DMA_AXIS_CONFIG_C,
         MASTER_AXI_CONFIG_G => DMA_AXIS_CONFIG_C)
      port map (
         -- Slave Port
         sAxisClk    => axilClk,
         sAxisRst    => axilRst,
         sAxisMaster => eventMaster,
         sAxisSlave  => eventSlave,
         -- Master Port
         mAxisClk    => axilClk,
         mAxisRst    => axilRst,
         mAxisMaster => txMaster,
         mAxisSlave  => txSlave);

   -----------------
   -- AXI Stream MUX
   -----------------
   U_Mux : entity work.AxiStreamMux
      generic map (
         TPD_G                => TPD_G,
         NUM_SLAVES_G         => 4,
         ILEAVE_EN_G          => true,
         ILEAVE_ON_NOTVALID_G => false,
         ILEAVE_REARB_G       => 128,
         PIPE_STAGES_G        => 1)
      port map (
         -- Clock and reset
         axisClk         => axilClk,
         axisRst         => axilRst,
         -- Inbound Master Ports
         sAxisMasters(0) => pgpObMasters(0),
         sAxisMasters(1) => txMaster,
         sAxisMasters(2) => pgpObMasters(2),
         sAxisMasters(3) => pgpObMasters(3),
         -- Inbound Slave Ports
         sAxisSlaves(0)  => pgpObSlaves(0),
         sAxisSlaves(1)  => txSlave,
         sAxisSlaves(2)  => pgpObSlaves(2),
         sAxisSlaves(3)  => pgpObSlaves(3),
         -- Outbound Port
         mAxisMaster     => appObMaster,
         mAxisSlave      => appObSlave);

   -----------------------
   -- App to DMA ASYNC FIFO
   -----------------------
   U_APP_to_DMA : entity work.AxiStreamFifoV2
      generic map (
         -- General Configurations
         TPD_G               => TPD_G,
         INT_PIPE_STAGES_G   => 1,
         PIPE_STAGES_G       => 0,
         SLAVE_READY_EN_G    => true,
         VALID_THOLD_G       => 1,
         -- FIFO configurations
         BRAM_EN_G           => true,
         GEN_SYNC_FIFO_G     => false,
         FIFO_ADDR_WIDTH_G   => 9,
         -- AXI Stream Port Configurations
         SLAVE_AXI_CONFIG_G  => DMA_AXIS_CONFIG_C,
         MASTER_AXI_CONFIG_G => DMA_AXIS_CONFIG_C)
      port map (
         -- Slave Port
         sAxisClk    => axilClk,
         sAxisRst    => axilRst,
         sAxisMaster => appObMaster,
         sAxisSlave  => appObSlave,
         -- Master Port
         mAxisClk    => dmaClk,
         mAxisRst    => dmaRst,
         mAxisMaster => dmaIbMaster,
         mAxisSlave  => dmaIbSlave);

end mapping;
