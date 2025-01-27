import os, sys

sys.path.insert(0, str(os.path.dirname(os.path.realpath(__file__))) + "/../")

from urllib import request
from urllib.error import URLError

from utils.parallel import MapReduce

downloadBase = True
downloadUpdates = False
downloadUpdatesParallel = False


# ADAPT the start/end to be last file on FTP-server + 1
updateStart = 1220
updateEnd = 1220

# ADAPT the baseline string to match the pattern on the FTP server.
medlineBase="pubmed24n"
baseEnd = updateStart-1

# ADAPT THIS LOCATION
downloadLocation = "/mnt/extproj/projekte/textmining/pubmed_feb24/"

# ADAPT THIS LOCATION if necessary
FTPURL="ftp://ftp.ncbi.nlm.nih.gov/pubmed/baseline/"

directory = os.path.dirname(downloadLocation)
if not os.path.exists(directory):
    os.makedirs(directory)

onlyNew = False

def downloadDataBase(data, env):

    for i in data:

        fileID = "{:>4}".format(i).replace(" ", "0")
        downloadFile = medlineBase+fileID+".xml.gz"
        print(downloadFile)

        if onlyNew:
            if os.path.exists(downloadLocation + "/" + downloadFile):
                continue

        request.urlretrieve(FTPURL+downloadFile, downloadLocation + "/" + downloadFile)

def downloadDataUpdate(data, env):

    for i in data:

        fileID = "{:>4}".format(i).replace(" ", "0")
        downloadFile = medlineBase+fileID+".xml.gz"
        print(downloadFile)

        if onlyNew:
            if os.path.exists(downloadLocation + "/" + downloadFile):
                continue

        request.urlretrieve("ftp://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/"+downloadFile, downloadLocation + "/" + downloadFile)

if downloadBase:

    ll = MapReduce(14)
    ll.exec([i for i in range(1,baseEnd)], downloadDataBase, None)

if downloadUpdatesParallel:

    ll = MapReduce(8)
    ll.exec([i for i in range(updateStart, updateEnd)], downloadDataUpdate, None)


if downloadUpdates:

    for i in range(updateStart, 10000):
        fileID = "{:>4}".format(i).replace(" ", "0")
        downloadFile = medlineBase + fileID + ".xml.gz"
        print(downloadFile)

        try:
            (url, resp) = request.urlretrieve("ftp://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/" + downloadFile,
                                downloadLocation + "/" + downloadFile)
        except URLError as e:
            print(downloadFile, "not existing")
            break
