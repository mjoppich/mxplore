
SAVEFOLDER="/mnt/raidexttmp/pmc_sep24/oa_bulk/oa_comm/xml/orig_files/"
mkdir -p $SAVEFOLDER

for LARGEFILE in `ls $SAVEFOLDER/../oa_comm_xml.PMC011xxxxxx*.sent`
do

echo $LARGEFILE
python3 /mnt/extproj/projekte/textmining/mxplore/python/textmine/splitStructuredOutput.py --sentfile $LARGEFILE --movepath $SAVEFOLDER

done


