import codecs
import re
from enum import Enum
import shlex
import sys

from collections import defaultdict

class GOTermType(Enum):
    TERM=0


class GORelationType(Enum):
    NONE=0
    REGULATES=1
    PARTOF=2
    IS_A=3

class GOSynonymeType(Enum):
    UNKNOWN=0

class GOSynonymeScope(Enum):
    EXACT=0
    BROAD=1
    NARROW=2
    RELATED=3

class GOSynonyme:
    def __init__(self, synonyme, scope, type=GOSynonymeType.UNKNOWN, xrefs=None):
        self.type = type
        self.syn = synonyme
        self.scope = scope
        self.xrefs = xrefs

        self.original_syn = None

        if self.scope == GOSynonymeScope.NARROW:
            if any([x in synonyme for x in ['NARROW', 'EXACT', 'BROAD', 'RELATED']]):
                try:
                    syn = GOTerm.handleSynonyme(self.syn)

                    if syn != None:

                        self.original_syn = self.syn

                        self.type = syn.type
                        self.syn = syn.syn
                        self.scope = syn.scope
                        self.xrefs = syn.xrefs


                except:
                    pass

    def __eq__(self, other):

        if other == None:
            return False

        synEq = self.syn == other.syn
        typeEq = self.type == other.type
        scopeEq = self.scope == other.scope


        xrefsEq = True

        if self.xrefs == None and other.xrefs != None:
            xrefsEq = False

        if self.xrefs != None and other.xrefs == None:
            xrefsEq = False

        if self.xrefs != None and other.xrefs != None:
            xrefsEq = self.xrefs == other.xrefs

        return synEq and typeEq and scopeEq and xrefsEq


    def __hash__(self):

        xrefhash = 0

        if self.xrefs != None:
            xrefhash = sum([hash(x) for x in sorted(self.xrefs)])

        return hash(self.type) + hash(self.scope) + hash(self.syn) + xrefhash


    def __repr__(self):
        return self.__str__()

    def __str__(self):

        xreflist = [] if self.xrefs == None else self.xrefs

        if isinstance(xreflist, str):
            if xreflist.endswith("]") and not xreflist.startswith("["):
                print("Strange xreflist", xreflist, self.original_syn)
                xreflist = "[" + xreflist

        return "\"{text}\" {scope} {xrefs}".format(text=self.syn, scope=self.scope.name, xrefs=str(xreflist))


class GOMappingEvidence(Enum):
    EXP=0
    IDA=1
    IPI=2
    IMP=3
    IGI=4
    IEP=5
    ISS=6
    ISO=7
    ISA=8
    ISM=9
    IGC=10
    IBA=11
    IBD=12
    IKR=13
    IRD=14
    RCA=15
    TAS=16
    NAS=17
    IC=18
    ND=19
    IEA=20


class GORelation:

    def __init__(self, type = GORelationType.NONE, termid = None, desc=None, term=None):

        self.type = type
        self.termid = termid
        self.desc = desc
        self.term = term

    def __repr__(self):
        return self.__str__()

    def __str__(self):


        if self.term == None:
            prefix="{reltype}: {termid}".format(reltype=self.type.name.lower(), termid=self.termid)

            if self.desc != None:
                suffix = " ! {termname}".format(termname=self.desc)

                return prefix + suffix
            else:
                return prefix

        else:
            prefix = "{reltype}: {termid} ! {termname}".format(reltype=self.type.name.lower(), termid=self.term.id, termname=self.term.name)
            return prefix




