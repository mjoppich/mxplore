import os, sys
sys.path.insert(0, str(os.path.dirname(os.path.realpath(__file__))) + "/../")

from mxutils.SynonymFile import Synfile


def normalize_gene_names(path):
    assert( not path is None )
    geneNameSynFile = Synfile(path)
    normalizeGeneNames = {}

    for sid in geneNameSynFile.mSyns:

        synonym = geneNameSynFile.mSyns[sid]

        for syn in synonym.syns:

            psyn = syn.upper()

            if psyn == sid:
                continue

            normalizeGeneNames[psyn] = sid

    return normalizeGeneNames
