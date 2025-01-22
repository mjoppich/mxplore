from flask import Flask, render_template, request, send_file, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, MetaData, select, and_, or_
from sqlalchemy.orm import load_only

import os, sys
from natsort import natsorted
import datetime
from collections import Counter, defaultdict
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pickle
import copy

from io import BytesIO

app = Flask(__name__, static_url_path="/static/", static_folder='/mnt/extproj/projekte/textmining/mxplore/mx_frontend/static/')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cons_evidences.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True

from collections import Counter

mx_base = "/mnt/extproj/projekte/textmining/mxplore/"
mx_python = f"{mx_base}/python/textmine/"
oboFolder = f"{mx_base}/obodir/"

sys.path.insert(0, mx_python)
from mxutils.GeneOntology import GeneOntology


infodict2obo = {}
infodict2obo["celllines"] = GeneOntology(oboFolder + "/cell_ontology.obo")
infodict2obo["disease"] = GeneOntology(oboFolder + "/doid.obo")
infodict2obo["GeneOntology"] = GeneOntology(oboFolder + "/go.obo")



with open(f"{mx_base}/mx_frontend/hg19_mirna_annotation.pickle", "rb") as fout:
    allMirnaAnnotsHG19 = pickle.load(fout)

with open(f"{mx_base}/mx_frontend/hg19_gene_annotation.pickle", "rb") as fout:
    allGeneAnnotsHG19 = pickle.load(fout)
    
with open(f"{mx_base}/mx_frontend/mm10_mirna_annotation.pickle", "rb") as fout:
    allMirnaAnnotsMM10 = pickle.load(fout)

with open(f"{mx_base}/mx_frontend/mm10_gene_annotation.pickle", "rb") as fout:
    allGeneAnnotsMM10 = pickle.load(fout)


db = SQLAlchemy(app)

with app.app_context():
    db.Model.metadata.reflect(bind=db.engine)
    #print(db.Model.metadata.tables)

"""

CREATE TABLE "mx" (
    "index" INTEGER PRIMARY KEY AUTOINCREMENT,
    "miRNA_family" TEXT,
    "gene_family" TEXT,
    "interaction" TEXT,
    "organisms" TEXT,
    "evidence_documents" TEXT,
    "sent_evidences" TEXT,
    "evidence_count" INTEGER,
    "sent_count" INTEGER,
    "is_consensus" INTEGER
    )

"""
import json

class Sentences(db.Model):
    __table__ = db.Model.metadata.tables['mx_sent']
    
    def to_dict(self):
        return {
            'doc_id': self.doc_id,
            'sent_id': self.sent_id,
            'sentence': self.sentence
        }


class Interactions(db.Model):
    __table__ = db.Model.metadata.tables['mx_int']
    

    def to_dict(self):
        return {
            'miRNA_family': self.miRNA_family,
            'gene_family': self.gene_family,
            'interaction': self.interaction,
            "evidence_document": self.evidence_documents
        }

class Annotations(db.Model):
    __table__ = db.Model.metadata.tables['mx_annot']

    def to_dict(self):
        return {
            'doc_id': self.doc_id,
            'annotation': self.annotation,
            'concept_id': self.concept_id,
            'concept': self.concept,
            'sent_evidences': self.sent_evidences,
        }


class MXRelations(db.Model):
    __table__ = db.Model.metadata.tables['mx']

    #index = db.Column(db.Integer, index=True, primary_key=True)
    #miRNA_family = db.Column(db.TEXT)
    #miRNA_family = db.Column(db.TEXT)
    #interaction = db.Column(db.TEXT)
    #organisms = db.Column(db.TEXT)
    #evidence_count = db.Column(db.TEXT)
    #is_consensus = db.Column(db.TEXT)
    
    def to_dict(self):
        return {
            'miRNA_family': self.miRNA_family,
            'gene_family': self.gene_family,
            'interaction': self.interaction,
            'organisms': self.organisms,
            'evidence_count': self.evidence_count,
            'is_consensus': self.is_consensus,
            'details': "<a href='{}/{}/{}'>Details</a>".format(self.miRNA_family, self.gene_family, self.interaction)
        }
        
    def to_details(self):
        return {
            'miRNA_family': self.miRNA_family,
            'gene_family': self.gene_family,
            'interaction': self.interaction,
            'organisms': self.organisms,
            'evidence_count': self.evidence_count,
            'is_consensus': self.is_consensus,
            "evidence_documents": self.evidence_documents,
            "sent_evidences": self.sent_evidences
        }

db.create_all()

hostFolder = "mxplore"

@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

@app.route('/')
def index():
    return render_template('server_home.html', title='mx-plore', host=hostFolder)

@app.route('/database')
def database():
    return render_template('server_table.html', title='mx-plore', host=hostFolder)

@app.route('/help')
def help():
    return render_template('server_help.html', title='mx-plore', host=hostFolder)

@app.route('/download')
def download():
    return render_template('server_download.html', title='mx-plore', host=hostFolder)

@app.route('/impress')
def impress():
    return render_template('server_impress.html', title='mx-plore', host=hostFolder)

@app.route("/annotations/gene",methods = ['GET']) #?gene=ABCA1&mirna=let-7a
def annotations():
    gene = request.args.get('gene')
    mirna = request.args.get('mirna')
    organism = request.args.get('organism')
    
    print("annotations", gene, mirna,organism)
    
    #with open("/mnt/extproj/projekte/textmining/mx_frontend/templates/test_json.json") as f:
    #    jsonData = json.load(f)
        
    if "hsa" in organism:
        # anything with human
        geneAnnot = copy.deepcopy(allGeneAnnotsHG19.get(gene, {}))
        mirAnnot = copy.deepcopy(allMirnaAnnotsHG19.get(gene, {}).get(mirna, {}))
    else:
        #mouse
        geneAnnot = copy.deepcopy(allGeneAnnotsMM10.get(gene, {}))
        mirAnnot = copy.deepcopy(allMirnaAnnotsMM10.get(gene, {}).get(mirna, {}))
    
    if len(geneAnnot) > 0 and len(mirAnnot) > 0:
        geneAnnot["tracks"].append(mirAnnot)
    
    print(os.getcwd())
    response = app.response_class(response=json.dumps(geneAnnot),
                                  status=200,
                                  mimetype='application/json')
    return response


