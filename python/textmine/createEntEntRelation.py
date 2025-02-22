import argparse

import sys

import glob
import os

import spacy
import scispacy
import string

sys.path.insert(0, str(os.path.dirname(os.path.realpath(__file__))) + "/./")


from collections import Counter, defaultdict
import re

from mxutils.SynfileMap import SynfileMap, SynonymID
from mxutils.SynonymFile import Synfile, AssocSynfile
from mxutils.mirnaID import miRNA, miRNAPART
from mxutils.SentenceDB import SentenceDB, RegPos
from mxutils.SyngrepHitFile import SyngrepHitFile
import copy

import pyparsing as pp
from mxutils.MirGeneRelCheck import SentenceRelationChecker, SentenceRelationClassifier

from mxutils.parallel import MapReduce
from enum import Enum
from intervaltree import Interval, IntervalTree

#nlp = spacy.load('/mnt/d/spacy/models/en_core_web_lg-2.2.0/en_core_web_lg/en_core_web_lg-2.2.0/')  # create blank Language class #en_core_web_lg


def augmentMiRNAs(sentence, y, entSyns):
    # get sentence from position to next blank

    if type(sentence.text) == bytes:
        nextWord = sentence.text.find(b" ", y.position[1])
    else:
        nextWord = sentence.text.find(" ", y.position[1])

    allY = [y]

    if nextWord > y.position[1]:

        newMirna = []

        if type(sentence.text) == bytes:

            textForSent = sentence.text#.encode("utf-8")
            foundText = textForSent[y.position[0]:nextWord].decode(errors="replace")
            addText = textForSent[y.position[1]:nextWord].decode(errors="replace")
        
        else:
            textForSent = sentence.text
            foundText = textForSent[y.position[0]:nextWord]
            addText = textForSent[y.position[1]:nextWord]

        if len(addText) > 1 and not foundText in [",", ";", "-"] and foundText.startswith("miR"):

            ppResMir = []

            try:

                mirnapp = "miR-" + pp.Group(pp.Combine(pp.Word(pp.nums)).setResultsName("mirnum") + pp.Optional(
                    pp.Word(pp.alphas, max=1)).setResultsName("var") + pp.Optional(
                    "-" + pp.Combine(pp.Word(pp.nums, max=1)).setResultsName("prec") + pp.FollowedBy(
                        pp.Or(["-", "/"]))) + pp.Optional(pp.Or(["-3p", "-5p"])).setResultsName("mod"))
                mirnapp += pp.ZeroOrMore(
                    pp.Group(
                        pp.Combine("/" + pp.Optional("-")) + pp.Combine(pp.Optional(pp.Word(pp.nums))).setResultsName(
                            "mirnum") +
                        pp.Combine(pp.Optional(pp.Word(pp.srange("[a-z]"), max=1))).setResultsName("var") +
                        pp.Optional("-" + pp.Combine(pp.Word(pp.nums, max=1)).setResultsName("prec") + pp.FollowedBy(
                            pp.Or(["-", "/"]))) +
                        pp.Optional(pp.Or(["-3p", "-5p"])).setResultsName("mod")
                    )
                )
                mirnapp += pp.StringEnd()

                ppRes = mirnapp.parseString(foundText, parseAll=True)


                for ppr in ppRes:
                    if type(ppr) == pp.ParseResults:
                        ppResMir.append(ppr)

            except pp.ParseException as e:
                pass

            if len(ppResMir) > 1:

                ppMirNum = None
                ppMirVar = ""
                ppMirMod = ""
                for pi, ppr in enumerate(ppResMir):

                    if ppr.get("mirnum", None) == None and ppr.get("var", None) == None and ppr.get("prec", None) == None and ppr.get("mod", None) == None:
                        continue

                    if len(ppr.get("mirnum", "")) == 0 and len(ppr.get("var", "")) == 0 and len(ppr.get("prec", "")) == 0 and len(ppr.get("mod", "")) == 0:
                        continue

                    ppMirNumTmp = ppr.get("mirnum", None)

                    if ppMirNumTmp != None and len(ppMirNumTmp) > 0:
                        ppMirNum = ppMirNumTmp

                    ppMirVar = ppr.get("var", "")
                    ppMirMod = ppr.get("mod", "")
                    ppMirPrec = ppr.get("prec", "")

                    if ppMirNum == None:
                        continue

                    #print(ppr, ppr.get("mirnum", "--"), ppr.get("var", "--"), ppr.get("prec", "--"), ppr.get("mod", '--'))

                    newMIRNA = "miR-{}{}{}".format(ppMirNum, ppMirVar, ppMirMod)

                    miObj = miRNA.parseFromComponents(mature="miR", mirid=ppMirNum, prec=ppMirVar, mseq=ppMirPrec, arm=ppMirMod)

                    #print(newMIRNA,miObj)

                    accSyns = []

                    for synFileID in entSyns.loadedSynFiles:
                        synFile = entSyns.loadedSynFiles[synFileID]
                        for sidx, syn in enumerate(synFile.mSyns):

                            synObj = synFile.mSyns[syn]

                            if synObj.match(newMIRNA):
                                accSyns.append((synFileID, synObj, sidx))


                    for (synFileID, accSyn, sidx) in accSyns:
                        ynew = copy.deepcopy(y)
                        ynew.hitSyn = newMIRNA
                        ynew.foundSyn = newMIRNA

                        ynew.position = (ynew.position[0], nextWord)
                        ynew.synonym = accSyn

                        newSynID = SynonymID()
                        newSynID.synfile = synFileID
                        newSynID.synid = sidx

                        ynew.synonymID = newSynID

                        hmirna = handleHarmonizedNameMirna(ynew)

                        if hmirna == None:
                            continue

                        newMirna.append(ynew)

        if len(newMirna) > 1:
            allY = newMirna

    return allY

