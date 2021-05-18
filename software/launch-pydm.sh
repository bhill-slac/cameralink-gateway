#!/usr/bin/bash
#
python scripts/devGui \
	--laneConfig 0=Opal1000 1=BaslerAce \
	--startupMode False \
	--standAloneMode False \
	--enableDump  True \
	--enLclsI  True \
	--enLclsII True \
	--pgp4 True \
	--guiType PyDM 
