import os, sys
sys.path.insert(0, str(os.path.dirname(os.path.realpath(__file__))) + "/")

from collections import defaultdict
from mxutils.GeneOntology import GeneOntology

from mxutils.Synonym import Synonym
from mxutils.SynonymUtils import handleCommonExcludeWords
from mxutils.idutils import loadExludeWords, printToFile
from mxutils.NcitTerm2Symbols import NcitTermSymbolDB



if __name__ == '__main__':

    import argparse


    parser = argparse.ArgumentParser(description='Convert Medline XML to miRExplore base files')
    parser.add_argument('-o', '--obo', type=argparse.FileType("r"), required=True, help="input ontology file")
    parser.add_argument('-n', '--ncit', type=str, required=True, help="NCIT conversion folder")
    parser.add_argument('-s', '--syn', type=argparse.FileType("w"), required=True, help="output synonym file")
    args = parser.parse_args()

    ncitObo = GeneOntology(args.obo.name)
    ncitTerm2Sym = NcitTermSymbolDB.loadFromFolder(args.ncit)

    vAllSyns = []

    print("Ignore Terms")
    ignoreTermIDs = [x.term.id for x in ncitObo["NCIT:C20189"].getAllChildren()] #Property or Attribute
    print("Ignore Terms Property or Attribute", len(ignoreTermIDs))
    ignoreTermIDs += [x.term.id for x in ncitObo["NCIT:C28428"].getAllChildren()] #Retired Concept
    print("Ignore Terms Retired Concept", len(ignoreTermIDs))
    ignoreTermIDs += [x.term.id for x in ncitObo["NCIT:C579"].getAllChildren()] #Inorganic Chemical
    print("Ignore Terms Inorganic Chemical", len(ignoreTermIDs))
    ignoreTermIDs += [x.term.id for x in ncitObo["NCIT:C20181"].getAllChildren()] #Conceptual Entity
    print("Ignore Terms Conceptual Entity", len(ignoreTermIDs))
    ignoreTermIDs = set(ignoreTermIDs)
    print("Ignore Terms", len(ignoreTermIDs))

    exclude_words_manual = {"NCIT:C63459": ["PCR"],
                            "any": ["regression", "follow-up", "randomized", "evaluated", "evaluate", "monitoring", "sensor", "targeted", "targeting", "computational", "biochemical", "statistically significant", "ability", "side effects", "pooled", "observational", "microscopy", "self-reported", "regression analysis", "laser", "biopsy", "optimization", "well-being", "wellbeing", "case report", "grade 3", "confidence interval", "ongoing", "lifestyle", "packaging", "localization", "recruitment", "calibration", "retrieval", "sequential", "follow up", "deployment", "case study", "healthcare"]}
    


    for termID in ncitObo.dTerms:

        oboNode = ncitObo.dTerms[termID]

        oboID = oboNode.id
        oboName = oboNode.name

        if oboID in ignoreTermIDs:
            continue

        oboSyns = oboNode.synonym
        oboRels = oboNode.is_a

        newSyn = Synonym(oboID)
        
        if not oboName.lower() in exclude_words_manual.get("any", []):
            newSyn.addSyn(oboName)

        if oboSyns != None:
            for x in oboSyns:
                if x.syn in exclude_words_manual.get(oboID, []) or x.syn.lower() in exclude_words_manual.get("any", []):
                    continue
                newSyn.addSyn(x.syn)


        allOrgs = [x for x in ncitTerm2Sym.org_term2symbol]

        for org in allOrgs:

            ncitID = oboID[oboID.index(":")+1:]

            if ncitID in ncitTerm2Sym.org_term2symbol[org]:

                orgSyms = ncitTerm2Sym.org_term2symbol[org][ncitID]

                for sym in orgSyms:
                    
                    if sym in exclude_words_manual.get(oboID, []) or x.syn.lower() in exclude_words_manual.get("any", []):
                        continue
                    newSyn.addSyn(sym)

        vAllSyns.append(newSyn)

    globalKeywordExcludes = loadExludeWords(disease=False, cell_co=False)

    vPrintSyns = handleCommonExcludeWords(vAllSyns, globalKeywordExcludes, mostCommonCount=100, maxCommonCount=5) #globalKeywordExcludes
    printToFile(vPrintSyns, args.syn.name, codec='utf8')