class Cooccurrence:

    def __init__(self):
        self.pubmed = None

        self.ent1 = None
        self.ent2 = None
        self.ent1type = None
        self.ent2type = None
        self.ent1found = None
        self.ent2found = None

        self.sameSentence = False
        self.sameParagraph = False
        self.relation = None
        self.mirnaFound = None

    def __str__(self):
        return "{pub}\t{type}\t{ent1}\t{ent2}\t{ent1type}\t{ent2type}".format(pub=self.pubmed, ent1=self.ent1, ent2=self.ent2, ent1type=self.ent1type, ent2type=self.ent2type)

    def __repr__(self):
        return self.__str__()

    def getIdTuple(self):
        return (self.gene, self.mirna)



def findAssocs(assocs, text, textLoc):
    res = []
    for word in assocs:

        allowedAssocPos = assocs[word]

        if False and not textLoc in allowedAssocPos:
            continue

        if word in text:
            res.append((word, textLoc))

    return res


def getStack(t):
    h = t
    stack = []
    while h != None:
        stack.append( (h, h.dep_, h.pos_) )

        h = h.head if h != h.head else None

    return stack

def getAllChildren(gen):

    allBase = [x for x in gen]
    allElems = []

    for x in allBase:

        allElems += getAllChildren(x.children)

    return allBase + allElems


