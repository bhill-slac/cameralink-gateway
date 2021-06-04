-------------------------------------------------------------------------------
-- File       : PgpQpll.vhd
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description:
-------------------------------------------------------------------------------
-- This file is part of 'PGP PCIe APP DEV'.
-- It is subject to the license terms in the LICENSE.txt file found in the
-- top-level directory of this distribution and at:
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
-- No part of 'PGP PCIe APP DEV', including this file,
-- may be copied, modified, propagated, or distributed except according to
-- the terms contained in the LICENSE.txt file.
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;

library surf;
use surf.StdRtlPkg.all;
use surf.AxiLitePkg.all;

library unisim;
use unisim.vcomponents.all;

entity PgpQpll is
   generic (
      TPD_G            : time            := 1 ns);
   port (
      -- QPLL Clocking
      pgpRefClk       : in  sl;
      qPllRefClk      : out slv(1 downto 0);
      qPllClk         : out slv(1 downto 0);
      qPllLock        : out slv(1 downto 0);
      qPllRefClkLost  : out slv(1 downto 0);
      gtQPllReset     : in  Slv2Array(3 downto 0);
      -- AXI-Lite Interface
      sysClk          : in  sl;
      sysRst          : in  sl;
      axilReadMaster  : in  AxiLiteReadMasterType  := AXI_LITE_READ_MASTER_INIT_C;
      axilReadSlave   : out AxiLiteReadSlaveType;
      axilWriteMaster : in  AxiLiteWriteMasterType := AXI_LITE_WRITE_MASTER_INIT_C;
      axilWriteSlave  : out AxiLiteWriteSlaveType);
end PgpQpll;


architecture mapping of PgpQpll is

   signal pllRefClk     : slv(1 downto 0);
   signal pllLockDetClk : slv(1 downto 0);
   signal pllReset      : slv(1 downto 0);
   signal qpllReset     : slv(1 downto 0);

begin

   qpllReset(0) <= gtQPllReset(0)(0) or gtQPllReset(1)(0) or gtQPllReset(2)(0) or gtQPllReset(3)(0);
   qpllReset(1) <= gtQPllReset(0)(1) or gtQPllReset(1)(1) or gtQPllReset(2)(1) or gtQPllReset(3)(1);

   pllRefClk     <= pgpRefClk & pgpRefClk;
   pllLockDetClk <= sysClk & sysClk;

   pllReset(0) <= qpllReset(0) or sysRst;
   pllReset(1) <= qpllReset(1) or sysRst;

   U_QPLL : entity surf.Gtp7QuadPll
      generic map (
         TPD_G                => TPD_G,
         -- PLL0 Configured for 3.125 Gbps
         PLL0_REFCLK_SEL_G    => "001",
         PLL0_FBDIV_IN_G      => 5,     -- 250 MHz clock reference
         PLL0_FBDIV_45_IN_G   => 5,
         PLL0_REFCLK_DIV_IN_G => 2,
         -- PLL1 Configured for 3.125 Gbps
         PLL1_REFCLK_SEL_G    => "001",
         PLL1_FBDIV_IN_G      => 5,
         PLL1_FBDIV_45_IN_G   => 5,
         PLL1_REFCLK_DIV_IN_G => 2)
      port map (
         qPllRefClk      => pllRefClk,  -- 250 MHz clock reference
         qPllOutClk      => qPllClk,
         qPllOutRefClk   => qPllRefClk,
         qPllLock        => qPllLock,
         qPllLockDetClk  => pllLockDetClk,
         qPllRefClkLost  => qPllRefClkLost,
         qPllReset       => pllReset,
         -- AXI Lite interface
         axilClk         => sysClk,
         axilRst         => sysRst,
         axilReadMaster  => axilReadMaster,
         axilReadSlave   => axilReadSlave,
         axilWriteMaster => axilWriteMaster,
         axilWriteSlave  => axilWriteSlave);

end mapping;
