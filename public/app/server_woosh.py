# server_whoosh.py
# Name: Joseph Van Boxtel & (James) Toan Minh Do
# CS 483 - Final Project
# December 6th, 2019
# Dr. Ben McCamish

from flask import Flask, render_template, redirect, url_for, request
import jinja2
import os
import sys
sys.path.append('./services/')
from index import MyWhooshIndexer
from package import Package
from searcher import *

# Initialize flask, jinja2, paths to packages directory
app = Flask(__name__)
here = os.path.dirname(__file__)
my_loader = jinja2.FileSystemLoader([here+'/services/data/packages', here+'/templates'])
app.jinja_loader = my_loader

# Landing page
@app.route('/')
def index():
    # Fetch 5 suggested packages and render them to landing page
    packages = mySearcher.getSuggested(5)
    return render_template('index.html', packages=packages)

# Handles POST requests
def parameterData(request):
    if request.method == 'POST':
        return request.form
    else:
        return request.args

def pageFromRequestData(data):
    try:
        return max(int(data.get('page', 1)), 1)
    except ValueError:
        print("Can't use page")
        return 1

# Page Navigation function
# Provides correct href for each buttons and calculates total pages available
def pageInfoForResults(pageCount, page, pageSize=10):
    pageInfo = dict()
    pageInfo['page'] = page
    pageInfo['next'] = page + 1 if page < pageCount else None
    pageInfo['prev'] = page - 1 if page > 1 else None
    print(pageCount)
    otherPages = list(range(max(1, page-2), min(page+2, pageCount)+1))
    if not 1 in otherPages:
        otherPages = [1] + otherPages
    pageInfo['otherPages'] = otherPages
    return pageInfo

# Initiate search with user query and renders the returned results from whoosh
def returnResults(query, page):
    (results, pageCount, totalCount) = mySearcher.search(query, page)
    pageInfo = pageInfoForResults(pageCount, page)

    return render_template('results.html', query=query, totalCount=totalCount, packages=results, pageInfo=pageInfo)

# Fetches the user's parameters and parse them to returnResults function for rendering
@app.route('/results', methods=['GET', 'POST'])
def results():
    # grab the parameters
    data = parameterData(request)
    query = data.get('searchterm')
    page = pageFromRequestData(data)

    return returnResults(query, page)

# Renders the Advanced Search page
@app.route('/advanced')
def advanced():
    return render_template('advanced.html')

# Fetches the advanced search parameters, build the appropriate query and parse it to returnResults function
@app.route('/adv_results', methods=['GET', 'POST'])
def adv_results():
    # grab the parameters
    data = parameterData(request)
    page = pageFromRequestData(data)
    owner = data.get('owner')
    name = data.get('searchterm','')
    dependencies = data.get('dependsOn','')
    swiftVersion = data.get('swiftVer','')
    starsMin = data.get('starsMin','')
    starsMax = data.get('starsMax','')

    queryString = mySearcher.buildAdvQueryString(owner, name, dependencies, swiftVersion, starsMin, starsMax)
    return returnResults(queryString, page)

# Renders the About page
@app.route('/about')
def about():
    return render_template('about.html')

# Returns the proper path to the package's readme file in the database 
def readmeHTMLPath(package):
    return 'services/data/packages/' + package.owner + '/' + package.name

# Loads and renders the correct details page of the package
# Returns an error page if the package is not found
@app.route('/package/<owner>/<repo>/readme')
def packageDetails(owner, repo):
    try:
        pack = Package.load(repo, owner, 'services/data/packages/')
        return render_template('details.html', package=pack)
    except:
        link = "https://github.com/"+owner+'/'+repo
        message = 'We do not have this package on file. Check it out on GitHub.'
        return render_template('error.html', title="404 Not Found", message=message, link=link)

# Returns the GitHub's URL of the package's source repository 
@app.route('/package/<owner>/<repo>/<path:location>')
def gitHubRepoFile(owner, repo, location):
    return redirect('https://raw.githubusercontent.com/'+owner+'/'+repo+'/master/'+location)

# Fetches the appropriate owner's avatar from the database
# Returns a default avatar if no file is found
@app.route('/avatar/<owner>.png')
def ownerAvatar(owner):
    filename = 'images/'+owner+'.png'
    if os.path.exists('//public/app'+url_for('static', filename=filename)):
        return app.send_static_file(filename)
    else:
        return app.send_static_file('noavatar.png')

# Provides the correct query/URL for each 'tag' buttons
@app.route('/tags/<tag>')
def tagSearch(tag):
    print('redirecting for tagSearch')
    query = 'tags:' + tag
    return redirect(url_for('results', searchterm=query))

# Provides the correct query/URL for each 'dependencies' buttons
@app.route('/dependency/<path:fullName>')
def dependencyDetail(fullName):
    owner, repo = os.path.split(fullName)
    print('redirecting for dependencyDetail')
    return redirect(url_for('packageDetails', owner=owner, repo=repo))

# Main
if __name__ == '__main__':
    # Init a global searcher val
    global mySearcher
    # Call MyWhooshServer function with proper the database's index and path to the packages directory
    mySearcher = MyWhooshSearcher(MyWhooshIndexer(), '//public/app/services/data/packages')
    mySearcher.prepare()
    # Specify the port for the site
    port = int(os.environ.get('PORT', 5000))#environ returns a string
    print("Starting on port: "+ str(port))
    app.run(host='0.0.0.0', port=port, debug=True)