#@app.route('/static/<path>')
#def static_file(path):  
#    return app.send_static_file(os.path.join("static", path))


@app.route('/file_downloads/<fname>') 
def file_downloads(fname):
    
    dfile = None
    if fname == "sqlite":
        dfile = "/mnt/extproj/projekte/textmining/mx_frontend/cons_evidences.db"
    elif fname == "mxtable":
        dfile = "/mnt/extproj/projekte/textmining/mx_frontend/mxplore_table_mx.tsv"
        
        
    if dfile is None:
        return redirect('/404')
        
    return send_file(dfile, as_attachment=True)


def extract_sentences( sent_evidences ):
    
    sents = sent_evidences.split(";")
    
    retList = []
    for x in sents:
        sentdata = eval(x)
        sentid = sentdata[0]
        loc1 = sentdata[1]
        loc2 = sentdata[2]
        
        retList.append({"sentid": sentid, "docid": sentid.split(".")[0], "loc1": loc1, "loc2": loc2})
    
    return retList

def make_url( docid ):
    if docid.startswith("PMC"):
        return "https://www.ncbi.nlm.nih.gov/pmc/articles/{}/".format(docid)
    else:
        return "https://pubmed.ncbi.nlm.nih.gov/{}/".format(docid)

def make_link( docid ):
    
    return "<a href='{}'>{}</a>".format(make_url(docid), docid)
    
    if docid.startswith("PMC"):
        return "<a href='https://www.ncbi.nlm.nih.gov/pmc/articles/{}/'>{}</a>".format(docid, docid)
    else:
        return "<a href='https://pubmed.ncbi.nlm.nih.gov/{}/'>{}</a>".format(docid, docid)
        
