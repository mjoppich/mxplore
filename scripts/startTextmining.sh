#!/usr/bin/sh

BASEFOLDER=$(dirname "$0")
MIREXPLORE_PATH=$BASEFOLDER/../python/



bash $BASEFOLDER/doTextmine.sh "python $MIREXPLORE_PATH/textmine/textmineDocument.py --test-is-word --only-longest-match --threads 20" "$BASEFOLDER/pubmed_feb24/" "./mx_feb24/results.pubmed/" "$BASEFOLDER"
bash $BASEFOLDER/doTextmine.sh "python $MIREXPLORE_PATH/textmine/textmineDocument.py --test-is-word --only-longest-match  --threads 20" "$BASEFOLDER/pmc_feb24/oa_comm/" "./mx_feb24/results.pmc.oa_comm/" "$BASEFOLDER"