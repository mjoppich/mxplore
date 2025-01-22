MAINDIR="/mnt/extproj/projekte/textmining/mxplore"

DATADIR=$MAINDIR
RESULTSDIR=$MAINDIR/mxresults/
TMDIR=$RESULTSDIR/results.pubmed/

SENTDIR=$MAINDIR/../pubmed_feb24/

MIREXPLORE_PATH=$MAINDIR/python/textmine/
ENTENTSCRIPT=$MIREXPLORE_PATH/createEntEntRelation.py
OUTPREFIX=$RESULTSDIR"/aggregated_pubmed/"

mkdir -p $OUTPREFIX

cd $MAINDIR

# CONTEXT EXTRACTION
CONTEXTSCRIPT="$MIREXPLORE_PATH/createContextInfo.py --threads 20"


CMD="python -O $CONTEXTSCRIPT --sentid-no-text --accept-pmids $OUTPREFIX/relevant_pmids.list --datadir $MAINDIR --sentdir $SENTDIR --resultdir $TMDIR/ncit/ --obo $MAINDIR/obodir/ncit.obo"
echo $CMD
$CMD > $OUTPREFIX/ncit.pmid || exit -1


SENTDIR=$MAINDIR/../pmc_feb24/
TMDIR=$RESULTSDIR/results.pmc.oa_comm/
OUTPREFIX=$RESULTSDIR"/aggregated_pmc/"


CMD="python -O $CONTEXTSCRIPT --sentid-no-text --accept-pmids $OUTPREFIX/relevant_pmids.list --datadir $MAINDIR --sentdir $SENTDIR --resultdir $TMDIR/ncit/ --obo $MAINDIR/obodir/ncit.obo"
echo $CMD
$CMD > $OUTPREFIX/ncit.pmid || exit -1