def make_source( docid ):
    if docid.startswith("PMC"):
        return "<img height='50px' style='background-color: gray;' src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNzAuMzUgNTMuNDMiPjxkZWZzPjxjbGlwUGF0aCBpZD0iY2xpcC1wYXRoIiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgtLjczKSI+PHBhdGggZmlsbD0ibm9uZSIgZD0iTTAgMGgyNzEuODF2NTMuNDNIMHoiLz48L2NsaXBQYXRoPjxzdHlsZT4uY2xzLTN7ZmlsbDojZmZmfTwvc3R5bGU+PC9kZWZzPjxnIGlkPSJMYXllcl8yIiBkYXRhLW5hbWU9IkxheWVyIDIiPjxnIGNsaXAtcGF0aD0idXJsKCNjbGlwLXBhdGgpIiBpZD0iTGF5ZXJfMS0yIiBkYXRhLW5hbWU9IkxheWVyIDEiPjxwYXRoIGNsYXNzPSJjbHMtMyIgZD0iTTguMTkgNDUuNTR2LTIwaDcuMzVhMTMuNzMgMTMuNzMgMCAwMTMuMDguMzIgNi43NyA2Ljc3IDAgMDEyLjQ5IDEuMDcgNS4yNyA1LjI3IDAgMDExLjY5IDIgNi44NSA2Ljg1IDAgMDEuNjIgMy4wNSA2Ljg1IDYuODUgMCAwMS0uNjQgMyA1LjgxIDUuODEgMCAwMS0xLjcyIDIuMSA3LjIgNy4yIDAgMDEtMi41IDEuMjIgMTEuMDYgMTEuMDYgMCAwMS0zIC40aC0yLjg1djYuODR6bTQuNTItMTAuMzhoMi41MnEzLjY4IDAgMy42Ny0zLjE5YTIuNTggMi41OCAwIDAwLS45LTIuMjYgNC43MiA0LjcyIDAgMDAtMi43NC0uNjVoLTIuNTV6TTI1LjkxIDQ1LjU0di0yMGg1LjE2bDMuMzQgOSAxLjIgMy41aC4xMmwxLjE5LTMuNSAzLjI1LTloNS4wN3YyMGgtNC41MVYzOC4ycTAtLjczLjA2LTEuNjJjLjA1LS42LjEtMS4yLjE3LTEuOHMuMTQtMS4yLjItMS43OS4xMy0xLjEyLjItMS42MWgtLjEzTDM5LjU1IDM2bC0zLjA3IDcuNzdoLTEuODJMMzEuNTcgMzYgMzAgMzEuMzhoLS4xNWMuMDcuNDkuMTMgMSAuMiAxLjYxcy4xNCAxLjE4LjE5IDEuNzkuMTEgMS4yLjE1IDEuNzkuMDcgMS4xMy4wNyAxLjYzdjcuMzR6TTQ4LjE0IDM1LjY2YTExLjg4IDExLjg4IDAgMDEuNzctNC40NEExMC4xOCAxMC4xOCAwIDAxNTEgMjcuOTFhOC43MiA4LjcyIDAgMDEzLTIuMDYgOS42NyA5LjY3IDAgMDEzLjY3LS43MSA3LjI1IDcuMjUgMCAwMTMuNC43OSA5Ljg2IDkuODYgMCAwMTIuNTIgMS44M2wtMi40NyAyLjgxYTcuMjEgNy4yMSAwIDAwLTEuNTUtMS4xMSA0IDQgMCAwMC0xLjg0LS40IDQuNDMgNC40MyAwIDAwLTIgLjQ0IDQuODMgNC44MyAwIDAwLTEuNTggMS4yOCA2LjE0IDYuMTQgMCAwMC0xLjA2IDIgOC43MSA4LjcxIDAgMDAtLjM5IDIuNyA3LjYzIDcuNjMgMCAwMDEuMzMgNC44IDQuMjUgNC4yNSAwIDAwMy42IDEuNzIgNC40NiA0LjQ2IDAgMDAyLjE1LS40OSA2IDYgMCAwMDEuNjYtMS4yOEw2My45MyA0M2E4LjQ5IDguNDkgMCAwMS0yLjg3IDIuMjEgOC4zNCA4LjM0IDAgMDEtMy40OS43NCAxMC4wNiAxMC4wNiAwIDAxLTMuNjUtLjY2IDguNSA4LjUgMCAwMS0zLTIgOS4yMiA5LjIyIDAgMDEtMi0zLjIxIDEyLjA2IDEyLjA2IDAgMDEtLjc4LTQuNDJ6IiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgtLjczKSIvPjxwYXRoIGNsYXNzPSJjbHMtMyIgZD0iTTAgMTQuNjJoNjkuMzlMMzUuNzQgMCAwIDE0LjYyek0wIDE2LjgyaDY5LjM5djMuMTNIMHpNMCA1MC4zaDY5LjM5djMuMTNIMHoiLz48cGF0aCBjbGFzcz0iY2xzLTMiIGQ9Ik03OCAzNy4xNlY0NGgtMy4yNVYyNS41M2g3LjA3YTcuMiA3LjIgMCAwMTQuOTIgMS42MSA1LjQ1IDUuNDUgMCAwMTEuODIgNC4yNyA1LjI2IDUuMjYgMCAwMS0xLjc5IDQuMjQgNy40NiA3LjQ2IDAgMDEtNSAxLjUxem0wLTIuNTloMy44NmEzLjc4IDMuNzggMCAwMDIuNjEtLjgxIDMgMyAwIDAwLjktMi4zMyAzLjE5IDMuMTkgMCAwMC0uOTUtMi40MyAzLjUyIDMuNTIgMCAwMC0yLjUxLS45Mkg3OHpNOTkuMzkgNDIuNjdhNC43OCA0Ljc4IDAgMDEtMy44NiAxLjZBNC4yOSA0LjI5IDAgMDE5Mi4xNCA0MyA1LjU4IDUuNTggMCAwMTkxIDM5LjE4di04LjloMy4wOHY4Ljg2YzAgMS43NC43MiAyLjYxIDIuMTcgMi42MWEzLjA1IDMuMDUgMCAwMDMtMS42MXYtOS44NmgzLjA4VjQ0aC0yLjg3ek0xMTcuNTcgMzcuMjlhOC4yNyA4LjI3IDAgMDEtMS40MyA1LjA5IDQuNjUgNC42NSAwIDAxLTMuOTMgMS44OSA0LjQ5IDQuNDkgMCAwMS0zLjc2LTEuNzRMMTA4LjMgNDRoLTIuNzlWMjQuNTFoMy4wOHY3LjA5YTQuNDcgNC40NyAwIDAxMy41OS0xLjYgNC43MSA0LjcxIDAgMDEzLjk1IDEuODcgOC4zNSA4LjM1IDAgMDExLjQ0IDUuMjJ6bS0zLjA5LS4yOWE1Ljg2IDUuODYgMCAwMC0uNzgtMy4zNSAyLjYyIDIuNjIgMCAwMC0yLjI5LTEuMTIgMi44NiAyLjg2IDAgMDAtMi44MiAxLjc1VjQwYTIuODkgMi44OSAwIDAwMi44NSAxLjc5IDIuNiAyLjYgMCAwMDIuMjMtMS4wNyA1LjY1IDUuNjUgMCAwMC44MS0zLjI3ek0xMjQuNjEgMjUuNTNMMTMwIDM5LjdsNS4zMS0xNC4xN2g0LjE2VjQ0aC0zLjJ2LTYuMDhsLjMxLTguMTUtNS41IDE0LjIzaC0yLjNsLTUuNDUtMTQuMjMuMzIgOC4xNFY0NGgtMy4yVjI1LjUzek0xNDkgNDQuMjdhNi4zOCA2LjM4IDAgMDEtNC43NS0xLjg1IDYuNjcgNi42NyAwIDAxLTEuODItNC45MnYtLjM4YTguMTggOC4xOCAwIDAxLjc5LTMuNjcgNiA2IDAgMDEyLjIzLTIuNTIgNS44IDUuOCAwIDAxMy4yLS45MSA1LjM5IDUuMzkgMCAwMTQuMzMgMS43OSA3LjYgNy42IDAgMDExLjUzIDUuMDd2MS4yNGgtOWE0LjE0IDQuMTQgMCAwMDEuMTMgMi43IDMuNDIgMy40MiAwIDAwMi41MSAxIDQuMTggNC4xOCAwIDAwMy40NS0xLjcybDEuNjcgMS41OWE1LjU1IDUuNTUgMCAwMS0yLjIxIDEuOTEgNi44OCA2Ljg4IDAgMDEtMy4wNi42N3ptLS4zNy0xMS43N2EyLjYzIDIuNjMgMCAwMC0yLjA1Ljg5IDQuNTggNC41OCAwIDAwLTEgMi40N2g1Ljg4di0uMjJhMy43OSAzLjc5IDAgMDAtLjgzLTIuMzUgMi41NyAyLjU3IDAgMDAtMi4wNC0uNzl6TTE1Ni4yOSAzN2E4LjE2IDguMTYgMCAwMTEuNDctNSA0LjczIDQuNzMgMCAwMTQtMS45MyA0LjQ3IDQuNDcgMCAwMTMuNTMgMS41M3YtN2gzLjA4VjQ0aC0yLjc5bC0uMTUtMS40MmE0LjU1IDQuNTUgMCAwMS0zLjcgMS42OCA0LjcgNC43IDAgMDEtMy45LTEuOTQgOC41MiA4LjUyIDAgMDEtMS41NC01LjMyem0zLjA4LjI3YTUuNjkgNS42OSAwIDAwLjgxIDMuMjcgMi42MiAyLjYyIDAgMDAyLjI5IDEuMTcgMi45MyAyLjkzIDAgMDAyLjc3LTEuNjhWMzQuMmEyLjg3IDIuODcgMCAwMC0yLjc0LTEuNjUgMi42NCAyLjY0IDAgMDAtMi4zMSAxLjE5IDYuMjggNi4yOCAwIDAwLS44MiAzLjU3ek0xOTIuNDIgMzhhNi43MSA2LjcxIDAgMDEtMi4xOCA0LjYxIDcuNDMgNy40MyAwIDAxLTUuMDcgMS42NiA3LjE5IDcuMTkgMCAwMS0zLjg5LTEuMDUgNi44OSA2Ljg5IDAgMDEtMi42LTMgMTAuNzggMTAuNzggMCAwMS0xLTQuNDhWMzRhMTAuNzggMTAuNzggMCAwMS45My00LjYxIDYuOTEgNi45MSAwIDAxMi42Ni0zLjA3IDcuMzkgNy4zOSAwIDAxNC0xLjA4IDcuMTggNy4xOCAwIDAxNC45MyAxLjY1IDYuOTQgNi45NCAwIDAxMi4xNyA0LjY5aC0zLjJhNC41NyA0LjU3IDAgMDAtMS4xNi0yLjg3IDMuODQgMy44NCAwIDAwLTIuNzQtLjg4IDMuNzYgMy43NiAwIDAwLTMuMjIgMS41MyA3LjY3IDcuNjcgMCAwMC0xLjA1IDQuNTN2MS42NGE4LjA2IDguMDYgMCAwMDEgNC41NyAzLjU1IDMuNTUgMCAwMDMuMTQgMS41OCA0LjEyIDQuMTIgMCAwMDIuODQtLjg1IDQuNDIgNC40MiAwIDAwMS4yNC0yLjgzek0yMDEgNDQuMjdhNi40IDYuNCAwIDAxLTQuNzYtMS44NSA2LjcxIDYuNzEgMCAwMS0xLjgyLTQuOTJ2LS4zOGE4LjE4IDguMTggMCAwMS44LTMuNjcgNi4wNiA2LjA2IDAgMDEyLjIyLTIuNTIgNS44NSA1Ljg1IDAgMDEzLjItLjkxIDUuNDEgNS40MSAwIDAxNC4zNiAxLjc5IDcuNiA3LjYgMCAwMTEuNTMgNS4wN3YxLjI0aC05YTQuMTQgNC4xNCAwIDAwMS4xNCAyLjcgMy40MSAzLjQxIDAgMDAyLjUxIDEgNC4xOSA0LjE5IDAgMDAzLjQ1LTEuNzJsMS42NiAxLjU5YTUuNTIgNS41MiAwIDAxLTIuMiAxLjkxIDYuOTQgNi45NCAwIDAxLTMuMDkuNjd6bS0uMzctMTEuNzdhMi42IDIuNiAwIDAwLTIgLjg5IDQuNjYgNC42NiAwIDAwLTEgMi40N2g1Ljg4di0uMjJhMy43OSAzLjc5IDAgMDAtLjgyLTIuMzUgMi41OSAyLjU5IDAgMDAtMi4wMi0uNzl6TTIxMS44IDMwLjI4bC4wOSAxLjU4YTUgNSAwIDAxNC0xLjg0cTQuMjkgMCA0LjM3IDQuOTJWNDRoLTMuMDl2LTguOWEyLjggMi44IDAgMDAtLjU2LTEuOTMgMi4zOCAyLjM4IDAgMDAtMS44NS0uNjMgMyAzIDAgMDAtMi43NiAxLjdWNDRoLTMuMVYzMC4yOHpNMjI3LjI3IDI2Ljk0djMuMzRoMi40MnYyLjI4aC0yLjQydjcuNjdhMS42OSAxLjY5IDAgMDAuMzEgMS4xNCAxLjQ2IDEuNDYgMCAwMDEuMTEuMzUgNS4xMyA1LjEzIDAgMDAxLjA4LS4xM1Y0NGE3Ljc3IDcuNzcgMCAwMS0yIC4yOXEtMy41NiAwLTMuNTYtMy45MnYtNy44MWgtMi4yNnYtMi4yOGgyLjI2di0zLjM0ek0yMzkuMjQgMzMuMUE3LjQ3IDcuNDcgMCAwMDIzOCAzM2EyLjgzIDIuODMgMCAwMC0yLjg1IDEuNjNWNDRIMjMyVjMwLjI4aDNsLjA3IDEuNTNhMy40OSAzLjQ5IDAgMDEzLjEtMS43OSAyLjg1IDIuODUgMCAwMTEuMDkuMTh6TTI0OSA0NGE0LjkzIDQuOTMgMCAwMS0uMzUtMS4yOCA0Ljc4IDQuNzggMCAwMS0zLjYxIDEuNTQgNC44NiA0Ljg2IDAgMDEtMy4zNy0xLjE4IDMuNzYgMy43NiAwIDAxLTEuMzEtMi45MkEzLjg4IDMuODggMCAwMTI0MiAzNi44YTcuODYgNy44NiAwIDAxNC42Ny0xLjE4aDEuODl2LS45YTIuMTYgMi4xNiAwIDAwLTIuNDEtMi4zNSAyLjcyIDIuNzIgMCAwMC0xLjczLjUzIDEuNjMgMS42MyAwIDAwLS42NyAxLjM0aC0zLjA5YTMuNDEgMy40MSAwIDAxLjc1LTIuMTEgNSA1IDAgMDEyLTEuNTUgNy4yIDcuMiAwIDAxMi44Ny0uNTYgNS43NyA1Ljc3IDAgMDEzLjg1IDEuMjIgNC4yOCA0LjI4IDAgMDExLjQ3IDMuNDF2Ni4xOWE3LjE0IDcuMTQgMCAwMC41MiAzVjQ0em0tMy4zOS0yLjIyYTMuNjIgMy42MiAwIDAwMS43My0uNDQgMy4wOCAzLjA4IDAgMDAxLjIxLTEuMTl2LTIuNThoLTEuNjdhNC41IDQuNSAwIDAwLTIuNTcuNTkgMS45MyAxLjkzIDAgMDAtLjg3IDEuNjkgMS44NCAxLjg0IDAgMDAuNTkgMS40MiAyLjMgMi4zIDAgMDAxLjU5LjUyek0yNTguMTYgNDRoLTMuMDlWMjQuNTFoMy4wOXpNMjYwLjU4IDMwYTUuNzUgNS43NSAwIDAxLjY5LTIuNzcgNS4xMiA1LjEyIDAgMDExLjkyLTIgNS4wOCA1LjA4IDAgMDE1LjI4IDAgNS4xMiA1LjEyIDAgMDExLjkyIDIgNS45MyA1LjkzIDAgMDEwIDUuNTUgNS4yMyA1LjIzIDAgMDEtMS45MSAyIDQuOTQgNC45NCAwIDAxLTIuNjUuNzUgNSA1IDAgMDEtMi42NC0uNzQgNS4yOCA1LjI4IDAgMDEtMS45Mi0yIDUuNzYgNS43NiAwIDAxLS42OS0yLjc5em05LjYgMGE0LjgxIDQuODEgMCAwMC0uNTYtMi4yOCA0LjI2IDQuMjYgMCAwMC0xLjU3LTEuNzIgNC4xIDQuMSAwIDAwLTIuMjItLjYzIDQuMjUgNC4yNSAwIDAwLTIuMTkuNiA0LjMzIDQuMzMgMCAwMC0xLjU4IDEuNjggNC43MyA0LjczIDAgMDAtLjU4IDIuMzIgNC44MyA0LjgzIDAgMDAuNTcgMi4zMiA0LjM2IDQuMzYgMCAwMDEuNTkgMS43MSA0LjE3IDQuMTcgMCAwMDQuMzYgMCA0LjI4IDQuMjggMCAwMDEuNTgtMS42OSA0LjgxIDQuODEgMCAwMC42LTIuMzF6bS01LjQxLjU2VjMzaC0xLjEydi02LjI3aDIuMDhhMi43OCAyLjc4IDAgMDExLjc3LjUgMS43IDEuNyAwIDAxLjYzIDEuNDIgMS40NCAxLjQ0IDAgMDEtLjg4IDEuMzMgMS4zMyAxLjMzIDAgMDEuNjcuNjMgMi4zMyAyLjMzIDAgMDEuMTkgMSA4LjMzIDguMzMgMCAwMDAgLjg2IDEuMTggMS4xOCAwIDAwLjEuNDJWMzNoLTEuMTVhNi4wOSA2LjA5IDAgMDEtLjEtMS40NCAxLjE1IDEuMTUgMCAwMC0uMjQtLjgxIDEuMTIgMS4xMiAwIDAwLS44MS0uMjV6bTAtMWgxLjA1YTEuNDUgMS40NSAwIDAwLjg2LS4yMy43MS43MSAwIDAwLjM0LS42My44OC44OCAwIDAwLS4yNi0uNzMgMS41NiAxLjU2IDAgMDAtLjk1LS4yM2gtMXoiIHRyYW5zZm9ybT0idHJhbnNsYXRlKC0uNzMpIi8+PC9nPjwvZz48L3N2Zz4='/>"
    else:
        return "<img height='50px' src='https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/US-NLM-PubMed-Logo.svg/320px-US-NLM-PubMed-Logo.svg.png'/>"        