class EntEntRelation:

    def __init__(self, relRes, ent1, ent2, sentence):
        
        self.interaction_direction = None
        self.regulation_direction = None

        self.accepted_relation = None
        self.accepted_relation_num = 0

        self.ent1 = ent1
        self.ent2 = ent2
        self.sentence_id = sentence

        self.same_paragraph = True
        self.same_sentence = True

        self.passive = False
        self.negated = False

        self.check_sdp = False
        self.check_conj = False

        self.rel_positon = (0,0)

        self._parse_relres(relRes)

    def _parse_relres(self, relRes):

        self.accepted_relation = relRes["accept_relation"]
        self.accepted_relation_num = 1 if self.accepted_relation else 0

        self.check_sdp = relRes["check_results"]["sdp"]
        self.check_conj = relRes["check_results"]["conj"]

        self.interaction_direction = relRes["check_results"]["classification"]["interaction_dir"]
        self.regulation_direction = relRes["check_results"]["classification"]["regulation_dir"]

        self.assocDir = "1V2" if self.interaction_direction == "GENE_MIR" else "2V1"

        self.passive = relRes["check_results"]["passive"]
        self.negated = relRes["check_results"]["negation"]

    def accepted(self):
        return self.accepted_relation_num == 1


    def _get_relation_tuple(self):
        
        return (
            self.assocDir.replace("V", ""),
            self.assocDir,
            self.regulation_direction,
            "", # reg stem
            str(self.sentence_id),
            False, # ??
            self.ent1.position,
            self.ent2.position,
            self.rel_positon,
            'spacy',
            self.accepted_relation_num,
            self.accepted_relation_num,
            0, # conj
            0, #??
            self.check_sdp,
            self.passive,
            self.negated,
            self.interaction_direction,
            self.regulation_direction
        )   

        
    def __str__(self):

        hitSyn1 = self.ent1.hitSyn
        hitSyn2 = self.ent2.hitSyn

        if self.ent1.synType == "MIRNA":
            hitSyn1 = handleHarmonizedNameMirna(self.ent1)

        if self.ent2.synType == "MIRNA":
            hitSyn2 = handleHarmonizedNameMirna(self.ent2)

        return "\t".join(
            [ str(x) for x in 
                [
                    self.ent1.synonym.id, hitSyn1, self.ent1.synType,
                    self.ent2.synonym.id, hitSyn2, self.ent2.synType,

                    self.sentence_id.docID,
                    self.same_paragraph, self.same_sentence,
                    [ self._get_relation_tuple() ]
                ]
            ]
        )



def findRelationBySyns(ent1Hit, ent2Hit, sentence, relHits, ent1Type, ent2Type):

    sentText = sentence.text

    e1Loc = ent1Hit.position
    e2Loc = ent2Hit.position

    if ent1Hit.foundSyn == "Th1":
        print(ent1Hit.documentID, ent1Hit.originalLine, file=sys.stderr)
        print(ent1Hit.documentID, sentence, file=sys.stderr)

    if ent2Hit.foundSyn == "Th1":
        print(ent2Hit.documentID, ent2Hit.originalLine, file=sys.stderr)
        print(ent2Hit.documentID, sentence, file=sys.stderr)

    relRes = relChecker.check_sentence(sentText
                                    , {"entity_type": ent1Type, "entity_type_token": "e1", "entity_location": e1Loc} #mirna
                                    , {"entity_type": ent2Type, "entity_type_token": "e2", "entity_location": e2Loc} #gene
                                    , fix_special_chars=False
                                    , relClassifier=relClassifier.classify
                                    )

    ententRel = EntEntRelation(relRes, ent1Hit, ent2Hit, sentence.id)

    return [ ententRel ]



def handleHarmonizedNameMirna(x):
    idx = x.synonym.syns.index(x.hitSyn)

    if idx >= 0:

        try:
            test = miRNA(x.synonym.syns[idx])
            outstr = test.getStringFromParts(
                [miRNAPART.ORGANISM, miRNAPART.MATURE, miRNAPART.ID, miRNAPART.PRECURSOR,
                 miRNAPART.MATURE_SEQS,
                 miRNAPART.ARM], normalized=True)

            return outstr

        except:

            # sys.stderr.write("cannot parse mirna: " + x.synonym.syns[idx])

            if __debug__:
                pass
                # miRNA(x.synonym.syns[idx])
                # exit(-1)

    for mirnaSyn in x.synonym.syns:

        if mirnaSyn.startswith("miR-") and not 'mediated' in mirnaSyn:
            test = miRNA(mirnaSyn)
            outstr = test.getStringFromParts(
                [miRNAPART.ORGANISM, miRNAPART.MATURE, miRNAPART.ID, miRNAPART.PRECURSOR,
                 miRNAPART.MATURE_SEQS, miRNAPART.ARM], normalized=True)

            return outstr

    if __debug__:
        print("Could not match", x.hitSyn)
    return None

