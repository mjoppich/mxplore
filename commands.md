

# Prepare environment

Prepare the environment and set paths as required.

    conda activate mirexplore

    export JAVA_HOME=/mnt/extproj/projekte/textmining/jdk/openlogic-openjdk-11.0.22+7-linux-x64

    export MXPLORE_PATH=/mnt/extproj/projekte/textmining/miRExplore/python/
    export MIREXPLORE_RESULTS=/mnt/extproj/projekte/textmining/mxresults/

    mkdir -p obodir
    mkdir -p synonyms
    mkdir -p $MIREXPLORE_RESULTS

## Data to be provided to the user
- ncit_conversion_folder
- obodir/aliases.txt
- obodir/miRNA.xls
- obodir/allrels.csv
- excludes
- synonyms/organism.syn
- aggregate_pmc.sh
- aggregate_pubmed.sh

# Downloading code

    #git clone git@github.com:mjoppich/nameConvert.git
    git clone git@github.com:mjoppich/miRExplore.git


# Downloading spacy models


    wget https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.2.5/en_core_sci_lg-0.2.5.tar.gz
    wget https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.2.5/en_ner_bionlp13cg_md-0.2.5.tar.gz

    wget https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.2.4/en_core_sci_lg-0.2.4.tar.gz
    wget https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.2.4/en_ner_bionlp13cg_md-0.2.4.tar.gz

# Download Pubmed and PMC

Download all PubMed Abstracts via this call:

    nohup /mnt/biosoft/software/python/3.11/mypy miRExplore/python/textmining/downloadPubmedAbstracts.py > nohup_pubmed_ftp &

And download PMC via FileZilla from: https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_bulk/

# Process XML files

## PubMed


    nohup python $MXPLORE_PATH/python/medlineXMLtoStructure.py --base pubmed24n --xml-path /mnt/extproj/projekte/textmining/pubmed_feb24/ --threads 16 --model spacy_models/en_ner_bionlp13cg_md-0.2.4/en_ner_bionlp13cg_md/en_ner_bionlp13cg_md-0.2.4 &> nohup_pubmed_extract &

## PMC

    nohup python $MXPLORE_PATH/python/medlineXMLtoStructurePMCtar.py --base oa_comm --xml-path pmc_feb24/oa_comm/ --threads 16 --model spacy_models/en_ner_bionlp13cg_md-0.2.4/en_ner_bionlp13cg_md/en_ner_bionlp13cg_md-0.2.4 &> nohup_pmc_extract &

### Splitting Chunks

It might be useful to split large PMC sentence files into smaller chunks. After adapting paths in the script, run:

    nohup bash chunk_pmc_files.sh > nohup_pmc_chunk &


# Prepare synonym lists

## miRNAs

Beware! The original files are not anymore available from mirbase! These are provided in the Zenodo archive!

    #wget -O obodir/aliases.txt.zip https://mirbase.org/ftp/CURRENT/aliases.txt.zip
    #wget -O obodir/miRNA.xls.zip https://mirbase.org/ftp/CURRENT/miRNA.xls.zip

    #unzip obodir/aliases.txt.zip
    #unzip obodir/miRNA.xls.zip

    python $MXPLORE_PATH/python/textmine/mirbase2syn.py --mirna-xls obodir/miRNA.xls --mirna-alias obodir/aliases.txt --syn synonyms/mirbase.hsa_mmu.syn


## Mouse gene symbols

    wget -O obodir/mouse_genes.rpt http://www.informatics.jax.org/downloads/reports/MRK_Sequence.rpt

    python $MXPLORE_PATH/python/textmine/mgi2syn.py --rpt obodir/mouse_genes.rpt --syn synonyms/mgi.syn

## Human gene symbols

    wget -O obodir/hgnc.tsv "https://www.genenames.org/cgi-bin/download/custom?col=gd_hgnc_id&col=gd_app_sym&col=gd_app_name&col=gd_status&col=gd_prev_sym&col=gd_aliases&col=gd_pub_chrom_map&col=gd_pub_acc_ids&col=gd_pub_refseq_ids&col=gd_name_aliases&col=gd_prev_name&status=Approved&status=Entry%20Withdrawn&hgnc_dbtag=on&order_by=gd_prev_sym&format=text&submit=submit"

    python $MXPLORE_PATH/python/textmine/hgnc2syn.py --tsv obodir/hgnc.tsv --syn synonyms/hgnc.syn

