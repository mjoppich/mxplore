import os, sys
sys.path.insert(0, str(os.path.dirname(os.path.realpath(__file__))) + "/")

from collections import defaultdict
from mxutils.GeneOntology import GeneOntology

from mxutils.Synonym import Synonym
from mxutils.SynonymUtils import handleCommonExcludeWords
from mxutils.idutils import loadExludeWords, printToFile


import argparse


if __name__ == '__main__':



    parser = argparse.ArgumentParser(description='Convert Medline XML to miRExplore base files')
    parser.add_argument('-o', '--obo', type=argparse.FileType("r"), required=True, help="input ontology file")
    parser.add_argument('-s', '--syn', type=argparse.FileType("w"), required=True, help="output synonym file")
    args = parser.parse_args()

    bodypartsObo = GeneOntology(args.obo.name)
    vAllSyns = []

    for cellID in bodypartsObo.dTerms:

        oboNode = bodypartsObo.dTerms[cellID]

        oboID = oboNode.id
        oboName = oboNode.name

        oboSyns = oboNode.synonym
        oboRels = oboNode.is_a

        newSyn = Synonym(oboID)
        newSyn.addSyn(oboName)


        aName = oboName.split(' ')

        if len(aName) > 1 and len(aName) < 5:

            acro = ""
            if aName[-1].upper() == 'CELL':
                acro = "".join([x[0].upper() for x in aName])

            newSyn.addSyn(acro)

        if oboSyns != None:
            for x in oboSyns:
                newSyn.addSyn(x.syn)

        #print(str(taxID) + " " + str(newSyn))

        vAllSyns.append(newSyn)

    globalKeywordExcludes = loadExludeWords(cell_co=False)

    vPrintSyns = handleCommonExcludeWords(vAllSyns, globalKeywordExcludes, mostCommonCount=200, maxCommonCount=5)
    printToFile(vPrintSyns, args.syn.name)