import glob
import os, sys
sys.path.insert(0, str(os.path.dirname(os.path.realpath(__file__))) + "/../")


from collections import defaultdict
from lxml import etree
import tarfile
from mxutils.idutils import eprint

import logging
import nltk.data
from copy import deepcopy
from mxutils.parallel import MapReduce
import spacy
import scispacy

logger = logging.getLogger('convertJatsToText')


class PubmedJournal:
    def __init__(self, journal, isoabbrev):
        self.journal = journal
        self.isoabbrev = isoabbrev



class PubmedEntry:
    
    def __init__(self, pubmedId):

        self.pmid = pubmedId
        self.pmc = None
        self.created = None
        self.journal = None

        self.title = None
        self.abstract = None
        self.sections = None

        self.pub_types = None
        self.cites = None

        self.authors = []
        self.doi = None

    def getID(self):
        return self.pmid
            

    def _makeSentences(self, content, tokenizer):

        returns = []

        if type(content) == str:
            returns = tokenizer(content)#tokenizer.tokenize(content)
        else:
            for x in content:
                sents = tokenizer(x)#tokenizer.tokenize(x)
                returns += sents

        #returns = [x + "." for x in returns]

        return returns

    def to_sentences(self, tokenizer):

        finalSents = []

        abstracts = [self.abstract[x] for x in self.abstract]
        abstractSents = self._makeSentences(abstracts, tokenizer)

        sections = [self.sections[x] for x in self.sections]
        textSents = self._makeSentences(sections, tokenizer)

        titleSents = self._prepareSentences(str(self.pmid), 1, [self.title])
        for x in titleSents:
            finalSents.append(x)

        if len(abstractSents) > 0:
            abstractSents = self._prepareSentences(str(self.pmid), 2, abstractSents)

            for x in abstractSents:
                finalSents.append(x)

        if len(textSents) > 0:
            textSents = self._prepareSentences(str(self.pmid), 3, textSents)

            for x in textSents:
                finalSents.append(x)

        return finalSents

    def _prepareSentences(self, articleName, module, sents):

        iSent = 1
        outContent = []

        for x in sents:

            if x == None:
                continue

            x = x.strip()
            #x = x.strip(',.;')

            if len(x) > args.min_sent_length:

                content = "{}.{}.{}\t{}".format(articleName, module, iSent, x)
                #content = str(articleName) + "." + str(module) + "." + str(iSent) + "\t" + str(x)
                outContent.append(content)
                iSent += 1

        return outContent


    def printIgnoration(self):

        for (section, cnt) in self.ignoredSections.most_common():
            print(str(section) + " " + str(cnt))

    @classmethod
    def get_node_with_attrib(cls, node, path, attrib, attribvalue, default=None):
        try:
            values = [x for x in node.findall(path)]

            for idNode in values:
                if not attrib in idNode.attrib:
                    continue

                idType = idNode.attrib[attrib]

                if idType == attribvalue:
                    return idNode

            return default
        except:
            return default

    @classmethod
    def get_nodes_with_attrib(cls, node, path, attrib, attribvalue, default=None):
        try:
            values = [x for x in node.findall(path)]
            keepNodes = []

            for idNode in values:
                if not attrib in idNode.attrib:
                    continue

                idType = idNode.attrib[attrib]

                if idType == attribvalue:
                    keepNodes.append(idNode)

            return keepNodes
        except:
            return default

    @classmethod
    def get_node(cls, node, path, default=None):
        try:
            value = node.find(path)
            return value
        except:
            return default

    @classmethod
    def get_value_from_node(cls, node, path, default=None):
        try:
            if path != None:
                valueElem = node.find(path)
                value = valueElem.text
                return value
            else:
                return node.text
        except:
            return default

    @classmethod
    def get_inner_text_from_node(cls, node, default=[]):
        if node == None:
            return default
        texts = [x.strip() for x in node.itertext() if len(x.strip()) > 0]

        if len(texts) == 0:
            return default
        elif len(texts) == 1:
            return texts[0]
        else:
            return texts

    @classmethod
    def get_inner_text_from_path(cls, node, path, default=None):
        fnode = cls.get_node(node, path, None)
        textReturn =  cls.get_inner_text_from_node(fnode, default=default)

        if type(textReturn) == list:
            textReturn = " ".join(textReturn)
        
        return textReturn

    @classmethod
    def get_nodes(cls, node, path):
        try:
            return [x for x in node.find(path)]
        except:
            return []

    @classmethod
    def _find_doi(cls, node):
        if node == None:
            return None

        idnodes = cls.get_nodes(node, 'PubmedData/ArticleIdList')

        for idnode in idnodes:
            if not 'IdType' in idnode.attrib:
                continue

            idType = idnode.attrib['IdType']

            if idType == 'doi':
                return idnode.text

        return None

    @classmethod
    def _find_authors(cls, node):
        if node == None:
            return None

        authNodes = cls.get_nodes_with_attrib(node, 'front/article-meta/contrib-group//contrib',"contrib-type", "author")

        allAuthors = []

        for authorNode in authNodes:

            lastName = cls.get_value_from_node(authorNode, 'name/given-names', '')
            foreName = cls.get_value_from_node(authorNode, 'name/surname', '')
            initials = ''
            affiliation = ''

            if lastName == '' and foreName == '':
                continue 

            allAuthors.append( (lastName, foreName, initials, affiliation) )

        return allAuthors

    @classmethod
    def get_node_values(cls, node):
        if node == None:
            return None

        childNodes = [x for x in node]

        allValues = []

        for child in childNodes:

            value = cls.get_value_from_node(child, None, None)

            if value != None:
                allValues.append(value)

        return allValues

    def cleanAbstract(self, abstract):

        for x in ['ABSTRACT TRUNCATED AT 250 WORDS', 'ABSTRACT TRUNCATED AT 400 WORDS', 'ABSTRACT TRUNCATED']:

            if abstract.endswith(x):
                return abstract.replace(x, '')

        return abstract

    @classmethod
    def get_abstract(cls, node):

        # TODO care for structued abstracts https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html#publicationtypelist
        structuredAbstract = {}

        abstractTexts = cls.get_nodes(node, '//abstract')

        if len(abstractTexts) == 0:
            abstractTexts = cls.get_nodes(node, './/abstract')

        for atext in abstractTexts:

            if type(atext) in [etree._Comment, etree._ProcessingInstruction]:
                continue

            label = atext.attrib.get('id', 'p1').upper()
            text = "".join([x for x in atext.itertext()])#atext.text
            if text != None:
                text = cls.removeLinebreaks(text)

                if label in structuredAbstract:
                    structuredAbstract[label] = structuredAbstract[label] + " " + text
                else:
                    structuredAbstract[label] = text


        return structuredAbstract

    @classmethod
    def get_text(cls, node):

        # TODO care for structued abstracts https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html#publicationtypelist
        structuredText = {}

        abstractTexts = cls.get_nodes(node, './body')

        for secText in abstractTexts:

            if type(secText) in [etree._Comment, etree._ProcessingInstruction]:
                continue

            secTitle = cls.get_inner_text_from_path(secText, "title")

            if secTitle == None:
                secTitle = secText.attrib.get('id', 'general').upper()

            text = "".join([x for x in secText.itertext()])#atext.text

            allXRefs = [x for x in secText.findall('.//xref')]

            for bad in allXRefs:
                par = bad.getparent()

                if not bad.tail is None:

                    if not bad.getprevious() is None:
                        cls.add_text_to_node(bad.tail, bad.getprevious())
                    else:
                        cls.add_text_to_node(bad.tail, par)

                par.remove(bad)

            allTexts = []
            for x in [secText] + [x for x in secText]:
                if x.text != None and len(x.text) > 0:
                    allTexts.append(x.text)
                if x.tail != None and len(x.tail) > 0:
                    tailStr = x.tail

                    if len(allTexts) > 0 and allTexts[-1] != None:
                        if allTexts[-1][-1] in ("(", "[") and tailStr[0] in (")", "]"):
                            allTexts[-1] = allTexts[-1][:-1]
                            tailStr = tailStr[1:]
                            
                    if len(tailStr) > 0:
                        allTexts.append(tailStr)

            textRem = "".join(allTexts)

            if text != None:
                text = cls.removeLinebreaks(text)
                structuredText[secTitle] = text

        return structuredText

    @classmethod
    def add_text_to_node(cls, text, node):

        if node.tail is None:
            node.tail = text
        else:
            node.tail += text

    @classmethod
    def get_literature(cls, node):

        if node == None:
            return None

        foundNodes = node.findall('back/ref-list//element-citation/pub-id')

        if len(foundNodes) == 0:
            foundNodes = cls.get_nodes_with_attrib(node, 'back/ref-list//ref/*/pub-id', "pub-id-type", "pmid")

        allReturnValues = []

        for subNode in foundNodes:
            PMID = subNode.text

            if PMID != None and PMID != '':
                allReturnValues.append( PMID )

        return allReturnValues

    @classmethod
    def removeLinebreaks(cls, text):

        if text == None or type(text) != str:
            return text

        text = text.replace('\n', ' ').replace('\r', '')
        return text

    @classmethod
    def fromXMLNode(cls, node):

        pmidIDNode = cls.get_node_with_attrib(node, 'front/article-meta/article-id', 'pub-id-type', 'pmid')
        pmcIDNode = cls.get_node_with_attrib(node, 'front/article-meta/article-id', 'pub-id-type', 'pmc')

        pmid = cls.get_value_from_node(pmidIDNode, None)
        pmc = cls.get_value_from_node(pmcIDNode, None)


        #europe pmc
        if pmc is None:
            pmcIDNode = cls.get_node_with_attrib(node, 'front/article-meta/article-id', 'pub-id-type', 'pmcid')
            pmc = cls.get_value_from_node(pmcIDNode, None)

        #print(pmid)
        #print(pmc)


        if pmc == None:
            #raise ValueError("could not find PMC ID")
            print("Could Not Find PMC ID", file=sys.stderr)
            return None

        if not pmc.startswith("PMC"):
            pmc = "PMC{}".format(pmc)

        journal_title = cls.get_inner_text_from_path(node, 'front/journal-meta/journal-title-group/journal-title')
        journal_abbrev_title_node = cls.get_node_with_attrib(node, 'front/journal-meta/journal-id', 'journal-id-type', 'iso-abbrev')
        journal_abbrev_title = cls.get_value_from_node(journal_abbrev_title_node, None)
        journal_doi_node = cls.get_node_with_attrib(node, 'front/article-meta/article-id', 'pub-id-type', 'doi')
        journal_doi = cls.get_value_from_node(journal_doi_node, None)

        #europe pmc
        if journal_title == None:
            journal_title = cls.get_inner_text_from_path(node, 'front/journal-meta/journal-title')
            journal_abbrev_title = journal_title
            journal_doi = cls.get_value_from_node(cls.get_node_with_attrib(node, 'front/article-meta/article-id', 'pub-id-type', 'doi'), None)


        #print(journal_title)
        #print(journal_abbrev_title)
        #print(journal_doi)

        title = cls.get_inner_text_from_path(node, 'front/article-meta/title-group/article-title')
        date_published_node = cls.get_node_with_attrib(node, 'front/article-meta/pub-date', "pub-type", "nihms-submitted")

        if date_published_node == None:
            date_published_node = cls.get_node_with_attrib(node, 'front/article-meta/pub-date', "pub-type", "pmc-release")

        #europe pmc
        if date_published_node == None:
            date_published_node = cls.get_node_with_attrib(node, 'front/article-meta/pub-date', "pub-type", "epub")

        date_day = cls.get_value_from_node(date_published_node, "day", "1")
        date_month = cls.get_value_from_node(date_published_node, "month", "1")
        date_year = cls.get_value_from_node(date_published_node, "year", "1")

        authors = cls._find_authors( node )


        #print(title)
        pubmed = PubmedEntry(pmc)
        pubmed.pmc = pmid
        pubmed.created = (date_year, date_month, date_day)
        pubmed.journal = (journal_title, journal_abbrev_title)

        pubmed.title = cls.removeLinebreaks(title)
        pubmed.doi = journal_doi
        pubmed.authors = authors

        return pubmed

    def add_text(self, node):

        abstract = PubmedEntry.get_abstract(node)
        text = PubmedEntry.get_text(node)

        publicationTypes = node.find('.').attrib.get("article-type", "unknown")
        citedLiterature = PubmedEntry.get_literature(node)

        self.abstract = abstract
        self.sections = text
        self.pub_types = [publicationTypes]
        self.cites = citedLiterature

