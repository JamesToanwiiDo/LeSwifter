# index.py
# Name: Joseph Van Boxtel & (James) Toan Minh Do
# CS 483 - Final Project
# December 6th, 2019
# Dr. Ben McCamish

from whoosh.index import *
from whoosh.fields import *
from whoosh.analysis import *
import csv
import os
import sys
import io
import operator
from package import *
import s3Storage
from scoring import *

class MyWhooshIndexer(object):
    # Initialize the variables and schema
    def __init__(self):
        self.indexName = 'leswifter'
        self.schema = MyWhooshIndexer.createSchema()
        super(MyWhooshIndexer, self).__init__()

    # Creates a directory to store the database's index
    # Performs indexing over the scrapped data directory
    def index(self, shouldDownloadFresh=False, dataFolderPath="//public/app/services/data/", indexPath='SwiftPackagesIndex'):
        if not os.path.exists(indexPath):
            os.makedirs(indexPath)
        indexer = create_in(indexPath, indexname=self.indexName, schema=self.schema)
        self.writer = indexer.writer()

        packagesFolderPath = os.path.join(dataFolderPath, 'packages')

        # If the shouldDownloadFresh flag is true then performs download of packages and
        # images from the S3 database
        if shouldDownloadFresh:
            if not os.path.exists(packagesFolderPath):
                s3Storage.download_dir('packages', dataFolderPath)
            s3Storage.download_dir('images', '//public/app/static/images')

        packagesByFullName = loadAllPackages(packagesFolderPath)
        depGraph = buildDepGraph(packagesByFullName)
        hubScores, authScores = hitsStyleScores(packagesByFullName, depGraph)

        for fullName, package in packagesByFullName.items():
            self.addToIndex(package, authScores[fullName])

        self.writer.commit()

        self.indexer = indexer

        printTopScores(hubScores, authScores)

    # Check for an existing index directory and creates it if there's none
    def findOrCreateIndex(self, path='SwiftPackagesIndex'):
        if exists_in(path, indexname=self.indexName):
            self.indexer = open_dir(path, indexname=self.indexName, schema=self.schema)
            return
        self.index()

    # Returns the index's schema
    def createSchema():
        return Schema(name=TEXT(stored=True, analyzer=MyWhooshIndexer.codeNameSplitterFilter()),
                      owner=TEXT(stored=True, analyzer=MyWhooshIndexer.codeNameSplitterFilter()),
                      path=TEXT(stored=False),
                      readme=TEXT(stored=False),
                      description=TEXT(stored=False),
                      tags=KEYWORD(stored=False, scorable=True, lowercase=True),
                      dependencies=TEXT(stored=False, analyzer=MyWhooshIndexer.codeNameSplitterFilter()),
                      stars=NUMERIC(sortable=True,stored=True),
                      swiftVersion=TEXT(),
                      authScore=NUMERIC(float, stored=True))

    def codeNameSplitterFilter():
        indexTimeFilter = IntraWordFilter(mergewords=True) | ExactMatchBoostFilter()
        queryTimeFilter = IntraWordFilter(mergewords=False)
        return SpaceSeparatedTokenizer() | MultiFilter(index=indexTimeFilter, query=queryTimeFilter)  | LowercaseFilter()# | PrintFilter()

    # Add to the database's index the package's detailed information
    def addToIndex(self, package, authScore):
        self.writer.add_document(name=package.name,
                            owner=package.owner,
                            path=package.name+'/'+package.owner,
                            readme=package.readmeMD,
                            description=package.description,
                            tags=' '.join(package.tags),
                            dependencies=' '.join(package.dependencyFullNames),
                            stars=package.stars,
                            swiftVersion=package.swiftVersion,
                            authScore=authScore)

# Prints the (hub/auth) scores of the top 50 results 
def printTopScores(hubScores, authScores):
    top50Hubs = sorted(hubScores.items(), key=operator.itemgetter(1), reverse=True)[:50]
    top50Auths = sorted(authScores.items(), key=operator.itemgetter(1), reverse=True)[:50]
    # Just for comparison. These values are not used for scoring; just to calculate the auth score.
    print("Top 50 Hubs")
    for hub in top50Hubs:
        print(hub)
    print("Top 50 Auths")
    for auth in top50Auths:
        print(auth)

class PrintFilter(Filter):
    """An identity filter: passes the tokens through untouched after printing.
    """

    def __call__(self, tokens):
        print("Tokens:")
        for t in tokens:
            print(repr(t.text))
            yield t

class ExactMatchBoostFilter(Filter):
    def __call__(self, tokens):
        prevPrevText = 'BaseValueThatDefinitelyWontMatch'
        prevText = 'BaseValueThatDefinitelyWontMatch'
        for t in tokens:
            if t.text.endswith(prevPrevText+prevText):
                print('boosting ' + t.text + " from " + prevPrevText + ', ' + prevText)
                # Must be the merged token.
                t.boost = t.boost * 3
            prevPrevText = prevText
            prevText = t.text
            yield t

# Main
if __name__ == '__main__':
    indexer = MyWhooshIndexer()
    indexer.index()
