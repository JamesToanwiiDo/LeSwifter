# package.py
# Name: Joseph Van Boxtel & (James) Toan Minh Do
# CS 483 - Final Project
# December 6th, 2019
# Dr. Ben McCamish

import whoosh
from whoosh.fields import *
import pickle
import os

class Package:
    # Returns the correct info.pickle file for the specified package
    def infoPath(name, owner, packagesPath):
        return os.path.join(packagesPath, owner, name, 'info.pickle')

    # Loads all package's info from the pickle file
    # Returns the data pulled from the info file
    def load(repoName, ownerName, packagesPath):
        path = Package.infoPath(repoName, ownerName, packagesPath)
        with open(path, mode='rb') as f:
            p = pickle.load(f)
            return Package(p.get('name'),
                           p.get('owner'),
                           p.get('dependencies', []),
                           p.get('description', ''),
                           p.get('readmeMD', ''),
                           p.get('stars', 0),
                           p.get('tags', []),
                           p.get('localOwnerAvatar'),
                           p.get('swiftVersion'))
        return None

    # Saves info scrapped to a specified pickle file
    def save(self, packagesPath):
        path = Package.infoPath(self.name, self.owner, packagesPath)
        with open(path, mode='wb') as f:
            properties = dict()
            properties['name'] = self.name
            properties['owner'] = self.owner
            properties['dependencies'] = self.dependencies
            properties['description'] = self.description
            properties['readmeMD'] = self.readmeMD
            properties['stars'] = self.stars
            properties['tags'] = self.tags
            properties['localOwnerAvatar'] = self.localOwnerAvatar
            properties['swiftVersion'] = self.swiftVersion

            pickle.dump(properties, f)

    # Initialize variables
    def __init__(self, name, owner, dependencies=[], description="", readmeMD="", stars=0, tags=[], localOwnerAvatar=None, swiftVersion=None):
        """
        name: string - name of the repository on GitHub
        owner: string - name of the owner of the repository on GitHub
        dependencies: list of (name: string, owner: string) - dependency owner and repo name pairs.
            One level deep ATM. Maybe deeper in the future.
        description: string - short description from GitHub
        readmeMD: string - markdown formatted README.
        stars: int - GitHub stars count
        tags: list of strings - GitHub topics for the repository
        localOwnerAvatar: string - path to the avatar image on the local server file system
        lastCommitDate: date -
        """
        self.name = name
        self.owner = owner
        self.dependencies = dependencies
        self.dependenciesString = str(dependencies)
        self.dependencyFullNames = map(fullNameFromTuple, dependencies)
        self.description = description
        self.readmeMD = readmeMD
        self.stars = stars
        self.tags = tags
        self.tagsString = str(tags)
        self.localOwnerAvatar = localOwnerAvatar
        self.swiftVersion = swiftVersion

# Returns the repository's GitHub URL
def gitHubURL(ownerName, repoName):
    return 'https://github.com/' + owner + '/' + name

# Returns the full name of the repo: <owner>/<repoName>
def fullNameFromTuple(ownerNamePair):
    return '/'.join(ownerNamePair)

# Handles the subdirectory paths
def listSubdirPaths(dirPath):
    for subdirName in os.listdir(dirPath):
        subdirPath = os.path.join(dirPath, subdirName)
        if not os.path.isdir(subdirPath):
            continue
        yield subdirPath

def packagesIn(packagesPath):
    for ownerPath in listSubdirPaths(packagesPath):
        for repoPath in listSubdirPaths(ownerPath):
            ownerName = os.path.split(ownerPath)[1]
            repoName = os.path.split(repoPath)[1]
            yield (ownerName, repoName)

def loadAllPackages(packagesPath):
    packages = dict()
    for owner, name in packagesIn(packagesPath):
        try:
            package = Package.load(name, owner, packagesPath)
            fullName = owner + '/' + name
            packages[fullName] = package
        except:
            continue
    return packages
