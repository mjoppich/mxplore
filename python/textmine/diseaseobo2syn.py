import os, sys
sys.path.insert(0, str(os.path.dirname(os.path.realpath(__file__))) + "/")

from collections import defaultdict
from mxutils.GeneOntology import GeneOntology

from mxutils.Synonym import Synonym
from mxutils.SynonymUtils import handleCommonExcludeWords
from mxutils.idutils import loadExludeWords, printToFile


if __name__ == '__main__':

    import argparse


    parser = argparse.ArgumentParser(description='Convert Medline XML to miRExplore base files')
    parser.add_argument('-o', '--obo', type=argparse.FileType("r"), required=True, help="input ontology file")
    parser.add_argument('-s', '--syn', type=argparse.FileType("w"), required=True, help="output synonym file")
    args = parser.parse_args()

    infile = args.obo # dataDir + "miRExplore/doid.obo"
    outfile = args.syn #"/mnt/d/dev/data/pmid_jun2020/synonyms/disease.syn"

    celloObo = GeneOntology(infile.name)

    ignoreTerms = set()

    ignoreTerms.add("DOID:4")
    print("Total terms:", len(celloObo.dTerms), "Ignore terms", len(ignoreTerms))


    vAllSyns = []

    for cellID in celloObo.dTerms:

        oboNode = celloObo.dTerms[cellID]

        oboID = oboNode.id
        oboName = oboNode.name

        if oboID in ignoreTerms:
            continue

        if oboNode.is_obsolete:
            print("skipping", oboName)
            continue

        oboSyns = oboNode.synonym
        oboRels = oboNode.is_a

        newSyn = Synonym(oboID)
        newSyn.addSyn(oboName)

        if oboSyns != None:
            for x in oboSyns:
                newSyn.addSyn(x.syn)

        #print(str(taxID) + " " + str(newSyn))

        vAllSyns.append(newSyn)

    globalKeywordExcludes = loadExludeWords()

    vPrintSyns = handleCommonExcludeWords(vAllSyns, None, mostCommonCount=10, maxCommonCount=5)

    printToFile(vPrintSyns, outfile.name, codec='utf8')