class GOTerm:

    def __init__(self):

        self.type = GOTermType.TERM
        self.id = None
        self.name = None
        self.namespace = None
        self.definition = None
        self.synonym = None
        self.is_a = None
        self.subset = None
        self.disjoint_from = None
        self.xref = None
        self.alt_id = None
        self.consider = None

        self.intersection_of = None

        self.is_obsolete = None
        self.comment=None
        self.children = None

        self.property_values = {}

    @classmethod
    def from_synonym(cls, syn):

        term = GOTerm()
        term.id = syn.id
        term.name = syn.id
        term.synonym = set()
        
        for x in syn.syns[1:]:

            termSyn = GOSynonyme(x, GOSynonymeScope.EXACT)
            term.synonym.add(termSyn)

        return term


    def get_parents(self):

        if self.is_a == None or len(self.is_a) == 0:
            return None

        setparents = set()

        for x in self.is_a:
            setparents.add(x)

        return list(setparents)

    def add_child(self, child):

        if self.children == None:
            self.children = set()

        self.children.add(child)


    def __str__(self):
        return self.__repr__()


    def toObo(self):
        lines = []

        lines.append("[Term]")
        lines.append("id: " + str(self.id))
        lines.append("name: " + str(self.name))

        if self.comment:
            lines.append("comment: \"{comment}\"".format(comment=self.comment))

        if self.namespace != None:
            lines.append("namespace: " + str(list(self.namespace)))

        if self.synonym != None:
            for syn in self.synonym:
                lines.append("synonym: " + str(syn))

        if self.is_a != None:
            for rel in self.is_a:
                lines.append(str(rel))

        if self.definition != None:
            lines.append("def: \"{definition}\"".format(definition=str(self.definition).strip('"')))

        if self.xref != None:

            if len(self.xref) > 0:

                for elem in self.xref:
                    lines.append("xref: {xrefs}".format(xrefs=str(elem)))

                #lines.append("xref: {xrefs}".format(xrefs=str(list(self.xref))))

        return "\n".join(lines)



    def __repr__(self):

        return str(self.id) + " " + str(self.name)


    def __children_at_level(self, already_seen, level, withLevel=False):

        if self.children == None or level == 0:

            if not withLevel:
                already_seen.add(self)
            else:
                already_seen.add( (self, level) )

            return

        for x in self.children:
            x.term.__children_at_level(already_seen, level-1, withLevel)

    def getChildrenAtLevel(self, level, withLevel=False):

        allchildren = set()

        self.__children_at_level(allchildren, level, withLevel=withLevel)

        if withLevel:
            allchildren = set([(x, level-l) for x,l in allchildren])


        return allchildren


    def getAllChildren(self, maxLevel=-1, withLevel=False, includeTerm=False):

        allchildren = set()

        self.__addAllChildrenRec(allchildren, maxLevel, withLevel=withLevel)

        if withLevel:
            allchildren = set([(x, maxLevel-l) for x,l in allchildren])

        if includeTerm:
            allchildren.add(GORelation(GORelationType['IS_A'], desc=self.name, termid=self.id, term=self))

        return allchildren

    def __addAllChildrenRec(self, already_seen, maxLevel, withLevel=False):

        if self.children == None or maxLevel == 0:
            return

        for x in self.children:

            if not x in already_seen:

                if not withLevel:
                    already_seen.add(x)
                else:
                    already_seen.add((x, maxLevel))

                childchildren = x.term.__addAllChildrenRec(already_seen, maxLevel-1, withLevel=withLevel)

    def getAllParents(self):

        allParents = set()
        seenByLevel = defaultdict(set)

        self.__getAllParents(seenByLevel, allParents, 0)

        return allParents

    def getAllParentyByLevel(self):

        allParents = set()
        seenByLevel = defaultdict(set)

        self.__getAllParents(seenByLevel, allParents, 0)

        return seenByLevel

    def __getAllParents(self, seenByLevel, already_seen, currentLevel):

        if self.is_a == None:
            return

        if None in self.is_a:
            print("oboterm with none parent ...", self.id, self.name)

        for x in self.is_a:

            if not x.term in already_seen:

                if x.term == None:
                    #print("None observed", x, x.termid)
                    continue

                already_seen.add(x.term)
                seenByLevel[currentLevel].add(x.term)

                x.term.__getAllParents(seenByLevel, already_seen, currentLevel+1)


    @classmethod
    def getKeyValueFromLine(cls, sLine):

        sLine = sLine.strip()

        aLine = sLine.split(":")

        key = aLine[0].strip()
        value = ":".join( aLine[1:] )
        value = value.strip()

        return (key, value)

    @classmethod
    def compareIDs(cls, id1, id2):

        return id1.upper() == id2.upper()

    @classmethod
    def splitSynonymValue(cls, search, delimeter=' ', quotedText={'(': ')', '[': ']', '\"': '\"', '\'': '\''}):

        try:
            aval = shlex.split(search)
        except:
            aval = shlex.split(search + "'")


        if aval[0].startswith("\"") and aval[0].endswith("\""):
            aval[0] = aval[0][1:len(aval[0])-1]


        if len(aval) < 4:
            return aval

        rval = []
        rval.append(aval[0])
        rval.append(aval[1])
        rval.append(aval[2])
        rval.append(" ".join(aval[3:]))


        return rval


        splitPos = []
        i = 0
        while i < len(search) and not i < 0:

            char = search[i]
            if char in quotedText:
                pos = search.find(quotedText[char], i + 1)
                i = pos + 1
                continue

            elif char == delimeter:
                splitPos.append(i)

            i += 1

        allWords = []

        lastStart = 0
        for pos in splitPos:
            word = search[lastStart:pos]
            lastStart = pos + len(delimeter)
            allWords.append(word)

        if lastStart != len(search):
            word = search[lastStart:]
            allWords.append(word)

        quoteChars = set()
        for x in quotedText:
            quoteChars.add(x)
            quoteChars.add(quotedText[x])

        retWords = []
        for word in allWords:
            if word[0] in quoteChars and word[-1] in quoteChars:
                retWords.append(word[1:len(word) - 1])
            else:
                retWords.append(word)
        return retWords

    @classmethod
    def parseFromLines(cls, vLines):

        # remove empty lines
        vLines = [x for x in vLines if len(x) > 0]

        # check that we got a term here
        if not vLines[0] == "[Term]":
            return None


        term = GOTerm()

        for sLine in vLines:

            sLine = sLine.strip()

            if sLine.startswith("#"):
                continue

            if sLine[0] == '[' and sLine[len(sLine)-1] == ']':

                sType = sLine[1:len(sLine)-1]

                term.type = GOTermType[sType.upper()]
                continue

            (key, value) = cls.getKeyValueFromLine(sLine)

            if cls.compareIDs("ID", key):
                term.id = value

            elif cls.compareIDs("alt_id", key):

                if term.alt_id == None:
                    term.alt_id = set()

                term.alt_id.add(value)

            elif cls.compareIDs("SYNONYM", key):

                if term.synonym == None:
                    term.synonym = set()

                elem = cls.handleSynonyme(value)

                if elem == None:
                    print("syn empty", value)
                    print("syn empty", term.id)
                    print("syn empty", sLine)

                term.synonym.add(elem)

            elif cls.compareIDs("DEF", key):
                term.definition = value

            elif cls.compareIDs("namespace", key):

                if term.namespace == None:
                    term.namespace = set()

                term.namespace.add(value)

            elif cls.compareIDs("NAME", key):
                term.name = value

            elif cls.compareIDs("COMMENT", key):

                if value[0] == value[-1] and value[0] == '"':
                    value = value[1:len(value)-1]

                term.comment=value

            elif cls.compareIDs("is_a", key) or cls.compareIDs('derived_from', key):

                oRelation = cls.handleISA(value)

                if oRelation != None:

                    if term.is_a == None:
                        term.is_a = set()

                    term.is_a.add(oRelation)

            elif cls.compareIDs("SUBSET", key):

                if term.subset == None:
                    term.subset = set()

                term.subset.add(value)

            elif cls.compareIDs("XREF", key):

                if term.xref == None:
                    term.xref = set()

                term.xref.add(value)

            elif cls.compareIDs("is_obsolete", key):

                if cls.compareIDs("true", value):
                    term.is_obsolete = True
                else:
                    term.is_obsolete = False

            elif cls.compareIDs('relationship', key):

                value = value.strip()
                if value.upper().startswith('DERIVED_FROM'):
                    avalue = value.split(' ')
                    fromName = " ".join(avalue[1:])

                    oRelation = cls.handleISA(fromName)

                    if oRelation != None:

                        if term.is_a == None:
                            term.is_a = set()

                        term.is_a.add(oRelation)


            elif cls.compareIDs("property_value", key):


                try:

                    lexer = shlex.shlex(value, posix=True)
                    lexer.quotes = '"'
                    lexer.wordchars += '\'[:].'
                    aValue = list(lexer)

                except ValueError:

                    print(vLines)

                    print(lexer.quotes)
                    print(lexer.wordchars)

                    print(value)
                    exit(-1)

                for i in range(0, len(aValue)):

                    aValue[i] = aValue[i].strip()
                    if len(aValue[i]) > 0 and aValue[i][0] == "\"" and aValue[i][len(aValue[i]) - 1] == "\"":
                        aValue[i] = aValue[i][1:len(aValue[i]) - 2]

                if cls.compareIDs("synonymExact", aValue[0]) or cls.compareIDs("synonymRelated", aValue[0]) or cls.compareIDs("synonymNarrow", aValue[0]) or cls.compareIDs("IAO:0000118", aValue[0]):

                    if term.synonym == None:
                        term.synonym = set()

                    scopeT = None
                    if cls.compareIDs("synonymExact", aValue[0]):
                        scopeT = GOSynonymeScope.EXACT
                    elif cls.compareIDs("synonymRelated", aValue[0]):
                        scopeT = GOSynonymeScope.RELATED
                    elif cls.compareIDs("synonymBroad", aValue[0]):
                        scopeT = GOSynonymeScope.BROAD
                    else:
                        scopeT = GOSynonymeScope.NARROW

                    aSplitVals = [aValue[1]]# was: aValue[1].split(", ")

                    for splitval in aSplitVals:
                        syn = GOSynonyme(splitval, scopeT, GOSynonymeType.UNKNOWN, None)

                        if syn == None:
                            print("synExact empty", aValue)
                        term.synonym.add(syn)


                elif aValue[0].startswith("synonym"):

                    if term.synonym == None:
                        term.synonym = set()

                    syn = GOSynonyme(aValue[1], GOSynonymeScope.EXACT, GOSynonymeType.UNKNOWN, None)

                    if syn == None:
                        print("synonym empty", aValue)

                    term.synonym.add(syn)

                else:
                    term.property_values[aValue[0]] = aValue[1]

            else:

                if not key in ['property_value', 'replaced_by', 'created_by', 'creation_date', 'disjoint_from', 'comment', 'consider', 'relationship', 'intersection_of']:

                    sys.stderr.write("unprocessed key: " + str(key) +  "\t" + str(sLine.strip())  + "\n")

        return term

    @classmethod
    def handleSynonyme(cls, value):
        """

        :param value:
        :return: GOSynonyme
        """

        aval = cls.splitSynonymValue(value)

        if len(aval) > 3:
            syn = 0
            scope = 1
            syntype=2
            xrefs=3
        else:
            syn = 0
            scope=1
            syntype=-1
            xrefs=2

        try:

            scopet = None
            synt = None
            synxrefs = None
            syntypet = GOSynonymeType.UNKNOWN

            scopet = GOSynonymeScope[aval[scope]]
            syntext = aval[syn]
            synxrefs = aval[xrefs]

            if syntype > 0:
                syntypett = aval[syntype].upper()

                try:
                    syntypet = GOSynonymeType[syntypett]

                except:
                    # apparently not a type.

                    if not ((synxrefs.startswith("[") and synxrefs.endswith("]")) or (synxrefs.startswith("{") and synxrefs.endswith("}"))):
                        synxrefs = aval[syntype] + " " + aval[xrefs]

                    syntypet = GOSynonymeType.UNKNOWN #GOSynonymeType[syntypett]

            if synxrefs == '':
                synxrefs = None

            if synxrefs != None and not ((synxrefs.startswith("[") and synxrefs.endswith("]")) or (synxrefs.startswith("{") and synxrefs.endswith("}"))):
                print(value, aval, syntypet, synxrefs)

            syn = GOSynonyme( syntext, scopet, syntypet, synxrefs )
            if syn == None:
                sys.stderr.write("Empty syn: " + str(value) + "\n")
            return syn

        except:


            return None

    #is_a: GO:0048308 ! organelle inheritance
    @classmethod
    def handleISA(cls, value):
        """

        :param value: value part of an is_a line
        :return: GORelation for :value
        """

        sRefTerm = value.split("!")
        sRefTerm = sRefTerm[0].strip()

        if "{" in sRefTerm:
            sRefTerm = sRefTerm[0:sRefTerm.index("{")-1]


        if len(sRefTerm) == 0:
            return None

        if len(sRefTerm) == 2:
            sRefDesc = sRefTerm [1]
        else:
            sRefDesc = None

        oRelation = GORelationType['IS_A']

        return GORelation(oRelation, termid=sRefTerm, desc=sRefDesc)

    @classmethod
    def merge(cls, term1, term2, newID):

        newTerm = GOTerm()
        newTerm.id = newID

        newTerm.name = term1.name
        newTerm.synonym = set()
        newTerm.synonym.add(GOSynonyme(term1.name, GOSynonymeScope.EXACT))

        newTerm.is_a = set()

        if term1.is_a != None:
            for parent in term1.is_a:
                newTerm.is_a.add(parent)

        if term2.is_a != None:
            for parent in term2.is_a:
                newTerm.is_a.add(parent)

        if term1.synonym:
            for x in term1.synonym:
                newTerm.synonym.add(x)

        if term2.synonym:
            for x in term2.synonym:
                newTerm.synonym.add(x)

        newTerm.children = set()

        if term1.children:
            for x in term1.children:
                newTerm.children.add(x)

        if term2.children:
            for x in term2.children:
                newTerm.children.add(x)

        return newTerm


