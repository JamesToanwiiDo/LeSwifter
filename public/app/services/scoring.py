# scoring.py
# Name: Joseph Van Boxtel & (James) Toan Minh Do
# CS 483 - Final Project
# December 6th, 2019
# Dr. Ben McCamish

from math import sqrt

def buildDepGraph(packagesByFullName):
    """ Build two dictionaries keyed by full name. One in each direction. """
    downGraph = dict()
    upGraph = dict()
    for fullName in packagesByFullName:
        package = packagesByFullName[fullName]
        downPackages = list()
        for owner, name in package.dependencies:
            depFullName = owner + '/' + name

            downPackages.append(depFullName)

            # fullName depends on depFullName
            upGraph[depFullName] = upGraph.get(depFullName, []) + [fullName]

        downGraph[fullName] = downPackages
    return (upGraph, downGraph) # fullName to dependencies

def normalize(scoreByName):
    """ Mutate the dictionary so the sum of squares is equal to 1 """
    totalScore = 0
    for score in scoreByName.values():
        totalScore += score**2
    print('Total Score Sum: ', totalScore)
    totalScore = sqrt(totalScore)
    for name, score in scoreByName.items():
        scoreByName[name] = score / totalScore

def hitsStyleScores(packagesByFullName, depGraph):
    upGraph, downGraph = depGraph
    # 20 iterations
    hubScores = dict() # fullName to score
    authScores = dict() # fullName to score

    for i in range(20):
        for fullName in packagesByFullName.keys():
            hubScore = 0
            for dependency in downGraph.get(fullName, []):
                hubScore += authScores.get(dependency, 1)
            hubScores[fullName] = hubScore
        # Normalize each score so they all sum to 1.
        # This ensures the values converge.
        normalize(hubScores)

        for fullName in packagesByFullName.keys():
            authScore = 0
            for dependent in upGraph.get(fullName, []):
                authScore += hubScores.get(dependent, 1)
            authScores[fullName] = authScore

        normalize(authScores)

    return (hubScores, authScores)

if __name__ == '__main__':
    import operator
    from package import loadAllPackages

    packagesPath = '//public/app/services/data/packages'
    packagesByName = loadAllPackages(packagesPath)
    depGraph = buildDepGraph(packagesByName)
    hScores, aScores = hitsStyleScores(packagesByName, depGraph)
    top50Hubs = sorted(hScores.items(), key=operator.itemgetter(1), reverse=True)[:50]
    top50Auths = sorted(aScores.items(), key=operator.itemgetter(1), reverse=True)[:50]
    print("Top 50 Hubs")
    for hub in top50Hubs:
        print(hub)
    print("Top 50 Auths")
    for auth in top50Auths:
        print(auth)