def findCooccurrences(pubmed, ent1Hits, ent2Hits, sentDB, relHits):
    def checkSynHit(synhit):
        if len(synhit.foundSyn) <= 5 and len(synhit.foundSyn) > 1:
            
            prefixPart = str(synhit.prefix).strip(string.whitespace + "()[],;.")
            suffixPart = str(synhit.suffix).strip(string.whitespace + "()[],;.")

            if len(prefixPart) > 0:
                return False
            if len(suffixPart) > 0:
                return False
            
            return synhit.perfectHit == True

        return True

    def chekSynHitMirna(synhit):

        if synhit.prefix.endswith("-") and len(synhit.prefix) == 4:
            if not synhit.prefix.lower() in ["mmu", "hsa"]:
                return False

        if len(synhit.foundSyn) <= 5:
            foundSyn = synhit.foundSyn.lower()           
            return foundSyn.startswith('mir') or foundSyn.startswith('micro') or foundSyn.startswith('let')

        return True


    setAllEnt1 = set()
    if args.folderType1.upper() == 'MIRNA':
        setAllEnt1 = set([x for x in ent1Hits if chekSynHitMirna(x)])

        allAugmentEnts = []
        for entHit in setAllEnt1:
            sentence = sentDB.get_sentence(entHit.documentID)
            allY = augmentMiRNAs(sentence, entHit, ent1Syns)
            allAugmentEnts += allY

        ent1Hits = allAugmentEnts
        setAllEnt1 = allAugmentEnts
    else:
        setAllEnt1 = set([x for x in ent1Hits if checkSynHit(x)])

    setAllEnt2 = set()
    if args.folderType2.upper() == 'MIRNA':
        setAllEnt2 = set([x for x in ent2Hits if chekSynHitMirna(x)])

        allAugmentEnts = []
        for entHit in setAllEnt2:
            sentence = sentDB.get_sentence(entHit.documentID)
            allY = augmentMiRNAs(sentence, entHit, ent2Syns)

            allAugmentEnts += allY

        

        ent2Hits = allAugmentEnts
        setAllEnt2 = allAugmentEnts


    else:
        setAllEnt2 = set([x for x in ent2Hits if checkSynHit(x)])


    ent1BySent = defaultdict(list)
    ent2BySent = defaultdict(list)

    ent1ToSent = {}
    ent2ToSent = {}

    for hit in ent1Hits:
        parSenID = (hit.documentID.parID, hit.documentID.senID)
        ent1BySent[parSenID].append(hit)
        ent1ToSent[hit] = parSenID

    for hit in ent2Hits:
        parSenID = (hit.documentID.parID, hit.documentID.senID)
        ent2BySent[parSenID].append(hit)
        ent2ToSent[hit] = parSenID

    allCoocs = []

    pmidRels = relHits.getHitsForDocument(pubmed)

    pmidRelBySent = defaultdict(list)


    if pmidRels != None:
        for rel in pmidRels:
            pmidRelBySent[str(rel.documentID)].append(rel)

    ftype1 = args.folderType1.upper()
    ftype2 = args.folderType2.upper()
    
    #print(rel)
    #print(setAllEnt1)
    #print(setAllEnt2)


    for x in setAllEnt1:
        for y in setAllEnt2:

            if args.same_sentence and not x.documentID == y.documentID:
                continue

            if x.synonym.id == y.synonym.id:
                continue

            if x.position == y.position:
                continue

            if x.hitSyn == y.hitSyn:
                continue

            x.synType = ftype1
            y.synType = ftype2

            ent1Loc = ent1ToSent[x]
            ent2Loc = ent2ToSent[y]

            # TODO is this not equal to some value of x?
            if ent1Loc[0] == ent2Loc[0]:
                #foundCooc.sameParagraph = True

                if ent1Loc[1] == ent2Loc[1]:
                    #foundCooc.sameSentence = True

                    yStartsInX = x.position[0] <= y.position[0] and y.position[0] <= x.position[1]
                    xStartsInY = y.position[0] <= x.position[0] and x.position[0] <= y.position[1]

                    if xStartsInY or yStartsInX:
                        print("Overlapping gene/mirna hit", file=sys.stderr)
                        print(x.originalLine, x.position, x.synType, file=sys.stderr)
                        print(y.originalLine, y.position, y.synType, file=sys.stderr)
                        continue

                    sentence = sentDB.get_sentence(x.documentID)
                    
                    if len(sentence.text) > 500:
                        continue
                    
                    if sentence.text.startswith("Table "):
                        continue
                    if sentence.text.startswith("Figure "):
                        continue
                    if sentence.text.startswith("Tab. "):
                        continue
                    if sentence.text.startswith("Fig. "):
                        continue
                    
                    relations = findRelationBySyns(x, y, sentence, pmidRelBySent, ftype1.lower(), ftype2.lower())

                    allCoocs += relations

    return allCoocs





