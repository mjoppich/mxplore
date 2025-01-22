
import argparse
import os,sys
import io
import glob
from collections import defaultdict, Counter
import shutil


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-s', '--sentfile', type=argparse.FileType('r'), required=True, help='alignment files')
    parser.add_argument('-o', '--outprefix', type=str, required=False, help='alignment files')
    parser.add_argument('-m', '--movepath', type=str, required=True, help='alignment files')
    parser.add_argument('-n', '--maxdocs', type=int, default=10000, help='alignment files')
    args = parser.parse_args()
    
    print(args.sentfile.name)

    if not os.path.isdir(args.movepath):
        raise argparse.ArgumentTypeError("movepath must be valid dir!")


    
    sentDir = os.path.dirname(args.sentfile.name)
    if sentDir == "":
        sentDir = "."
    sentName = os.path.splitext(os.path.basename(args.sentfile.name))[0]
        
    sentprefix = os.path.join(sentDir, sentName)
    
    relFiles = [x for x in glob.glob("{}*".format(sentprefix)) if not x.endswith(".tar.gz")]
    print(relFiles)
    
    if args.outprefix is None:
        args.outprefix = "chunked"
        


    doc2chunks = {}
    currentChunk = 0
    currentChunkSet = set()
    

    # FIRST PATH: SENTENCE FILE!
    
    sentFiles = [x for x in relFiles if x.endswith(".sent")]
    assert(len(sentFiles) == 1)
    sentFile = sentFiles[0]
            

    with open(sentFile, "rb") as sentFileIn:
        
        relOutFile = "{}/{}_{}_{}.{}".format(sentDir, args.outprefix, currentChunk, sentName, "sent")    
        print(sentFile, "-->", relOutFile)
        
        fout = open(relOutFile, "wb")
        
        for line in sentFileIn:
            aline = line.decode(errors="ignore").split("\t")
            
            docID = aline[0].split(".")[0]
            
            if not docID.startswith("PMC"):
                print("Non-PMC-line")
                print(line)
                continue
            
            currentChunkSet.add(docID)
            
            if len(currentChunkSet) > args.maxdocs:
                
                fout.flush()
                fout.close()
                
                currentChunkSet = set([docID])
                currentChunk += 1
                                                
                relOutFile = "{}/{}_{}_{}.{}".format(sentDir, args.outprefix, currentChunk, sentName, "sent")    
                print(sentFile, "-->", relOutFile)
                
                fout = open(relOutFile, "wb")

            fout.write(line)
            doc2chunks[docID] = currentChunk
                    
        fout.flush()
        fout.close()
        
    chunk2docID = defaultdict(set)
    for doc in doc2chunks:
        chunk2docID[doc2chunks[doc]].add(doc)
        
    for chunkID in chunk2docID:
        print("Chunk", chunkID, ":", len(chunk2docID[chunkID]))
        

    remainingFiles = [x for x in relFiles if not x.endswith(".sent")]
    
    for remFile in remainingFiles:
        
        rembase, remExt = os.path.splitext(remFile)
        print(remFile, remExt)
        
        chunkFiles = dict()
        for chunkID in chunk2docID:
            
            relOutFile = "{}/{}_{}_{}.{}".format(sentDir, args.outprefix, chunkID, sentName, remExt[1:])    
            print(remFile, "-->", relOutFile)
            
            fout = open(relOutFile, "w")
            chunkFiles[chunkID] = fout
        
        chunk2adds = Counter()
        with open(remFile, "r") as remFileIn:
            
            for line in remFileIn:
                aline = line.split("\t")
                
                if not line.startswith("PMC"):
                    print("Non-PMC-line")
                    print(line)
                    continue
                
                docID = aline[0].split(".")[0]
                
                if docID == "":
                    continue
                
                if not docID in doc2chunks:
                    print("Missing docID!!!", docID)
                    print(line)
                    print(aline)
                    continue
                
                docChunk = doc2chunks[docID]
                fout = chunkFiles[docChunk]
                
                chunk2adds[docChunk] += 1

                fout.write(line)
                doc2chunks[docID] = currentChunk
            
            
        for chunkID in chunkFiles:
            fout = chunkFiles[chunkID]
            fout.flush()
            fout.close()
        
        print(chunk2adds)

    for relFile in relFiles:
        baseName = os.path.basename(relFile)
        newName = os.path.join(args.movepath, baseName)
        print(relFile, "-->", newName)
        shutil.move(relFile, newName)

        