class GOGeneMapping:

    def __init__(self):

        self.mapping_evidence = None
        self.gene_id = None
        self.organism = None

    def __repr__(self):
        return self.__str__()

    def __str__(self):

        return str(self.organism) + " " + str(self.gene_id) + " " + str(self.mapping_evidence.name)



class GeneOntology:

    def __init__(self, sFileName = None):

        self.dTerms = {}
        self.dTermMapping = defaultdict(set)
        self.dGeneIDMapping = {}

        if sFileName != None:
            self.loadFile(sFileName)

    def __getitem__(self, item):
        return self.dTerms.__getitem__(item)

    def __setitem__(self, key, value):
        retval = self.dTerms.__setitem__(key, value)

        self.linkChildren()

        return retval

    def __len__(self):
        return self.dTerms.__len__()

    def loadGeneAnnotation(self, sFileName, organisms):

        if type(organisms) == int:
            organisms = {organisms}


        def addGeneAnnotation(sLine, iLine):

            nonlocal organisms

            if len(sLine) > 0 and sLine[0] == '#':
                return

            aLine = sLine.split("\t")

            iOrg = int(aLine[0])

            if iOrg not in organisms:
                return

            iGeneID = int(aLine[1])
            sGOClass = aLine[2]
            sEvidence = aLine[3].upper()
            oEvidence = GOMappingEvidence[sEvidence]

            oMapping = GOGeneMapping()
            oMapping.gene_id = iGeneID
            oMapping.mapping_evidence = oEvidence
            oMapping.organism = iOrg

            if sGOClass in self.dTerms:
                self.dTermMapping.add(sGOClass, oMapping)

        with open(sFileName, 'r') as infile:
            for line in infile:
                addGeneAnnotation(line.strip(), 0)

    def replaceISA(self, oTerm, dAllTerms):

        if oTerm.is_a == None or len(oTerm.is_a) == 0:
            return

        for isa in oTerm.is_a:

            if isinstance(isa.termid, str):

                if isa.termid in dAllTerms:
                    isa.term = dAllTerms[isa.termid]


    def loadFile(self, sFileName):

        dTerms = {}

        def processLines(sLine, iLine):

            nonlocal vCurrentTermLines
            nonlocal dTerms

            #sLine = inLine.decode('utf-8')
            if '?' in sLine and not "CHEBI" in sLine:
                sLine = sLine

            if 'owlATOL:0002274' in sLine:
                sLine = sLine

            sLine = sLine.strip()

            if len(sLine) > 2 and sLine[0] == '[' and sLine[len(sLine)-1] == ']':

                if len(vCurrentTermLines) > 0:

                    oNewTerm = GOTerm.parseFromLines(vCurrentTermLines)

                    if oNewTerm != None and oNewTerm.id == 'owlATOL:0002274':
                        oNewTerm.id = 'owlATOL:0002274'


                    if oNewTerm != None:

                        self.replaceISA(oNewTerm, dTerms)

                        if len(dTerms) % 10000 == 0:
                            sys.stderr.write(str(len(dTerms)) + "\n")

                        dTerms[oNewTerm.id] = oNewTerm

                vCurrentTermLines = []

            vCurrentTermLines.append(sLine)

            return vCurrentTermLines


        vCurrentTermLines = []

        with open(sFileName, 'r', encoding='utf-8') as oFile:
            iLineCount = 0

            for sLine in oFile:
                #sLine = str(sLine, "utf-8")
                processLines(sLine, iLineCount)
                iLineCount = iLineCount + 1

        if len(vCurrentTermLines) > 0:

            oNewTerm = GOTerm.parseFromLines(vCurrentTermLines)
            if oNewTerm != None:
                self.replaceISA(oNewTerm, dTerms)
                if len(dTerms) % 10000 == 0:
                    sys.stderr.write(str(len(dTerms)) + "\n")
                dTerms[oNewTerm.id] = oNewTerm

        self.dTerms = dTerms

        self.linkChildren()

    def addterm(self, other):

        return self.addterms([other])

    def addterms(self, others, link_children=True):

        assert(isinstance(others, (list, set)))

        for x in others:
            assert(isinstance(x, GOTerm))

        for x in others:
            self.dTerms[x.id] = x

        if link_children:
            self.linkChildren()


    def linkChildren(self):

        for x in self.dTerms:
            elem = self.dTerms[x]

            if elem != None:
                elem.children = None


        # replace all remaining str GO references with objects
        for x in self.dTerms:
            oElem = self.dTerms[x]
            self.replaceISA(oElem, self.dTerms)


        iNoParent = 0

        # also add child references
        for x in self.dTerms:

            child = self.dTerms[x]

            vParents = child.get_parents()

            if vParents == None or len(vParents) == 0:
                iNoParent += 1
                # print(str(id) + " has no parents!")

            if vParents == None:
                continue

            for parent in vParents:
                #parent is GORelation

                if parent.term == None:
                    parent.term = self.dTerms[parent.termid] if parent.termid in self.dTerms else None

                oParent = parent.term

                if oParent == None:
                    continue

                oParent.add_child(GORelation(parent.type, termid=child.id, desc=child.name, term=child))

        sys.stderr.write("no parent " + str(iNoParent) + "\n")

    def getID(self, oID):

        if oID in self.dTerms:
            return self.dTerms[oID]

        return None

    def getMappings(self, taxids, id):
        if type(taxids) == int:
            taxids = {taxids}

        found_genes = set()

        if id in self.dTermMapping:

            vAllMappings = self.dTermMapping[id]

            for mapping in vAllMappings:

                if taxids == None or len(taxids) == 0 or mapping.organism in taxids:
                    found_genes.add(mapping)

            if len(found_genes) > 0:
                return found_genes


        return None

    def saveFile(self, path):

        with open(path, 'w') as outfile:

            for elemid in self.dTerms:

                node = self.dTerms[elemid]

                outfile.write( node.toObo() + "\n\n" )

            return path

        return None

    def mergeTerms(self, listOfIDs, idStr, linkChildren=True):

        if len(listOfIDs) < 2:
            return

        initialMerge = GOTerm.merge(self[listOfIDs[0]], self[listOfIDs[1]], idStr)

        if len(listOfIDs) > 2:

            for i in range(2, len(listOfIDs)):
                initialMerge = GOTerm.merge(initialMerge, self[listOfIDs[i]], idStr)

        for id in listOfIDs:
            if id in self.dTerms:
                del self.dTerms[id]

        self.dTerms[idStr] = initialMerge

        if linkChildren:
            self.linkChildren()

        return initialMerge


    def getGenes(self, taxids, id):
        """

        returns tuples of taxid, gene_id . If you need only gene_id: [x[1] for x in getGenes(...)]

        :param taxids: tax id of organisms to look for
        :param id: term id to search for
        :return: set of tuples (taxid, gene_id)
        """

        mappings = self.getMappings(taxids, id)

        if mappings == None:
            return None

        genes = [ (x.organism, x.gene_id) for x in mappings ]

        return genes

    def getRoots(self):

        vroots = []
        for x in self.dTerms:

            child = self.dTerms[x]

            vParents = child.get_parents()

            if vParents == None or len(vParents) == 0:
                vroots.append(child)
        return vroots


    @classmethod
    def mergeOntologies(cls, iter):

        newOnto = GeneOntology()

        iCnt = 0
        for onto in iter:

            for id in onto.dTerms:

                term = onto.dTerms[id]

                if not id in newOnto.dTerms:
                    newOnto.dTerms[id] = term
                else:

                    newid = 'META:' + str(iCnt)

                    sys.stderr.write(" ".join(("Merging: ", term.id, str(newOnto[id]), " into ", newid))+"\n")

                    mergedTerm = GOTerm.merge(term, newOnto.dTerms[id], newid)
                    iCnt += 1
                    newOnto.dTerms[id] = mergedTerm

        newOnto.linkChildren()

        return newOnto