## Prepare disease ontology synonyms

The DOID can be downloaded from https://github.com/DiseaseOntology/HumanDiseaseOntology/tree/main/src/ontology .

    wget -O obodir/doid.obo https://raw.githubusercontent.com/DiseaseOntology/HumanDiseaseOntology/main/src/ontology/HumanDO.obo

    python $MXPLORE_PATH/python/textmine/diseaseobo2syn.py --obo obodir/doid.obo --syn synonyms/disease.syn

## Prepare NCIT

The NCIT obo can be downloaded from https://obofoundry.org/ontology/ncit#:~:text=NCI%20Thesaurus%20%28NCIt%29is%20a%20reference%20terminology%20that%20includes,NCIt%20OBO%20Edition%20releases%20should%20be%20considered%20experimental. 

    wget -O obodir/ncit.obo http://purl.obolibrary.org/obo/ncit.obo

    python $MXPLORE_PATH/python/textmine/ncit2syn.py --obo obodir/ncit.obo --syn synonyms/ncit.syn --ncit ./ncit_conversion_folder/


## Prepare GO

The GO obo can be downloaded from https://obofoundry.org/ontology/go.html .
Here we use, in order to avoid too many overlapping terms, the basic GO version.

    wget -O obodir/go.obo http://purl.obolibrary.org/obo/go/go-basic.obo

    python $MXPLORE_PATH/python/textmine/gobo2syn.py --obo obodir/go.obo --syn synonyms/


## Prepare Model Anatomy

The, integrated cross-species ontology covering anatomical structures in animals, uberon ontology is available from https://obofoundry.org/ontology/uberon.html . The basic edition excludes external ontologies and most relations.

    wget -O obodir/model_anatomy.obo http://purl.obolibrary.org/obo/uberon/basic.obo

    python $MXPLORE_PATH/python/textmine/modelanatomy2syn.py --obo obodir/model_anatomy.obo --syn synonyms/model_anatomy.syn

## Prepare Cell Ontology

    wget -O obodir/cell_ontology.obo http://purl.obolibrary.org/obo/cl/cl-basic.obo

    python $MXPLORE_PATH/python/textmine/cells2syn.py --obo obodir/cell_ontology.obo --syn synonyms/cell_ontology.syn



# Performing text mining

## Brief check

If you call this script, you should receive hits for all genes, and distinguish also the -AS and non-AS isoforms!

    python ./miRExplore/python/textmine/textmineDocument.py --only-longest-match --test-is-word --threads 1 --submatch-exclude ./excludes/gene_excludes.syn -s ./synonyms/hgnc.syn -i python/textmine/testdata/tm_test_file -o ./ -nocells -tl 5 -prunelevel none -e excludes/all_excludes.syn

## Starting Textmining

Within the startTextmining.sh script call doTextmine.sh for each folder (pubmed/pmc) separately!

    bash startTextmining.sh


## QC: you may want to check for highly mentioned synonyms ...

For examples, to identify highly mentioned synonyms in the ncit text mining results run:

    python $MXPLORE_PATH/python/textmine/identifyHighlyMentionedSynonyms.py --index ./mxresults/results.pubmed/ncit/pubmed24n122*


# Relation extraction

In order to perform relation extraction call the following to scripts

    nohup bash $MIREXPLORE_RESULTS/aggregate_pmc.sh > $MIREXPLORE_RESULTS/nohup_pmc_aggregate &
    nohup bash $MIREXPLORE_RESULTS/aggregate_pubmed.sh > $MIREXPLORE_RESULTS/nohup_pubmed_aggregate &



# Database creation

Execute the notebooks in $MXPLORE_PATH$/python/postproc/ in the following order:

## Preprocess data into parquet data frames

### Creating the interaction parquet file

    create_interaction_df.ipynb

### create the consensus parquet file

    create_interaction_consensus.ipynb

### create annotation parquet file

    create_annotation_df.ipynb

### create sentence and date parquet file

    create_date_df.ipynb
    create_sentence_df.ipynb


## Create the sqlite database

    create_sqlite_databases.ipynb
    

# Benchmark

In order to run the Bagewadi et al. benchmark, use the scripts in the scai_eval folder.

Run

    TestClassifications.ipynb

to get global results.

The notebook

    AllScaiComparisons.ipynb

generates results using all combinations of the various rules and delivers finegrained results, which can be visualized using

    eval_check.ipynb

