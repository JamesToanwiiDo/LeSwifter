# CS-483-FProject
## Final Project for CS 483 Web Data

## Swift Package Database
Created by: Joseph Van Boxtel & Toan Minh Do
December 6, 2019

### Introduction
The purpose of this project is to form a database of packages written with the Swift Programming Language. Our team is using the following development tools & APIs: Python, Whoosh!, Bootstrap, and PyGithub.

### Describing the Features
1. Parse and Link Dependencies
The Package.swift file states the dependencies on other packages. The related dependencies and its links will also be displayed alongside the returned package. Users can also view the repositories of the dependencies via the linked URLs. The Swift compiler can be configured to output the AST structure of the Package.swift file in JSON format. Then we pluck the dependencies from the JSON.

2. Dependency Search
Search such as “dependsOn: Vapor” will be supported. The results would be packages that depend on a project matching the search term “Vapor”. UI will make this type of search easy and discoverable. Such search would be helpful for server-side devs because the community is partially split between Vapor (open source) and IBM’s Kitura for web server functionality.

3. Search by Compatibility
Search will allow choosing a specific Swift version. Only results matching that filter would be considered. This would use a similar parse mechanism as above.

4. README.md rendering
The detail page for each repository will feature a rendered version of the README just like on Github. This saves users the click through to Github. Implemented using a library like this to convert Github’s MD to HTML.

### Describing the Dataset
The dataset consists of all (many of) the Swift Packages that are hosted on GitHub. Each repository will be represented by its Package.swift and README.* files. A document will refer to the combination of those two and some links to the repository.


## Launching with Docker
We provide the system pre-indexed and ready to go in this zip.
Prepare the image(one-time, or as changes if not mounting):

```
docker build -f ./Dockerfile.web -t le-swifter:latest .
```
Launch the server like this.
```
docker run -it -p 5000:5000 --env-file .env le-swifter:latest
```
Or if you would like to mount the current version of public for hot reloading:
```
docker run -it -v "$(pwd)"/public:/public -p 5000:5000 --env-file .env le-swifter:latest
```

### Building the Dataset

The Dockerfile specifies python3 as the entrypoint for the web service.
The default command is server_woosh.py. To use one of the other programs add their path to the end of the `docker run` command.

### Scraper
This reads from the GitHub API and parses the packages. It stores the database in a folder structure in the `/public/app/services/data/packages` folder. The owner avatars go in the `/public/app/static/images` folder. Running the scraper will erase the local images folder, so only run it if the local directory is not mounted. It also uploads to S3 but that should just overwrite the contents for each specific package so that is not a concern. Keep in mind it takes 16 hours to complete the scraper.
To use the scraper:
```
docker run -it --env-file .env le-swifter:latest services/scraper.py
```

### Indexer
This reads the folder structure left from the scraper and creates the Whoosh index. This is the point where the HITS-style scoring takes place.
The indexer takes about 3 minutes. Although there is an up-to-date version of the index.
The indexer should not have any ill effects it it is allowed to complete.
To run the index:
```
docker run -it --env-file .env le-swifter:latest services/index.py
```
