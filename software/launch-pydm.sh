#!/usr/bin/bash
#
python scripts/devGui \
	--camType Opal1000 BaslerAce Opal1000 Opal1000\
	--defaultFile config/Opal1000.yml \
	--startupMode False \
	--standAloneMode False \
	--enableDump  True \
	--enLclsI  True \
	--enLclsII True \
	--pgp4 True \
	--guiType PyDM 