def to_consensus_string(input):
    if input == 1:
        return "yes"
    return "no"


@app.route('/<mirna>/<gene>/<interaction>') 
def details(mirna, gene, interaction):
    query = MXRelations.query.filter(db.and_(MXRelations.miRNA_family == mirna, MXRelations.gene_family == gene, MXRelations.interaction == interaction))
    
    sendData = [user.to_details() for user in query]
    organisms = [x["organisms"] for x in sendData]
    evidences = [x["evidence_count"] for x in sendData]
    consensus = [to_consensus_string(x["is_consensus"]) for x in sendData]
    
    
    
    evidence_docs = set()
    for x in sendData:
        evidence_docs.update(x["evidence_documents"].split(";"))

    requiredSents = set()
    printLocations = []
    for x in sendData:
        for y in extract_sentences(x["sent_evidences"]):
            requiredSents.add(y["sentid"])  
            printLocations.append(y)
    
    sentData = [x.to_dict() for x in Sentences.query.filter(Sentences.sent_id.in_(requiredSents))]
    sentid2sent = {x["sent_id"]: x["sentence"] for x in sentData}
    
    annotData = [x.to_dict() for x in Annotations.query.filter(Annotations.doc_id.in_(evidence_docs))]
    foundConcepts = Counter([x["concept"] for x in annotData])
    
    if len(foundConcepts) > 100:
        
        if foundConcepts.most_common(1)[0][1] < 2:
            fcThreshold = 0
        else:
            fcThreshold = 2
    else:
        fcThreshold = 0
        
    #print("foundConcepts", len(foundConcepts), fcThreshold)
    #print(foundConcepts.most_common(10))
    
    useConcepts = [x[0] for x in foundConcepts.most_common(250)]
    #20*(2**foundConcepts[x])
    foundConcepts = [{"text": x, "size": foundConcepts[x], "orig_count": foundConcepts[x]} for x in useConcepts if foundConcepts[x] > fcThreshold]
    #print("foundConcepts2", len(foundConcepts))

    sentenceData = []
    for x in sendData:
        for y in extract_sentences(x["sent_evidences"]):
            y["sent"] = sentid2sent[y["sentid"]]
            
            highSent = y["sent"]
            locList = sorted([y["loc1"], y["loc2"]], key=lambda x: x[0], reverse=True)
            
            for elem in locList:
                pref = highSent[:elem[0]]
                suff = highSent[elem[1]:]
                target = highSent[elem[0]:elem[1]]
                
                highSent = pref + "<span style='background-color: #FFFF00'>{}</span>".format(target) + suff
                
            y["sent_high"] = highSent.replace("\r","").replace("\n","").replace("\t"," ")
            
            sentenceData.append(y)
        
            y["docid_link"] = make_link(y["docid"])
            y["docid_source"] = make_source(y["docid"])
            
    sentenceData = natsorted(sentenceData, key=lambda x: x["docid"], reverse=True)
    
    orgs = set()
    for orgstr in organisms:
        for o in orgstr.split(";"):
            orgs.add(o)

    return render_template('server_details.html', **{
        "mirna_family": mirna,
        "gene_family": gene,
        "interaction": interaction,
        "organisms": ", ".join(natsorted(orgs)), #sorted(set())[0],
        "evidences": ", ".join([str(x) for x in evidences]),
        "consensus": ", ".join([str(x) for x in consensus]),
        'detail_data': sendData,
        "sentences": sentenceData,
        "annotations": foundConcepts, 
        "timeline_url": "/{}/timeline/{}/{}/{}".format(hostFolder,mirna, gene, interaction),
        "timelinedata_url": "/{}/timelinedata/{}/{}/{}".format(hostFolder,mirna, gene, interaction),
        "host": hostFolder
    })


