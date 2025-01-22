
import sys

import os, sys

sys.path.insert(0, str(os.path.dirname(os.path.realpath(__file__))) + "/../")

from mxutils.SynfileMap import SynonymID
from mxutils.SentenceID import SentenceID

class SyngrepHit:

    def __init__(self):

        self.documentID = None
        self.synonymID = None
        self.synonym = None

        self.foundSyn = None
        self.hitSyn = None

        self.perfectHit = False
        self.synType = None

        self.position = (None, None)

        self.originalLine = None
        
        self.prefix = None
        self.suffix = None
        self.sentenceIt = None

    def __hash__(self):
        return hash(self.position) ^ hash(self.foundSyn) ^ hash(self.hitSyn) ^ hash(self.documentID)

    def __str__(self):

        return "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
            self.documentID,
            self.synonymID,
            self.foundSyn,
            self.position[0],
            self.position[1]-self.position[0],
            self.hitSyn,
            self.perfectHit,
            self.prefix,
            self.suffix,
            self.sentenceIt
        )

    @classmethod
    def fromLine(cls, line, synfileMap,sentIDNoText=False):


        aline = [x.strip() for x in line.split('\t')]

        if len(aline) < 7:
            return None

        retObj = SyngrepHit()
        retObj.documentID = SentenceID.fromStr(aline[0])
        retObj.synonymID = SynonymID.fromStr(aline[1])

        if synfileMap != None:
            retObj.synonym = synfileMap.getSynonyme(retObj.synonymID)

            if retObj.synonym == None:
                retObj.synonym = synfileMap.getSynonyme(retObj.synonymID)

        retObj.foundSyn = aline[2]
        retObj.hitSyn = aline[5]

        sentStart = int(aline[3])
        sentLength = int(aline[4])

        if not sentIDNoText:
            sentStart -= len(str(retObj.documentID))+1

        if not sentStart >= 0:
            print(aline, file=sys.stderr)
            print(sentStart, sentLength, file=sys.stderr)


        retObj.position = (int(sentStart), int(sentStart)+int(sentLength))

        if len(aline) < 7:
            retObj.perfectHit = True
        else:
            retObj.perfectHit = aline[6].upper() == 'TRUE'
            
        if len(aline) >= 10:
            retObj.prefix = aline[7]
            retObj.suffix = aline[8]
            retObj.sentenceIt = aline[9]

        retObj.originalLine = line

        return retObj
