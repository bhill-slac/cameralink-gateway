#!/usr/bin/bash
#	--laneConfig 0=Opal1000 1=BaslerAce \
#
python scripts/devGui \
	--laneConfig 0=Opal1000 1=BaslerAce 2=Opal1000 3=Opal1000\
	--startupMode False \
	--standAloneMode False \
	--enableDump  True \
	--enLclsI  True \
	--enLclsII True \
	--pgp4 True \
	--guiType PyDM 