@app.route('/api/data')
def data():
    query = MXRelations.query
    
    #print(request.args)

    # search filter
    search = request.args.get('search[value]')
    if search:
        
        prefix = "%"
        suffix = "%"
        
        if search.endswith("$"):
            suffix = ""
        if search.startswith("^"):
            prefix = ""
    
        query = query.filter(db.or_(
            MXRelations.miRNA_family.like(f'{prefix}{search}{suffix}'),
            MXRelations.gene_family.like(f'{prefix}{search}{suffix}')
        ))
    
    
    # filters
    i = 0
    while True:
        col_name = request.args.get(f'columns[{i}][data]')
        
        if col_name is None:
            break
            
        col_sel_value = request.args.get(f'columns[{i}][search][value]')
        
        if col_sel_value == "":
            i += 1
            continue
        
        #print("Filter", col_name, col_sel_value, col_sel_value=="")
        
        if col_name in ["miRNA_family", "gene_family"]:
            prefix = "%"
            suffix = "%"
            
            searchValue = col_sel_value
            if searchValue.endswith("$"):
                suffix = ""
                searchValue = searchValue[:-1]
            if searchValue.startswith("^"):
                prefix = ""
                searchValue = searchValue[1:]
                
            searchPattern = prefix + searchValue + suffix               
            
            query = query.filter( MXRelations.__dict__[col_name].like(searchPattern) )
        elif col_name in ["evidence_count"]:
            
            print(col_name, col_sel_value)
            
            splitValues = col_sel_value.split("-yadcf_delim-")
            
            if len(splitValues[0]) > 0:
                lowerBound = int(splitValues[0])
                print("evidence_count >=", lowerBound)
                query = query.filter( MXRelations.evidence_count >= lowerBound )
            
            if len(splitValues[1]) > 0:
                upperBound = int(splitValues[1])
                print("evidence_count <=", upperBound)
                query = query.filter( MXRelations.evidence_count <= upperBound )
            
        elif col_name in ["details"]:              
            print("context filter to", col_name, col_sel_value)
            
            if len(col_sel_value) > 0:
                
                if "|" in col_sel_value:
                    split_values = col_sel_value.split("|")
                    cell_value, concept_value, disease_value = split_values[0], split_values[1], split_values[2]
                    
                    print("detailed filtering", "[{}]".format(cell_value), "[{}]".format(concept_value), "[{}]".format(disease_value))
                    
                    annotQuery = None
                    
                    for value, selector in [(cell_value, ["celllines"]), (concept_value, ["ModelAnatomy", "ncit", "GeneOntology"]), (disease_value, ["disease"])]:
                        
                        if len(value) == 0:
                            continue
                        
                        condition = db.and_(Annotations.annotation.in_(selector), Annotations.concept.like("%{}%".format(value)))
                        
                        if annotQuery is None:
                            annotQuery = db.session().query(Annotations.doc_id).distinct(Annotations.doc_id)
                            annotQuery.filter( condition )
                            
                        else:
                            
                            annotQuery2 = db.session().query(Annotations.doc_id).distinct(Annotations.doc_id)
                            annotQuery2.filter( condition )
                            
                            annotQuery = annotQuery.filter(Annotations.doc_id.in_(annotQuery2))
                            
                    if not annotQuery is None:
                        annotQuery.subquery("sq_annot")
                    
                else:
                    #print("annotQuery")
                    annotQuery = db.session().query(Annotations.doc_id).distinct(Annotations.doc_id).\
                        filter(Annotations.concept.like("%{}%".format(col_sel_value))).subquery("sq_annot")
                        
                        
                if not annotQuery is None:
                    #print("subQuery")
                    subQuery = db.session().query((Interactions.miRNA_family+Interactions.gene_family+Interactions.interaction).label("ccint")).distinct("ccint").filter( Interactions.evidence_documents.in_(annotQuery) ).subquery("sq_int")
                    
                    #print("Query")
                    query = query.filter((MXRelations.miRNA_family + MXRelations.gene_family + MXRelations.interaction).in_(subQuery))
                    
        else:
            
            if col_name == "is_consensus":
                if col_sel_value == "yes":
                    col_sel_value = 1
                else:
                    col_sel_value = 0
            
            query = query.filter(MXRelations.__dict__[col_name] == col_sel_value )
        i += 1

    # sorting
    order = []
    i = 0
    while True:
        col_index = request.args.get(f'order[{i}][column]')
        if col_index is None:
            break
        col_name = request.args.get(f'columns[{col_index}][data]')
        #if col_name not in ['gene_family', 'miRNA_family', 'interaction']:
        #    col_name = 'miRNA_family'
        descending = request.args.get(f'order[{i}][dir]') == 'desc'
        col = getattr(MXRelations, col_name)
        if descending:
            col = col.desc()
        order.append(col)
        i += 1
        
    if order:
        query = query.order_by(*order)

    # pagination
    start = request.args.get('start', type=int)
    length = request.args.get('length', type=int)   
    
    queryCount = query.count()
    
    query = query.offset(start).limit(length)
    

    sendData = [user.to_dict() for user in query]
    for result in sendData:
        result["is_consensus"] = to_consensus_string(result["is_consensus"])

    # response
    return json.dumps({
        'data': sendData,
        'recordsFiltered': queryCount,
        'recordsTotal': MXRelations.query.count(),
        'draw': request.args.get('draw', type=int)
    })

