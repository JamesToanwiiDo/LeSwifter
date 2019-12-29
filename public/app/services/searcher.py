# searcher.py
# Name: Joseph Van Boxtel & (James) Toan Minh Do
# CS 483 - Final Project
# December 6th, 2019
# Dr. Ben McCamish

from random import randint
from whoosh.scoring import BM25F
from whoosh.fields import *
from whoosh.qparser import *
from whoosh.qparser.dateparse import DateParserPlugin
from index import *
from package import Package
import random
from random import randint

# Custom BM25 ranking class
class CustomPackageWeighting(BM25F):
    starCountKey = 'stars'
    authScoreKey = 'authScore'
    use_final = True
    
    def final(self, searcher, docnum, score):
        fields = searcher.reader().stored_fields(docnum)
        starCount = fields[self.starCountKey]
        authScore = fields[self.authScoreKey]# Avoid multiplying by zero.
        starModifier = starCount/100 + 1 # Avoid multiplying by zero.
        authModifier = authScore*1000 + 1
        finalScore = score * authModifier * starModifier

        fullName = fields['owner'] + '/' + fields['name']
        print('Document', fullName, score, starModifier, authModifier, 'final: ', finalScore)
        return finalScore

class RandomWeighting(BM25F):
    use_final = True

    def final(self, searcher, docnum, score):
        rand = randint(1, 1000)/1000
        finalScore = rand
        return finalScore

class MyWhooshSearcher(object):
    # Initialize variables
    def __init__(self, myIndexer, packagesPath, searchBy = ['owner','name', 'path', 'description']):
        self.indexer = myIndexer
        self.packagesPath = packagesPath
        self.searchFields = searchBy
        super(MyWhooshSearcher, self).__init__()

    # Initialize the database's index
    def prepare(self):
        self.indexer.findOrCreateIndex()

    # Initiate normal search with the user's query
    def search(self, queryEntered, page=1):
        return self._search(self.buildQuery(queryEntered), page)

    # Initiate advanced search with the user's query
    def adv_search(self, advQueryString, page=0):
        return self._search(self.buildQuery(advQueryString), page)

    # Performs the search operations
    # Fetches the top results returned by whoosh
    # Loads those packages in for rendering
    def _search(self, query, page=1):
        customWeighting = CustomPackageWeighting()

        with self.indexer.indexer.searcher(weighting=customWeighting) as search:
            topHits = search.search_page(query, page)
            totalCount = topHits.total
            print('query terms: ')
            for t in query.iter_all_terms():
                print(repr(t))
            docResults = list()
            for hit in topHits:
                filteredResult = self.trimToDesiredFields(hit, ['name','owner'])
                docResults.append(Package.load(filteredResult[0], filteredResult[1], self.packagesPath))
            return (docResults, topHits.pagecount, totalCount)
        return ([], 0, 0)

    # Fetch a random popular package from the database with pre-defined search
    def getSuggested(self, count):
        parser = QueryParser('stars', self.indexer.schema)
        query = parser.parse('[1000 TO]', debug=True)
        with self.indexer.indexer.searcher(weighting=RandomWeighting()) as search:
            topHits = search.search(query, limit=5)
            docResults = list()
            for hit in topHits:
                filteredResult = self.trimToDesiredFields(hit, ['name','owner'])
                docResults.append(Package.load(filteredResult[0], filteredResult[1], self.packagesPath))
            return docResults
        return []

    # Builds the query for normal search and returns the query
    # Parses the user queries over all searchFields
    def buildQuery(self, userQuery):
        parser = MultifieldParser(self.searchFields, schema=self.indexer.schema, group=AndGroup)
        query = parser.parse(userQuery, debug=True)
        return query

    # Builds a query for the Advanced Search feature and returns the query
    # Parses specific parameters over the correct searchField
    # Performs checks in case fields are empty
    def buildAdvQueryString(self, owner='', name='', dependencies='', swiftVersion='', starsMin='', starsMax=''):
        segments = []
        if(len(owner) > 0):
            segments.append('owner:(' + owner + ')')

        if(len(name) > 0):
            segments.append('name:(' + name + ')')

        if(len(dependencies) > 0):
            segments.append("dependencies:('" + dependencies + "')")

        if(len(swiftVersion) > 0):
            segments.append("swiftVersion:(" + swiftVersion + ")")

        if(len(starsMin) > 0 or len(starsMax) > 0):
            segment = "stars:["
            if len(starsMin) > 0:
                segment += starsMin + ' '
            segment += "TO"
            if len(starsMax) > 0:
                segment += ' ' + starsMax
            segment += "]"
            segments.append(segment)

        return ' '.join(segments)

    # Trim the fields
    def trimToDesiredFields(self, result, fields):
        return tuple([result[key] for key in fields])