class PubmedXMLParser:

    def __init__(self):
        self.tree = None

    def remove_namespace(self, tree):
        """
        Strip namespace from parsed XML, assuming there's only one namespace per node
        """
        if tree == None:
            return

        for node in tree.iter():
            try:
                has_namespace = node.tag.startswith('{')
            except AttributeError:
                continue  # node.tag is not a string (node is a comment or similar)
            if has_namespace:
                node.tag = node.tag.split('}', 1)[1]

    def parseXML(self, path):

        self.tree = None

        try:
            self.tree = etree.parse(path)
        except:
            try:
                self.tree = etree.fromstring(path)
            except Exception as e:
                eprint("Unable to load graph:", str(e))
                raise
        if '.nxml' in path:
            self.remove_namespace(self.tree)  # strip namespace for

        return self.tree

class PubmedArticleIterator:

    def __init__(self, parser):
        self.parser = parser

    def __iter__(self):

        if self.parser == None:
            return self

        return self.parser.tree.findall('article').__iter__()

    def __next__(self):
        raise StopIteration()





if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(description='Convert Medline XML to miRExplore base files')
    parser.add_argument('-x', '--xml-path', type=str, required=True, help="path to folder with tar.GZ files.")
    parser.add_argument('-b', '--base', default="pubmed22n", type=str, required=False)
    parser.add_argument('-o', '--output', default="", type=str, required=False)
    parser.add_argument('-t', '--threads', type=int, default=8, required=False)

    parser.add_argument('-s', '--min_sent_length', default=5, type=int, required=False)
    
    parser.add_argument('-m', '--model', type=str, default=None, required=False)
    args = parser.parse_args()
    


    #python3 medlineXMLtoStructurePMC.py --xml-path /mnt/raidtmp/joppich/pubmed_pmc/pmc/ftp.ncbi.nlm.nih.gov/pub/pmc/oa_bulk/oa_comm_extracted/PMC000xxxxxx/ --base "" --threads 6

    # python3 python/textmining/medlineXMLtoStructurePMC.py --xml-path /mnt/input/public/EuroupePMC/oa/ --base "" --output /mnt/raidtmp/joppich/pubmed_pmc/pmc/europepmc/ --threads 30 --zipped

    storagePath = args.xml_path
    baseFileName = args.base

    if storagePath.upper().endswith(".TAR.GZ"):
        suffix = ""
    else:
        suffix = '*.tar.gz'

    searchString = storagePath+baseFileName+suffix
    print("Searching for", searchString)
    allXMLFiles = glob.glob(searchString)
    allXMLFiles = sorted(allXMLFiles)

    print("Found", len(allXMLFiles), "files")
    print("Going through", len(allXMLFiles), " files.")

    print("Loading model", args.model)
      
    nlp = spacy.load(args.model)
    tokenizer = lambda sentTxt: [str(sent).strip() for sent in nlp(sentTxt).sents]

    def senteniceFile(filenames, env):


        for filename in filenames:
            
            print(filename)
            storagePath = os.path.dirname(filename) + "/"
            basefile = os.path.basename(filename)
            print(storagePath, basefile)
            
            file_extension = ".tar.gz"

            sentfile = os.path.join(storagePath, basefile.replace(file_extension, ".sent"))
            titlefile = os.path.join(storagePath, basefile.replace(file_extension, ".title"))
            authorfile = os.path.join(storagePath, basefile.replace(file_extension, ".author"))
            citationfile = os.path.join(storagePath, basefile.replace(file_extension, ".citation"))
            datefile = os.path.join(storagePath, basefile.replace(file_extension, ".date"))
            typefile = os.path.join(storagePath, basefile.replace(file_extension, ".pubtype"))
            pmidfile = os.path.join(storagePath, basefile.replace(file_extension, ".pmid"))
            journalfile = os.path.join(storagePath, basefile.replace(file_extension, ".journal"))


            print(sentfile, titlefile, authorfile, citationfile, datefile, typefile, pmidfile, sep="\n")

            if len(args.output) > 0:

                sentfile = os.path.join(args.output, os.path.basename(sentfile))
                titlefile = os.path.join(args.output, os.path.basename(titlefile))
                authorfile = os.path.join(args.output, os.path.basename(authorfile))
                citationfile = os.path.join(args.output, os.path.basename(citationfile))
                datefile = os.path.join(args.output, os.path.basename(datefile))
                typefile = os.path.join(args.output, os.path.basename(typefile))
                pmidfile = os.path.join(args.output, os.path.basename(pmidfile))
                journalfile = os.path.join(args.output, os.path.basename(journalfile))


            print(filename, basefile, sentfile)

            tar_file = tarfile.open(filename)

            pmid2title = {}
            pmid2authors = defaultdict(set)
            pmid2citations = defaultdict(set)

            with open(sentfile, 'w') as outfile, open(datefile, 'w') as outdate, open(journalfile, 'w') as outjournal, open(typefile, "w") as outtype, open(pmidfile, "w") as outpmid, open(titlefile, 'w') as outtitle, open(authorfile, 'w') as outauthor, open(citationfile, 'w') as outcitation:
                


                
                for tarmember in tar_file.getmembers():
                    
                    xmlFile = tar_file.extractfile(tarmember)

                    pubmedParser = PubmedXMLParser()
                    pubmedParser.parseXML(xmlFile)
                    elemIt = [pubmedParser.tree]

                    for eidx, ielem in enumerate(elemIt):

                        #print(ofilename, eidx)

                        elem = deepcopy(ielem)

                        try:
                            
                            entry = PubmedEntry.fromXMLNode(elem)

                            if entry is None:
                                print("Empty entry", filename)
                                continue


                            entry.add_text(elem)
                            sents = entry.to_sentences(tokenizer)

                            for x in sents:
                                outfile.write(x + "\n")

                            pmidID = entry.getID()
                            pmidID = pmidID.replace("\t", "").replace("\n", "")

                            if entry.created != None:
                                
                                print(pmidID, "\t".join([str(x).replace("\t", "").replace("\n", "") for x in entry.created]), sep="\t", file=outdate)

                            if entry.pub_types != None:
                                for ept in entry.pub_types:
                                    print(pmidID, ept, sep="\t", file=outtype)

                            if entry.pmc != None:
                                print(pmidID, entry.pmc, sep="\t", file=outpmid)

                            if entry.title != None:
                                print(str(pmidID), str(entry.title), sep="\t", file=outtitle)
                                
                            if entry.journal != None:
                                print(str(pmidID), str(entry.journal[0]), str(entry.journal[1]), sep="\t", file=outjournal)

                            if entry.authors != None and len(entry.authors) > 0:
                                
                                for author in entry.authors:

                                    first = author[1] if author[1] != None else ''
                                    initials = author[2] if author[2] != None else ''
                                    last = author[0] if author[0] != None else ''
                                    
                                    first = first.replace("\t", " ").replace("\n", " ")
                                    initials = initials.replace("\t", " ").replace("\n", " ")
                                    last = last.replace("\t", " ").replace("\n", " ")

                                    print(str(pmidID), first, initials, last, sep="\t", file=outauthor)


                            if entry.cites != None and len(entry.cites) > 0:
                                for cite in entry.cites:
                                    cite = cite.replace("\t", "").replace("\n", "")
                                    print(str(pmidID) , str(cite), sep="\t", file=outcitation)

                        except:

                            eprint("Exception", sentfile)
                            
                            #continue
                            entry = PubmedEntry.fromXMLNode(elem)
                            entry.add_text(elem)
                            #exit(-1)
                            try:

                                pmid = PubmedEntry.fromXMLNode(elem)
                                eprint(pmid)

                            except:
                                pass

                            continue
                        
                    outfile.flush()
                    outdate.flush()
                    outtype.flush()
                    outpmid.flush()
                    outtitle.flush()
                    outauthor.flush()
                    outcitation.flush()

                

    if args.threads == 1:
        for x in allXMLFiles:
            senteniceFile([x], None)

    else:
        ll = MapReduce(args.threads)
        result = ll.exec( allXMLFiles, senteniceFile, None, 1, None)

    print("Done")