#
##
### TIMELINES
##
#


@app.route('/timeline/<mirna>/<gene>/<interaction>') 
def timeline_details(mirna, gene, interaction):

    session = db.session()
    fig = generateInteractionHistory(cursor=session, gene=gene, mir=mirna, interaction=interaction, obodict=infodict2obo)
    
    if not fig is None:
        img = BytesIO()
        fig.savefig(img, format='jpeg', bbox_inches = 'tight',  dpi = 100)
        img.flush()
        plt.close()

    img.seek(0)
    return send_file(img, mimetype='image/jpeg')


@app.route('/timelinedata/<mirna>/<gene>/<interaction>') 
def timeline_data(mirna, gene, interaction):

    session = db.session()
    allInteractions = generateInteractionHistory(cursor=session, gene=gene, mir=mirna, interaction=interaction, obodict=infodict2obo, return_data=True)
    
    allInteractions = sorted(allInteractions, key=lambda x: x["date"])
    
    entries = []

    for x in allInteractions:
        
        ctx_string = ""
        for ctx in x["context"]:
            for elem in x["context"][ctx]:
                ctx_string += "{} ({})<br/>".format(elem[0], elem[1])
            ctx_string += "<br/>"
            
        authors = "; ".join(x["authors"]) + "; et al."
        journal = x["journal"]
        title = x["title"]
        
        if len(title) > 30:
            title = title[:30] + "..."
        
        date = x["date"].strftime("%B %Y")
                    
        pmidDesc = """
        <span><strong>{}</strong><br/>
        <span>{}</span><br/>
        <span>{}</span><br/>
        <span>{} {} {}</span><br/><br/>
        <span>{}</span></span>""".format(x["interaction"], title, authors, journal, date, x["doc_id"], ctx_string )
        
        
        x["doc_id"]
        
        entries.append({"year": date, "title": pmidDesc, "pmcurl": make_url(x["doc_id"])})

    # response
    return json.dumps({
        'data': entries
    })


