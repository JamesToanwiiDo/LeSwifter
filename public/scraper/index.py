import whoosh
from whoosh.index import create_in
from whoosh.index import open_dir
from whoosh.fields import *
from whoosh.qparser import QueryParser
from whoosh.qparser import MultifieldParser
from whoosh import qparser
import csv
import os
import subprocess
import io
import re

class MyWhooshIndexer(object):
    def __init__(self):
        self.schema = Package.schema()
        super(MyWhooshIndexer, self).__init__()

    def index(self):
        indexer = self.findOrCreateIndexer(self.schema, 'SwiftPackagesIndex')
        writer = indexer.writer()

        docs = self.parseDocuments("data")
        for doc in docs:
            doc.addToIndex(writer)

        writer.commit()

        self.indexer = indexer

    def findOrCreateIndexer(self, schema, path):
        if not os.path.exists(path):
            os.makedirs(path)
        indexer = create_in(path, schema)
        return indexer

    def parseDocuments(self, dataPath):
        docs = list()
        for ownerName in os.listdir(dataPath):
            #print("owner: " + ownerName)
            ownerPath = os.path.join(dataPath, ownerName)
            #print("ownerPath: " + ownerPath)
            if not os.path.isdir(ownerPath):
                continue
            for repoName in os.listdir(ownerPath):
                #print("repo: " + repoName)
                repoPath = os.path.join(ownerPath, repoName)
                #print("repoPath: " + repoPath)
                if not os.path.isdir(repoPath):
                    continue

                deps = self.parseDependencies(repoPath)
                print(repoPath + "deps: " + str(deps))
                docs.append(Package(repoName, ownerName, deps, "READ ME"))
        return docs

    def parseDependencies(self,localRepoPath):
        """ returns a list of dependency strings """

        manifestFile = io.open(os.path.join(localRepoPath,'Package.swift'), mode="r", encoding="utf-8")
        manifestContent = manifestFile.read()
        manifestFile.close()

        gitUrls = urlsIn(manifestContent)
        return list(filter(notNone, map(authorAndName, gitUrls)))

def urlsIn(string):
    return re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string)

def authorAndName(gitUrl):
    comps = gitUrl.split('/')
    if len(comps) > 2:
        author = comps[-2]
        name = comps[-1]
        #name = name[:-4] # remove .git
        return author+'/'+name
    return None

def notNone(element):
    return not element == None

class GitHubRepo:
    def __init__(self, name, owner, description, lastestPushTime, starCount, tags, branches, localAuthorImageURL):
        """
        tags: list of strings
        branches: list of strings
        """
        self.url = '...'

class Package:
    def __init__(self, name, gitubRepo, dependencies, readmeMD, readmeHTML):
        """
        dependencies: list of strings of form: owner/repo
        readmeMD: string
        readmeHTML: string
        """
        self.identifier = owner + '/' + name
        self.name = name
        self.owner = owner
        self.dependencies = dependencies
        self.readmeMD = readmeMD

    def schema():
        return Schema(identifier=ID(stored=True, unique=True),
                      name=TEXT(stored=True, field_boost=5.0),
                      owner=TEXT(stored=True, field_boost=1.5),
                      readme=TEXT(stored=True),
                      dependencies=KEYWORD(stored=True))

    def addToIndex(self, writer):
        writer.add_document(identifier=self.identifier,
                            name=self.name,
                            owner=self.owner,
                            readme=self.stripReadme(self.readmeMD),
                            dependencies=', '.join(self.dependencies))

    def stripReadme(self, readmeMD):
        return readmeMD

if __name__ == '__main__':
    indexer = MyWhooshIndexer()
    indexer.index()
