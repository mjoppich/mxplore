import io
from collections import defaultdict

import os, sys
from enum import Enum

import os, sys
sys.path.insert(0, str(os.path.dirname(os.path.realpath(__file__))) + "/../")

from mxutils.SentenceID import SentenceID

class RegPos(Enum):
    BEFORE=-1
    AFTER=-2
    BEFORE_GM=1
    AFTER_GM=2
    BEFORE_MG=3
    AFTER_MG=4
    BETWEEN=5

class ElemOrder(Enum):
    MG=0
    GM=1

class Sentence:

    def __init__(self, sentid, text):

        self.id = sentid

        #attention: this is byte object for miRNA-gene interactions!
        self.text = text

    def __str__(self):
        return "{id}\t{txt}".format(id = self.id, txt=self.text)


    def extract_text(self, posM, posG):

        order = None
        text = None

        if posM[1] < posG[0]:
            order = ElemOrder.MG
        elif posG[1] < posM[0]:
            order = ElemOrder.GM
        else:
            order = None

        if order == ElemOrder.MG:
            textBefore = self.text[0:posM[0]]
            text = self.text[ posM[1]:posG[0] ]
            textAfter = self.text[posG[1]:]
        else:
            textBefore = self.text[0:posG[0]]
            text = self.text[ posG[1]: posM[0] ]
            textAfter = self.text[posM[1]:]


        return (textBefore, text, textAfter, order)


class SentenceDB:

    def __init__(self, file, sent_no_byte=False):

        self.pubmed2sents = defaultdict(list)
        self.filename = os.path.abspath(file)
        self.sent_no_byte = sent_no_byte

        if not os.path.isfile(self.filename):
            raise ValueError("Not a valid filename: " + self.filename)

        if self.sent_no_byte:
            self.pubmed2sents = self.loadFile_nobytes(self.filename)
        else:
            self.pubmed2sents = self.loadFile_bytes(self.filename)

    def loadFile_nobytes(self, filename):


        for encoding in [("utf8", "strict"), ("latin1", "strict"),("utf8", "ignore"), ("latin1", "ignore")]:
            try:
                print("Loading", filename, "with encoding", encoding, file=sys.stderr)
                with io.open(filename, 'r', encoding=encoding[0], errors=encoding[1]) as infile:
                    retObj = defaultdict(list)

                    for line in infile:
                        #line = line.decode('latin1')

                        line = line.strip()
                        if len(line) == 0:
                            continue

                        aline = line.split("\t")

                        if len(aline) != 2:
                            continue

                        sentID = SentenceID.fromStr(aline[0])
                        sentText = aline[1]

                        retObj[sentID.docID].append(Sentence(sentID, sentText))

                    return retObj

            except:
                continue

        return None


    def loadFile_bytes(self, filename):

        retObj = defaultdict(list)

        with io.open(filename, 'rb') as infile:

            for line in infile:
                #line = line.decode('latin1')

                line = line.strip()
                if len(line) == 0:
                    continue

                aline = line.split(b"\t")

                if len(aline) != 2:
                    continue

                sentID = SentenceID.fromStr(aline[0].decode())
                sentText = aline[1]

                retObj[sentID.docID].append(Sentence(sentID, sentText))

        return retObj


    def get_sentences(self, idval, default=None):

        if not idval in self.pubmed2sents:
            return default

        return self.pubmed2sents[idval]

    def get_sentence(self, sentid, default=None):

        allsent = self.get_sentences(sentid.docID)

        if allsent == None:
            return default

        for sent in allsent:

            if sent.id == sentid:
                return sent

        return default
