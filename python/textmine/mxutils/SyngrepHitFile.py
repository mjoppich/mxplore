from collections import defaultdict
import io

import os, sys

sys.path.insert(0, str(os.path.dirname(os.path.realpath(__file__))) + "/../")

from mxutils.SyngrepHit import SyngrepHit


class SyngrepHitFile:

    def __init__(self, filename, synfileMap = None, sentIDNoText=False):

        self.docid2hits = defaultdict(list)

        with io.open(filename, 'r', encoding="UTF-8", errors="ignore") as infile:

            for line in infile:

                #line = line.decode('latin1')

                hit = SyngrepHit.fromLine(line, synfileMap, sentIDNoText=sentIDNoText)

                if hit == None:
                    continue

                docID = hit.documentID.docID

                if docID == None:
                    exit(-1)

                self.docid2hits[docID].append(hit)

    def getHitsForDocument(self, docID):
        return self.docid2hits.get(docID, None)

    def __len__(self):
        return len(self.docid2hits)

    def __contains__(self, item):

        return item in self.docid2hits

    def __iter__(self):
        self.allDocIDs = [x for x in self.docid2hits]
        self.currentDocIdx = 0
        return self

    def __next__(self):

        if self.currentDocIdx < len(self.allDocIDs):
            idx = self.currentDocIdx
            self.currentDocIdx += 1
            return self.allDocIDs[idx]

        raise StopIteration()