def get_relation_data(cursor, mirna, gene, interaction):
    
    interaction_condition = ""
    if not interaction is None:
        interaction_condition = "and interaction = '{}'".format(interaction)
    
    if mirna and gene:
        sqlres = cursor.execute("""
                    SELECT miRNA_family, gene_family, interaction, evidence_documents FROM mx WHERE miRNA_family='{}' and gene_family='{}' {}
                    ORDER BY evidence_count desc;
                    """.format(mirna, gene, interaction_condition)
                    )
    else:
        if mirna:
            query_equal = "miRNA_family='{}'".format(mirna)
        else:
            query_equal = "gene_family='{}'".format(gene)
        
        sqlres = cursor.execute("""
                SELECT miRNA_family, gene_family, interaction, evidence_documents FROM mx WHERE {} {}
                ORDER BY evidence_count desc;
                """.format(query_equal, interaction_condition)
                )
    
    results = []
    for x in sqlres:
        results.append({
            "miRNA_family": x[0],
            "gene_family": x[1],
            "interaction": x[2],
            "evidence_documents": x[3],
        })
    return results

def get_doc_pubdates(cursor, documents):
    
    query = """
    SELECT doc_id, date FROM mx_dates WHERE doc_id IN ({});
    """.format(",".join(["'{}'".format(x) for x in documents]))
    
    sqlres = cursor.execute(query)
    
    results = {}
    for x in sqlres:
        if x[1] == "0001-01-01":
            continue
        if x[1].startswith("0000"):
            continue
        results[x[0]] = datetime.datetime.strptime(x[1], '%Y-%m-%d')

    return results

def get_doc_authors(cursor, documents):
    
    query = """
    SELECT doc_id, firstname, lastname FROM mx_authors WHERE doc_id IN ({});
    """.format(",".join(["'{}'".format(x) for x in documents]))
    
    sqlres = cursor.execute(query)
    
    results = defaultdict(list)
    for x in sqlres:
        results[x[0]].append( "{} {}".format(x[1], x[2]) )

    return results

def get_doc_journals(cursor, documents):
    query = """
    SELECT doc_id, journal FROM mx_journals WHERE doc_id IN ({});
    """.format(",".join(["'{}'".format(x) for x in documents]))
    
    sqlres = cursor.execute(query)
    
    results = dict()
    for x in sqlres:
        results[x[0]] = x[1]

    return results

def get_doc_titles(cursor, documents):
    query = """
    SELECT doc_id, title FROM mx_titles WHERE doc_id IN ({});
    """.format(",".join(["'{}'".format(x) for x in documents]))
    
    sqlres = cursor.execute(query)
    
    results = dict()
    for x in sqlres:
        results[x[0]] = x[1]

    return results
        
def get_annot_data(cursor, documents, rel_annotations=['celllines', 'disease', 'GeneOntology']):
    sqlres = cursor.execute("""
                SELECT doc_id, annotation, concept_id, concept FROM mx_annot WHERE doc_id IN ({}) and annotation IN ({});
                """.format(",".join(["'{}'".format(x) for x in documents]), ",".join(["'{}'".format(x) for x in rel_annotations]))
                )
    
    results = []
    for x in sqlres:
        results.append({
            "doc_id": x[0],
            "annotation": x[1],
            "concept_id": x[2],
            "concept": x[3],
        })
    return results
        
def make_timeline( allInteractions, title, outpath=None ):

    allInteractions = sorted(allInteractions, key=lambda x: x["date"])
    
    names = []
    dates = []

    for x in allInteractions:
        
        ctx_string = ""
        for ctx in x["context"]:
            for elem in x["context"][ctx]:
                ctx_string += "{} ({})\n".format(elem[0], elem[1])
            ctx_string += "\n"
        pmidDesc = x["interaction"] + "\n" + "{}, {}".format(x["doc_id"], x["date"].strftime("%B %Y")) + "\n" + ctx_string + "\n"
        date = x["date"]

        names.append(pmidDesc)
        dates.append(date)
        
    alllevels = [-5,5,-1,1] #-3,3,
        
    # Choose some nice levels
    levels = np.tile(alllevels,
                     int(np.ceil(len(dates)/len(alllevels))))[:len(dates)]
    
    szFac = len(names) // 15
    szFac += 1

    # Create figure and plot a stem plot with the date
    fig, ax = plt.subplots(figsize=(szFac * 15, 8), constrained_layout=True)
    ax.set(title=title)

    markerline, stemline, baseline = ax.stem(dates, levels,
                                             linefmt="C3-", basefmt="k-")

    plt.setp(markerline, mec="k", mfc="w", zorder=3)

    # Shift the markers to the baseline by replacing the y-data by zeros.
    markerline.set_ydata(np.zeros(len(dates)))

    # annotate lines
    vert = np.array(['top', 'bottom'])[(levels > 0).astype(int)]
    for d, l, ltext, va in zip(dates, levels, names, vert):
        ax.annotate(ltext, xy=(d, l+ (-1) * np.sign(l) * 0.75), xytext=(-10, np.sign(l)*4),
                    textcoords="offset points", va=va, ha="right")

    # format xaxis with 4 month intervals
    ax.get_xaxis().set_major_locator(mdates.MonthLocator(interval=6))
    ax.get_xaxis().set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")

    # remove y axis and spines
    ax.get_yaxis().set_visible(False)
    for spine in ["left", "top", "right"]:
        ax.spines[spine].set_visible(False)

    ax.margins(y=0.5)
    ax.set_ylim(2*min(alllevels),2*max(alllevels))
    #ax.grid(True, which='both')
        
    return fig
    
