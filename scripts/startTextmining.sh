#!/usr/bin/sh

BASEFOLDER=$(dirname "$0")
MIREXPLORE_PATH=$BASEFOLDER/../python/

echo $BASEFOLDER

PUBMEDPATH=/mnt/extproj/projekte/textmining/pubmed_feb24/
PMCPATH=/mnt/extproj/projekte/textmining/pmc_feb24/oa_comm/

bash $BASEFOLDER/doTextmine.sh "python $MIREXPLORE_PATH/textmine/textmineDocument.py --test-is-word --only-longest-match --threads 20" "$PUBMEDPATH" "./mxresults/results.pubmed/" "$BASEFOLDER/../"

bash $BASEFOLDER/doTextmine.sh "python $MIREXPLORE_PATH/textmine/textmineDocument.py --test-is-word --only-longest-match  --threads 20" "$PMCPATH" "./mxresults/results.pmc.oa_comm/" "$BASEFOLDER/../"