def analyseFile(splitFileIDs, env):

    fileCoocs = []

    for splitFileID in splitFileIDs:

        print(splitFileID, file=sys.stderr)

        ent1File = resultBase + "/"+args.folder1+"/" + splitFileID + ".index"
        ent2File = resultBase + "/"+args.folder2+"/" + splitFileID + ".index"
        relFile = resultBase + "/relations/" + splitFileID + ".index"

        sentFile = args.sentdir + "/" + splitFileID + ".sent"

        ent1Hits = SyngrepHitFile(ent1File, ent1Syns, sentIDNoText=args.sentid_no_text)
        if len(ent1Hits) == 0:
            continue

        ent2Hits = SyngrepHitFile(ent2File, ent2Syns, sentIDNoText=args.sentid_no_text)
        if len(ent2Hits) == 0:
            continue

        relHits = SyngrepHitFile(relFile, relSyns, sentIDNoText=args.sentid_no_text)

        # only load sentences if there's a hit ...
        sentDB = None

        print("Found something in: " + str(splitFileID), file=sys.stderr, flush=True)

        for docID in ent1Hits:

            #if not docID in ["27150436"]:
            #    continue

            if accept_pmids != None:
                if not docID in accept_pmids:
                    continue

            if docID in ent2Hits:

                if sentDB == None:
                    sentDB = SentenceDB(sentFile, sent_no_byte=args.sent_no_byte)

                ent1SynHits = ent1Hits.getHitsForDocument(docID)
                ent2SynHits = ent2Hits.getHitsForDocument(docID)

                # if docID == 'a27229723':
                #    [print(x.synonyme) for x in hgncSynHits]
                #    [print(x.synonyme) for x in mirnaSynHits]

                ent1HitsPerSentence = Counter()
                ent2HitsPerSentence = Counter()

                for x in ent1SynHits:
                    ent1HitsPerSentence[x.documentID] += 1
                for x in ent2SynHits:
                    ent2HitsPerSentence[x.documentID] += 1

                removeSentences = set()
                for x in ent1HitsPerSentence:
                    if ent1HitsPerSentence[x] > args.max_finds_per_sentence:
                        removeSentences.add(x)
                for x in ent2HitsPerSentence:
                    if ent2HitsPerSentence[x] > args.max_finds_per_sentence:
                        removeSentences.add(x)

                if len(removeSentences) > 0:
                    for x in removeSentences:
                        print("Removing sentence", x, "with entity counts:", ent1HitsPerSentence[x], ent2HitsPerSentence[x], file=sys.stderr)

                        ent1SynHits = [x for x in ent1SynHits if not x.documentID in removeSentences]
                        ent2SynHits = [x for x in ent2SynHits if not x.documentID in removeSentences]

                foundCoocs = findCooccurrences(str(docID), ent1SynHits, ent2SynHits, sentDB, relHits)

                for relEntEnt in foundCoocs:
                    if relEntEnt.accepted():
                        print(str(relEntEnt), flush=True)
                    
                    """
                    print(
                        "{ent1}\t{ent1found}\t{ent1type}\t{ent2}\t{ent2found}\t{ent2type}\t{pubmed}\t{sapar}\t{sase}\t{relation}\n".format(
                            ent1=cooc.ent1,
                            ent2=cooc.ent2,
                            ent1found=cooc.ent1found,
                            ent2found=cooc.ent2found,
                            ent1type=cooc.ent1type,
                            ent2type=cooc.ent2type,
                            pubmed=cooc.pubmed,
                            sapar=cooc.sameParagraph,
                            sase=cooc.sameSentence,
                            relation=cooc.relation,
                        ), end='', flush=True)
                    """

                fileCoocs += foundCoocs

    
    print("Found {cnt} elems in files {ids}\n".format(cnt=str(len(fileCoocs)), ids=str(splitFileIDs)), file=sys.stderr, flush=True)


    #printed = printStuff(None, fileCoocs, None)

    thisProcID = str(os.getpid())
    print("{procID}: Found {cnt} (printed: {printed}) elems in files {ids}".format(
        cnt=str(len(fileCoocs)),
        ids=str(splitFileIDs),
        printed=len(fileCoocs),
        procID=thisProcID), file=sys.stderr, flush=True)

    return None