def vis_interaction( mir, gene, interactions):
    
    if len(interactions) == 1:
        relInteract, relCategory = list(interactions.keys())[0].split(";")
    else:
        relIC, relCount = interactions.most_common(1)[0]
        relInteract, relCategory = relIC.split(";")

    if relInteract == "MIR_GENE":
        e1 = mir
        e2 = gene               
    else:
        e1 = gene
        e2 = mir
     
    if relCategory in ["DOWN"]:
        e12c = u"\u22a3"
    elif relCategory in ["UP"]:
        e12c = u"\u2191"
    elif relCategory in ["NEU"]:
        e12c = u"\u21e5"
    elif relCategory in ["NA"]:

        e12c = u"\u2974"
        e12c = u"\u1e6a"
        
    return "{} {} {}".format(e1, e12c, e2)



def get_doc_contexts(cursor, doc_ids, context_obos, printable=True):
    
    res = get_annot_data(cursor, doc_ids)
    
    result = defaultdict(lambda: defaultdict(Counter))
    for x in res:
        docid = x["doc_id"]
        ctx_type = x["annotation"]
        concept = (x["concept"], x["concept_id"])
        
        result[docid][ctx_type][concept] += 1
        
    if not printable:
        return result
        
    for doc_id in result:
        for context in result[doc_id]:
            
            if not context in context_obos:
                continue
            obo = context_obos[context]
            
            parents = []
            for concept, concept_id in result[doc_id][context]:
                
                conceptParents = obo[concept_id].get_parents()
                if conceptParents is None:
                    continue
                
                for parent in conceptParents:
                    parents.append((obo[parent.termid].name, parent.termid))
            
            for parent in parents:
                result[doc_id][context][parent] += 2
                       
                       
    print_results = defaultdict(lambda: defaultdict(list))
    for doc_id in result:
        for context in result[doc_id]:
            for elem, _ in result[doc_id][context].most_common(2):
                
                elem_name, elem_id = elem
                if len(elem_name) > 30:
                    elem_name = elem_name[:17] + " ..."
                
                print_results[doc_id][context].append( (elem_name, elem_id) )
                
                                                
    return print_results

def get_doc_with_contexts(cursor, relevant_documents, context, obodict):
   
     
    context2terms = defaultdict(set)
    for ctx in context:
        for term in context[ctx]:
            context2terms[ctx].update([term["termid"]]+[x.termid for x in obodict[ctx][term["termid"]].getAllChildren()])
            
               
    doc_contexts = get_doc_contexts(cursor, relevant_documents, obodict, printable=False)
    
    accepted_documents = set()

    for doc_id in doc_contexts:
        accepted_contexts = 0
        for ctx in context:
            doc_terms = [x[1] for x in doc_contexts[doc_id][ctx]]
            
            if len(context2terms[ctx].intersection(doc_terms)) > 0:
                accepted_contexts += 1
                
        if accepted_contexts == len(context):
            accepted_documents.add(doc_id)
    
    return accepted_documents


def generateInteractionHistory( cursor, gene, mir, interaction, title="", obodict={}, context=None, return_data=False):
    
    mir_gene_interactions = get_relation_data(cursor, mir, gene, interaction)
    
    relevant_documents = set()
    doc2interactions = defaultdict(Counter)
    
    for x in mir_gene_interactions:
        for doc in x["evidence_documents"].split(";"):
            relevant_documents.add(doc)
            doc2interactions[doc][x["interaction"]] += 1
    #
    ## filter for documents one is interested in
    #
    if not context is None:
        relevant_documents = get_doc_with_contexts(cursor, relevant_documents, context, obodict)
    
    contexts = get_doc_contexts(cursor, relevant_documents, obodict)
    
    docDates = get_doc_pubdates(cursor, relevant_documents)
    docAuthors = get_doc_authors(cursor, relevant_documents)
    docJournals = get_doc_journals(cursor, relevant_documents)
    docTitles = get_doc_titles(cursor, relevant_documents)
    #docJournals = {}
    #docTitles = {}
    
    print_entries = []
    for entry in mir_gene_interactions:
        for doc_id in entry["evidence_documents"].split(";"):
            
            if not doc_id in relevant_documents:
                continue
            
            doc_entry = {}
            doc_entry["interaction"] = vis_interaction(entry["miRNA_family"], entry["gene_family"], doc2interactions[doc_id])

            doc_entry["doc_id"] = doc_id
            
            if not doc_id in docDates:
                continue
            
            doc_entry["date"] = docDates.get(doc_id, None)
            doc_entry["authors"] = docAuthors.get(doc_id, [])
            doc_entry["journal"] = docJournals.get(doc_id, "-/-")
            doc_entry["title"] = docTitles.get(doc_id, "-/-")
            doc_entry["context"] = contexts[doc_id]
            
            print_entries.append(doc_entry)

    if return_data:
        return print_entries


    if len(print_entries):
        return make_timeline( print_entries, title, outpath=None )
    
    return None













if __name__ == '__main__':
    app.run(host="localhost", port=8001, debug=False)
