# githubPackages.py
# Name: Joseph Van Boxtel & (James) Toan Minh Do
# CS 483 - Final Project
# December 6th, 2019
# Dr. Ben McCamish

import os
from github import Github
import github as github_api
import base64
import io
import re
import s3Storage
import itertools
import time
import requests
from package import Package
import datetime

def ensureParentDirsExist(dirsPath):
    """ Create directories if they don't exist yet. Don't pass a path to a file. """
    if not os.path.exists(dirsPath):
        os.makedirs(dirsPath)

def ensureParentDirsExistForFile(filePath):
    """ Create directories if they don't exist yet. """
    ensureParentDirsExist(os.path.dirname(filePath))

def stripBreakTag(html):
    return re.sub('<br>', ' ', html)

# Rate Limiting
# General: 5000 per hour
# Search: 30 per minute
# Note each search is limited to 1000 results.
class GithubPackages:

    def __init__(self, token='7f3199cd11ab38a271cd5e10a03ff07afba52736'):
        self.github = Github(token)
        self.rateLimitsHit = 0

    def storePackageManifest(self, githubFileMatch, repoPath):
        f = open(os.path.join(repoPath,'Package.swift'), "wb+")
        self.waitForCoreRateLimitIfNeeded()
        content = base64.b64decode(githubFileMatch.content)
        f.write(content)
        f.close()

    def fetchAvatar(self, repo, localPath):
        # limiting the size can save as much as 8x in disk space.
        avatarLink = repo.owner.avatar_url+'&s=50'
        #print("Avatar from: ", avatarLink)
        ensureParentDirsExistForFile(localPath)
        with open(localPath, 'wb') as file:
            req = requests.get(avatarLink)
            file.write(req.content)

    def reposForSearch(self, keywords):
        advancedFilterSpecifiers = "language:Swift "
        query = keywords + advancedFilterSpecifiers
        self.waitForSearchRateLimitIfNeeded()
        for repo in self.github.search_repositories(query, sort="stars"):
            try:
                self.waitForCoreRateLimitIfNeeded()
                file = repo.get_contents("/Package.swift")
                yield (repo, file)
            except github_api.GithubException:
                print(repo.full_name + " does not have a Package.swift file.")
        return

    def reposForManifestFileSize(self, minKiloByteSize=None, maxKiloByteSize=None):

        if minKiloByteSize == None and maxKiloByteSize == None:
            fileSizeConstraint = ""
        elif minKiloByteSize != None and maxKiloByteSize == None:
            fileSizeConstraint = "size:>" + str(minKiloByteSize)
        elif minKiloByteSize == None and maxKiloByteSize != None:
            fileSizeConstraint = "size:<" + str(maxKiloByteSize)
        else:
            fileSizeConstraint = "size:" + str(minKiloByteSize) + ".." + str(maxKiloByteSize)

        self.waitForSearchRateLimitIfNeeded()
        results = self.github.search_code("PackageDescription " + fileSizeConstraint + " path:/ filename:Package.swift")
        print("Searching by " + fileSizeConstraint + " returned " + str(results.totalCount) + " repos.")
        for manifestFile in results:
            yield (manifestFile.repository, manifestFile)

    def waitForSearchRateLimitIfNeeded(self):
        """ Searches before the search rate limit kicks in. """
        limitInfo = self.github.get_rate_limit()
        #print("search limit info: ", limitInfo.search)
        if limitInfo.search.remaining < 1:
            timeUntilReset = limitInfo.search.reset-datetime.datetime.now()
            print(datetime.datetime.now(), " - Waiting for rate limit: " + str(timeUntilReset) + " until " + str(limitInfo.search.reset))
            time.sleep(timeUntilReset.total_seconds()+10)

    def waitForCoreRateLimitIfNeeded(self):
        """ Searches before the core rate limit kicks in. """
        limitInfo = self.github.get_rate_limit()
        #print("core limit info: ", limitInfo.core)
        if limitInfo.core.remaining < 1:
            timeUntilReset = limitInfo.core.reset-datetime.datetime.now()
            print(datetime.datetime.now(), " - Waiting for rate limit: " + str(timeUntilReset) + " until " + str(limitInfo.core.reset))
            time.sleep(timeUntilReset.total_seconds()+10)

    def repoForNameAndOwner(self, ownerSlashRepo, attempt=1):
        try:
            self.waitForCoreRateLimitIfNeeded()
            repo = self.github.get_repo(ownerSlashRepo)
            self.waitForCoreRateLimitIfNeeded()
            file = repo.get_contents("/Package.swift")
            return (repo, file)
        except github_api.UnknownObjectException as error:
            print(ownerSlashRepo + " does not exist or is not a Swift Package.")
            return None
        except:
            return None

    def topicsFor(self, repo):
        self.waitForCoreRateLimitIfNeeded()
        return repo.get_topics()

    def getRenderedReadme(self, repo, repoPath):
        self.getReadme(repo, repoPath)
        self.renderReadme(repo, repoPath)

    def getReadme(self, repo, repoPath):
        readme = repo.get_readme() # the actual api supports fetching rendered HTML but not PyGithub.
        path = os.path.join(repoPath,'README.md')
        with open(path, "wb+") as f:
            self.waitForCoreRateLimitIfNeeded()
            content = base64.b64decode(readme.content)
            f.write(content)

    def renderReadme(self, repo, repoPath):

        mdFile = io.open(os.path.join(repoPath,'README.md'), mode="r", encoding="utf-8")
        markdown = mdFile.read()
        mdFile.close()

        htmlFile = io.open(os.path.join(repoPath,'README.html'), mode="w+", encoding="utf-8")
        self.waitForCoreRateLimitIfNeeded()
        readmeHTML = self.github.render_markdown(markdown, context=repo)
        readmeHTML = stripBreakTag(readmeHTML)
        htmlFile.write(readmeHTML)
        htmlFile.close()


def main():
    api = GithubPackages()
    for i in range(40):
        print('request', i, 'requests left:', api.github.rate_limiting[0])
        api.repoForNameAndOwner('apple/swift-nio')

if __name__ == '__main__':
	main()
