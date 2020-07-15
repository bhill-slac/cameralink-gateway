#!/usr/bin/bash
python scripts/devGui \
	--camType Opal1000 \
	--defaultFile config/Opal1000.yml \
	--startupMode False \
	--standAloneMode False \
	--guiType PyDM &
