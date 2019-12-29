import boto3
import os

s3_client = boto3.client('s3')

def upload_dir(local, destPrefix='', bucket='le-swifter-production', client=s3_client):
    for fileName in os.listdir(local):
        path = os.path.join(local, fileName)
        if os.path.isdir(path):
            # Recursive because our use case is only a few levels deep.
            upload_dir(path, destPrefix+'/'+fileName, bucket, client)
        else:
            upload_file(path, destPrefix+'/'+fileName, bucket, client)

def upload_file(local, dest, bucket='le-swifter-production', client=s3_client):
    #print("Uploading " + local + ' to ' + dest)
    client.upload_file(local, bucket, dest)

# https://stackoverflow.com/questions/31918960/boto3-to-download-all-files-from-a-s3-bucket
def download_dir(prefix, local, bucket='le-swifter-production', client=s3_client):
    """
    params:
    - prefix: pattern to match in s3
    - local: local path to folder in which to place files
    - bucket: s3 bucket with target contents
    - client: initialized s3 client object
    """
    keys = []
    dirs = []
    next_token = ''
    base_kwargs = {
        'Bucket':bucket,
        'Prefix':prefix,
    }

    while next_token is not None:
        kwargs = base_kwargs.copy()
        if next_token != '':
            kwargs.update({'ContinuationToken': next_token})
        results = client.list_objects_v2(**kwargs)
        contents = results.get('Contents')
        if contents != None:
            for file in contents:
                if isDir(file):
                    #print("Found dir " + file.get('Key'))
                    dirs.append(file.get('Key'))
                else:
                    #print("Found file " + file.get('Key'))
                    keys.append(file.get('Key'))

        next_token = results.get('NextContinuationToken')

    for d in dirs:
        dest_pathname = os.path.join(local, d)
        if not os.path.exists(os.path.dirname(dest_pathname)):
            os.makedirs(os.path.dirname(dest_pathname))

    for fileKey in keys:
        dest_pathname = os.path.join(local, fileKey)
        if not os.path.exists(os.path.dirname(dest_pathname)):
            os.makedirs(os.path.dirname(dest_pathname))
        #print('downloading: ' + fileKey + ' to ' + dest_pathname)
        client.download_file(bucket, fileKey, dest_pathname)

def isDir(fileObj):
    """ Directories are represented as files that end with a slash `/` """
    k = fileObj.get('Key')
    return k[-1] == '/'

def main():
    print(os.environ.get('AWS_ACCESS_KEY_ID', 'No AWS_ACCESS_KEY_ID'))
    print(os.environ.get('AWS_SECRET_ACCESS_KEY', 'No AWS_SECRET_ACCESS_KEY'))
    #download_dir('', '//public/app/services/data', 'le-swifter-production')
    upload_dir('//public/app/services/data', '', 'le-swifter-production')

if __name__ == '__main__':
	main()
