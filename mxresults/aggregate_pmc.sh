MAINDIR=$(dirname "$0/../")

DATADIR=$MAINDIR
RESULTSDIR=$MAINDIR/mxresults/
TMDIR=$RESULTSDIR/results.pmc.oa_comm/
OUTPREFIX=$RESULTSDIR"/aggregated_pmc/"

SENTDIR=/mnt/extproj/projekte/textmining/pmc_feb24/oa_comm/
EN_CORE_SCI_LG="/mnt/extproj/projekte/textmining/spacy_models/en_core_sci_lg-0.2.4/en_core_sci_lg/en_core_sci_lg-0.2.4"
EN_NER_BIONLP13="/mnt/extproj/projekte/textmining/spacy_models/en_ner_bionlp13cg_md-0.2.4/en_ner_bionlp13cg_md/en_ner_bionlp13cg_md-0.2.4"

MODEL_ARGS="--threads 20 --nlp ${EN_CORE_SCI_LG} --nlpent ${EN_NER_BIONLP13}"

MIREXPLORE_PATH=$MAINDIR/python/textmine/
ENTENTSCRIPT=$MIREXPLORE_PATH/createEntEntRelation.py

mkdir -p $OUTPREFIX

cd $MAINDIR

# nohup bash aggregate_pmc.sh > nohup_pmc_aggregate &

# RELATION EXTRACTION
CMD="python -O $ENTENTSCRIPT --sentid-no-text --sent-no-byte --datadir $DATADIR --sentdir $SENTDIR --resultdir $TMDIR -f1 mirna -f2 mgi  -ft1 mirna -ft2 gene --same-sentence $MODEL_ARGS"
echo $CMD
$CMD > $OUTPREFIX"mirna_gene.mmu.pmid" 2> $OUTPREFIX"mirna_gene.mmu.err" || exit -1

CMD="python -O $ENTENTSCRIPT --sentid-no-text --sent-no-byte --datadir $DATADIR --sentdir $SENTDIR --resultdir $TMDIR -f1 mirna -f2 hgnc -ft1 mirna -ft2 gene --same-sentence $MODEL_ARGS"
echo $CMD
$CMD > $OUTPREFIX"mirna_gene.hsa.pmid" 2> $OUTPREFIX"mirna_gene.hsa.err" || exit -1


# SUBSET CONTEXT ONLY FOR RELEVANT ARTICLES
cat $OUTPREFIX/mirna_gene.mmu.pmid $OUTPREFIX/mirna_gene.hsa.pmid | cut -f 7 | sort | uniq > $OUTPREFIX/relevant_pmids.list
echo "Found Documents"
wc -l $OUTPREFIX/relevant_pmids.list

# CONTEXT EXTRACTION
CONTEXTSCRIPT="$MIREXPLORE_PATH/relation_extraction/createContextInfo.py --threads 20"

CMD="python -O $CONTEXTSCRIPT --sentid-no-text --accept-pmids $OUTPREFIX/relevant_pmids.list --datadir $MAINDIR --sentdir $SENTDIR --resultdir $TMDIR/disease/ --obo $MAINDIR/obodir/doid.obo"
echo $CMD
$CMD > $OUTPREFIX/disease.pmid || exit -1

CMD="python -O $CONTEXTSCRIPT --sentid-no-text --accept-pmids $OUTPREFIX/relevant_pmids.list --datadir $MAINDIR --sentdir $SENTDIR --resultdir $TMDIR/cellline/ --obo $MAINDIR/obodir/cell_ontology.obo"
echo $CMD
$CMD > $OUTPREFIX/celllines.pmid || exit -1

CMD="python -O $CONTEXTSCRIPT --sentid-no-text --accept-pmids $OUTPREFIX/relevant_pmids.list --datadir $MAINDIR --sentdir $SENTDIR --resultdir $TMDIR/go/ --obo $MAINDIR/obodir/go.obo"
echo $CMD
$CMD > $OUTPREFIX/go.pmid || exit -1

CMD="python -O $CONTEXTSCRIPT --sentid-no-text --accept-pmids $OUTPREFIX/relevant_pmids.list --datadir $MAINDIR --sentdir $SENTDIR --resultdir $TMDIR/model_anatomy/ --obo $MAINDIR/obodir/model_anatomy.obo"
echo $CMD
$CMD > $OUTPREFIX/model_anatomy.pmid || exit -1

CMD="python -O $CONTEXTSCRIPT --sentid-no-text --accept-pmids $OUTPREFIX/relevant_pmids.list --datadir $MAINDIR --sentdir $SENTDIR --resultdir $TMDIR/org/ --obo $MAINDIR/obodir/organism.obo"
echo $CMD
$CMD > $OUTPREFIX/organism.pmid || exit -1

CMD="python -O $CONTEXTSCRIPT --sentid-no-text --accept-pmids $OUTPREFIX/relevant_pmids.list --datadir $MAINDIR --sentdir $SENTDIR --resultdir $TMDIR/ncit/ --obo $MAINDIR/obodir/ncit.obo"
echo $CMD
$CMD > $OUTPREFIX/ncit.pmid || exit -1