# --sentdir /mnt/d/dev/data/pmid_jun2020/pmid/ --resultdir /mnt/d/dev/data/pmid_jun2020/results.raw/ --datadir /mnt/d/dev/data/pmid_jun2020/ --folder1 hgnc --folder2 mirna --folderType1 gene --folderType2 mirna --same-sentence

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='aggregate tm results', add_help=False)
    parser.add_argument('-s', '--sentdir', type=str, help='where are the sentences?', required=True)
    parser.add_argument('-r', '--resultdir', type=str, help='where are all the index-files?', required=True)
    parser.add_argument('-d', '--datadir', type=str, help='where is te miRExplore bsae?', required=True)

    parser.add_argument('-sf', '--single-file', type=argparse.FileType("r"), help='single file processing mode', required=False, default=None)

    parser.add_argument('-f1', '--folder1', type=str, help='entity 1: hgnc, mirna', default="hgnc", required=False)
    parser.add_argument('-f2', '--folder2', type=str, help='entity 2: mgi, mirna', default="mirna", required=False)

    parser.add_argument('-ft1', '--folderType1', type=str, help='entity type 1: entity: mirna, gene, lncrna, ...', default="gene", required=False)
    parser.add_argument('-ft2', '--folderType2', type=str, help='entity type 2: entity: mirna', default="mirna", required=False)

    parser.add_argument('--sentid-no-text', dest='sentid_no_text', action="store_true", required=False, default=False)
    parser.add_argument('--sent-no-byte', dest='sent_no_byte', action="store_true", required=False, default=False)

    parser.add_argument('--same-sentence', dest='same_sentence', action="store_true", required=False, default=False)
    parser.add_argument('--accept_pmids', type=argparse.FileType('r'), required=False, default=None)

    parser.add_argument('--relex', type=argparse.FileType('r'), required=False, default=None)
    parser.add_argument('--mine-path', type=str, default="/mnt/f/dev/data/pmid_jun2020/", required=False)

    parser.add_argument("--threads", type=int, default=8, help="number of threads used for processing all files")

    parser.add_argument('--nlp', type=str, required=False, default='/mnt/f/spacy/en_core_sci_lg-0.2.4/en_core_sci_lg/en_core_sci_lg-0.2.4/')
    parser.add_argument('--nlpent', type=str, required=False, default="/mnt/f/spacy/en_ner_bionlp13cg_md-0.2.4/en_ner_bionlp13cg_md/en_ner_bionlp13cg_md-0.2.4")

    parser.add_argument("--max-finds-per-sentence", type=int, default=30, help="maximal number of entities found per sentence")



    args = parser.parse_args()

    print("Loading NLP", file=sys.stderr)
    nlp = spacy.load(args.nlp)
    print("Loading NLPENT", file=sys.stderr)
    nlp_ent = spacy.load(args.nlpent)
    print("NLPs loaded", file=sys.stderr)

    print("Creating relChecker", file=sys.stderr)
    relChecker = SentenceRelationChecker(nlp, nlp_ent)
    print("Creating relClassifier", file=sys.stderr)
    relClassifier = SentenceRelationClassifier(args.datadir + '/obodir/allrels.csv')
    print("miRExplore relation extraction models loaded", file=sys.stderr)

    #resultBase = dataDir + "/miRExplore/textmine/results_pmc/"
    resultBase = args.resultdir
    dataDir = args.datadir

    print("Getting Folder1 synfile.map", file=sys.stderr)
    ent1Syns = SynfileMap(resultBase + "/"+args.folder1+"/synfile.map")
    ent1Syns.loadSynFiles((args.mine_path, dataDir))

    print("Getting Folder2 synfile.map", file=sys.stderr)
    ent2Syns = SynfileMap(resultBase + "/"+args.folder2+"/synfile.map")
    ent2Syns.loadSynFiles((args.mine_path, dataDir))

    print("Getting relations synfile.map", file=sys.stderr)
    relSyns = SynfileMap(resultBase + "/relations/synfile.map")
    relSyns.loadSynFiles((args.mine_path, dataDir))

    print("Getting obodir/allrels.csv", file=sys.stderr)
    relationSyns = AssocSynfile(args.datadir + '/obodir/allrels.csv')
    print("All maps loaded", file=sys.stderr)


    accept_pmids = None

    if args.accept_pmids != None:

        accept_pmids = set()

        for line in args.accept_pmids:

            line = line.strip()

            if len(line) > 0:
                accept_pmids.add(line)

    idTuple2Pubmed = defaultdict(set)

    if args.single_file != None:
        allfiles = [args.single_file.name]
    else:
        allfiles = glob.glob(resultBase + "/"+args.folder1+"/*.index")

    allfileIDs = [os.path.basename(x).replace(".index", "") for x in allfiles]
    allfileIDs = sorted(allfileIDs, reverse=True)
    print("Going to process {} files!".format(len(allfileIDs)), file=sys.stderr)

    if __debug__:
        args.threads = 1
        print("Running on threads:" + str(args.threads), file=sys.stderr, flush=True)

    print("Debug Mode? " + str(__debug__) + " and threads " + str(args.threads), file=sys.stderr, flush=True)


    def printStuff(old, fileCoocs, env):


        setSeenRels = set()

        printed = 0

        for cooc in fileCoocs:

            coocRel = None if cooc.relation == None else tuple(cooc.relation)
            thisCooc = (
                cooc.ent1, cooc.ent1type, cooc.ent1found, cooc.ent2, cooc.ent2type, cooc.ent2found, cooc.pubmed, cooc.sameParagraph, cooc.sameSentence, coocRel
            )

            if thisCooc in setSeenRels:
                continue

            setSeenRels.add(thisCooc)

            print("{ent1}\t{ent1found}\t{ent1type}\t{ent2}\t{ent2found}\t{ent2type}\t{pubmed}\t{sapar}\t{sase}\t{relation}\n".format(
                ent1=cooc.ent1,
                ent2=cooc.ent2,
                ent1found=cooc.ent1found,
                ent2found=cooc.ent2found,
                ent1type=cooc.ent1type,
                ent2type=cooc.ent2type,
                pubmed=cooc.pubmed,
                sapar=cooc.sameParagraph,
                sase=cooc.sameSentence,
                relation=cooc.relation,
            ), end='', flush=True)

            printed += 1

        return printed


    if args.threads > 1:
        ll = MapReduce(args.threads)
        result = ll.exec(allfileIDs, analyseFile, None, 1, None)

    else:

        for fileID in allfileIDs:
            analyseFile([fileID], env=None)