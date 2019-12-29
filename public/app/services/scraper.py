# scraper.py
# Name: Joseph Van Boxtel & (James) Toan Minh Do
# CS 483 - Final Project
# December 6th, 2019
# Dr. Ben McCamish

import os
import shutil
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
from githubPackages import *
from index import packagesIn,listSubdirPaths

def ensureParentDirsExist(dirsPath):
    """ Create directories if they don't exist yet. Don't pass a path to a file. """
    print('dirsPath', dirsPath)
    if not os.path.exists(dirsPath):
        os.makedirs(dirsPath)

def ensureParentDirsExistForFile(filePath):
    """ Create directories if they don't exist yet. """
    ensureParentDirsExist(os.path.dirname(filePath))

def parseManifest(localRepoPath):
    """ returns a list of dependency (ownerName, repoName) tuples """

    manifestFile = io.open(os.path.join(localRepoPath,'Package.swift'), mode="r", encoding="utf-8")
    manifestContent = manifestFile.read()
    manifestFile.close()

    dependencyPairs = dependencyOwnerRepoPairsIn(manifestContent)
    swiftVersion = swiftVersionInManifest(manifestContent)

    return (dependencyPairs, swiftVersion)

def swiftVersionInManifest(manifestContent):
    match = re.search('swift-tools-version:(.*)', manifestContent)
    if match:
        return match.group(1)
    else:
        # It is definitely possible that some packages don't have swift version specified.
        return None

def dependencyOwnerRepoPairsIn(string):
    """ Find urls that match the form they show up in the Package.swift file.
    dependencies: [
        .package(url: "https://github.com/apple/swift-nio", from: "2.0.0"),
    ]
    Notice that repo URLs always have just two components after the host.
    """
    gitHubIdentifier = '[A-Za-z0-9_.-]+'
    owner = '('+gitHubIdentifier+')'
    repo = '('+gitHubIdentifier+')'
    matchIterator = re.finditer('//github.com/' + owner + '/' + repo + '"', string)

    dependencies = list()
    for ownerRepoPair in matchIterator:
        # 0 is the full match.
        author = ownerRepoPair[1]
        name = ownerRepoPair[2]

        # Sometimes dep URLs include .git and sometimes they don't.
        name = stripDotGit(name)

        dependencies.append((author, name))
    return dependencies

def stripDotGit(repoName):
    if repoName[-4:] == '.git':
        return repoName[:-4]
    return repoName

# def fetchAvatar(repo, localPath):
#     # limiting the size can save as much as 8x in disk space.
#     avatarLink = repo.owner.avatar_url+'&s=50'
#     print("Avatar from: ", avatarLink)
#     ensureParentDirsExistForFile(localPath)
#     with open(localPath, 'wb') as file:
#         req = requests.get(avatarLink)
#         file.write(req.content)

def scrapePackage(searchResultFile, github, repoPath, ownerPath):
    repo = searchResultFile.repository
    print(repo.full_name)

    ensureParentDirsExist(repoPath)

    # Work with the Package.swift file
    github.storePackageManifest(searchResultFile, repoPath)
    dependencyPairs, swiftVersion = parseManifest(repoPath)
    #print('swift version:', swiftVersion)
    # Work with the README
    try:
        github.getRenderedReadme(repo, repoPath)
    except github_api.GithubException:
        print("A github readme op failed.")

    # Get the fields from the repo object
    repoName = repo.full_name.split('/')[1]
    ownerName = repo.full_name.split('/')[0]
    description = repo.description
    readmeMD = ''
    starCount = repo.stargazers_count
    tags = github.topicsFor(repo)
    github.fetchAvatar(repo, "//public/app/static/" + ownerPath)
    lastCommit = repo.pushed_at

    return Package(repoName, ownerName, dependencyPairs, description, readmeMD, starCount, tags, ownerPath, lastCommit, swiftVersion)

def scrapeRepo(manifestFile, repo, github, packagesPath):
    repoPath = os.path.join(packagesPath, repo.full_name)
    ownerPath = os.path.join("images", repo.owner.login + ".png")
    package = scrapePackage(manifestFile, github, repoPath, ownerPath)
    package.save(packagesPath)

    # Now upload to S3 because the file system isn't persistent on Heroku.
    s3Storage.upload_dir(repoPath, 'packages/'+repo.full_name)
    return package

def retrieveContinationOrDefault(progressPath):
    try:
        s3Storage.download_dir('progress', progressPath)

        dirContents = list(os.listdir(os.path.join(progressPath,'progress')))
        #print('dirContents', dirContents)
        mostRecentProgressFilePath = sorted(dirContents)[-1]
        #print('mostRecent', mostRecentProgressFilePath)
        mostRecentRangeMin = int(os.path.split(mostRecentProgressFilePath)[1])
        return mostRecentRangeMin + 50
    except Exception as e:
        print('Could not resume', e)
        return 150

def main():
    github = GithubPackages()

    packagesPath = '//public/app/services/data/packages'

    # Rate limited to 30 requests per minute for search. Each request contains 30 items.
    # That results in 900 repositories per minute.
    # In practice I seem to get page 22 (600ish repositories) before rate-limiting begins.
    # Note each search is limited to 1000 results.

    count = 0
    redundantCount = 0
    # both of these hold "owner/repo" strings
    yetToFetch = set()
    fetched = set()#packagesIn(packagesPath))
    #print('already know about ', fetched)


    def queueUpDependenciesOfPackage(package):
        #print("Also need dependenices of " + package.name + " ")
        for owner, name in package.dependencies:
            ownerSlashRepo = owner + '/' + name
            if ownerSlashRepo not in fetched:
                yetToFetch.add(ownerSlashRepo)

    def processRepo(repo, manifestFile):
        nonlocal count
        nonlocal redundantCount
        if repo.full_name in fetched:
            redundantCount += 1
            return
        fetched.add(repo.full_name)
        try:
            package = scrapeRepo(manifestFile, repo, github, packagesPath)
            queueUpDependenciesOfPackage(package)
            count += 1
            print('count:', count)
        except Exception as e:
            print('Exception during processing a repo: ', e)
            return
            # Anything that went wrong with this package will cause it to be thrown out.

    def processBatchOfRepos(reposAndManifests, path, name):
        localPath = os.path.join(path, name)
        with open(localPath, 'w') as f:
            for repo, file in reposAndManifests:
                processRepo(repo, file)
                print(repo.full_name, file=f)

        s3Storage.upload_file(localPath, 'progress/'+name)
        s3Storage.upload_dir('//public/app/static/images', 'images')
        shutil.rmtree('//public/app/static/images')
        os.makedirs('//public/app/static/images')

    progressPath = os.path.join(packagesPath, '_progress_')
    ensureParentDirsExist(progressPath)
    startValue = retrieveContinationOrDefault(progressPath)
    try:
        for minSize in range(startValue, 1500, 50):
            processBatchOfRepos(github.reposForManifestFileSize(minKiloByteSize=minSize, maxKiloByteSize=minSize+50), progressPath, str(minSize))
        # 1500 Empirical value that makes < 1000 results
        processBatchOfRepos(github.reposForManifestFileSize(minKiloByteSize=1500), progressPath, '1500')

    except Exception as e:
        # ensure the images are uploaded.
        print('Exeption while searching: ', e)

    # Re-uploading is worth the extra stability.
    s3Storage.upload_dir('//public/app/static/images', 'images')
    shutil.rmtree('//public/app/static/images')
    os.makedirs('//public/app/static/images')

    print('Hit Rate limit: ', github.rateLimitsHit)

if __name__ == '__main__':
	main()