if __name__ == '__main__':

    #GOTerm.handleSynonyme("\"Kenya baboon\" EXACT common_name []")

    #oTest = GeneOntology("/home/proj/projekte/textmining/FBN_ATOL_Dummerstorf/Daten-Ontologien/MethodOntology_MZ1.obo") #"C:/ownCloud/data/biomodels/go.obo"
    #oTest.loadGeneAnnotation("/home/users/joppich/ownCloud/data/biomodels/gene2go.9606", {9606})
    #oTest = GeneOntology("/home/proj/projekte/textmining/FBN_ATOL_Dummerstorf/Daten-Ontologien/synonymes/modified/atol_v6_MZ.prot.obo")
    #oTest = GeneOntology('/mnt/c/dev/data/fbn_textmine/mom_new.obo')
    #oTest = GeneOntology('/mnt/c/Users/mjopp/Downloads/ncit.obo')
    #oTest = GeneOntology('/home/mjoppich/ownCloud/data/miRExplore/obodir/ncit.obo')
    #oTest = GeneOntology('/mnt/c/ownCloud/data/miRExplore/cellline_ontology/clo.new.owl.obo')
    #oTest = GeneOntology('/mnt/c/ownCloud/data/miRExplore/cell_ontology/cl.obo')

    oTest = GeneOntology('/home/mjoppich/dev/data/tm_soehnlein/obodir/messages.obo')

    for termID in oTest.dTerms:
        print(termID)

    allRoots = oTest.getRoots()

    print("ROOTS")
    child2root = {}
    for x in allRoots:
        allchildren = x.getAllChildren()

        for t in allchildren:
            child2root[t.term.id] = x.name
            child2root[t.term.name] = x.name

    print(child2root)
    exit()

    #oTest.saveFile("/mnt/c/ownCloud/data/miRExplore/cellline_ontology/clo.new.obo")

    #print(oTest.getID('GO:0002281'))
    #print(oTest.getGenes({9606}, 'GO:0002281'))

    #oterm = oTest.dTerms['NCIT:C17764']
    oterm = oTest.dTerms['CL:0000115']
    oterm.toObo()
    allchildren = oterm.getAllChildren()

    #print(len(allchildren))

    #oRet = GeneOntology()

    newTerm = GOTerm()
    newTerm.id = "interleukin"
    newTerm.name = "interleukin"
    newTerm.synonym = set()

    seenSyns = set()

    hsaMmu = ('CXCL', 'Cxcl')
    hsaMmu = None


    for rel in allchildren:
        #print(rel.term.id, rel.term.name)
        print(rel.term.id.replace(":", "_"))

        termSyns = [GOSynonyme(rel.term.name, GOSynonymeScope.BROAD)]

        if rel.term.synonym != None:
            termSyns += rel.term.synonym

        for x in termSyns:


            if x.syn in seenSyns:
                continue

            seenSyns.add(x.syn)

            x.scope = GOSynonymeScope.BROAD
            newTerm.synonym.add(x)

            if hsaMmu != None:


                if x.syn.startswith(hsaMmu[0]+"-"):
                    nsyn = x.syn.replace(hsaMmu[0]+"-", hsaMmu[0])

                    y = GOSynonyme(nsyn, GOSynonymeScope.BROAD, GOSynonymeType.UNKNOWN, x.xrefs)
                    newTerm.synonym.add(y)

                if x.syn.startswith(hsaMmu[0]):
                    nsyn = x.syn.replace(hsaMmu[0], hsaMmu[1])

                    y = GOSynonyme(nsyn, GOSynonymeScope.BROAD, GOSynonymeType.UNKNOWN, x.xrefs)
                    newTerm.synonym.add(y)

                    if x.syn.startswith(hsaMmu[0]+"-"):
                        nsyn = x.syn.replace(hsaMmu[0]+"-", hsaMmu[0])

                        y = GOSynonyme(nsyn, GOSynonymeScope.BROAD, GOSynonymeType.UNKNOWN, x.xrefs)
                        newTerm.synonym.add(y)

            else:

                nsyn = x.syn.lower()

                y = GOSynonyme(nsyn, GOSynonymeScope.BROAD, GOSynonymeType.UNKNOWN, x.xrefs)
                newTerm.synonym.add(y)





        #print(oTest.dTerms[rel.term.id].toObo())

    print(newTerm.toObo())


    #    oRet.dTerms[rel.term.id] = rel.term

    #oRet.saveFile("/mnt/c/Users/mjopp/Desktop/ncit.obo")

    #oTest = GeneOntology('/mnt/c/Users/mjopp/Desktop/ncit.obo')


    #print( oTest.getRoots() )