
SAVEFOLDER="/mnt/extproj/projekte/textmining/pmc_feb24/oa_comm/orig_files/"


for LARGEFILE in `ls pmc_feb24/oa_comm/oa_comm_xml.PMC*.sent`
do

echo $LARGEFILE
python3 ./miRExplore/python/textmining/splitStructuredOutput.py --sentfile $LARGEFILE --movepath $SAVEFOLDER

done




#