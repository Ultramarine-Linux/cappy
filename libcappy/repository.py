import requests
import json
import platform

# Copr repo management for libcappy.
# This is essentially a wrapper around the Copr API so that we can actually easily manage Copr repos.
class Copr:
    def __init__(self):
        self.request = requests.Session()
    def list_projects(self,page_amount=100,page=1,copr_url='https://copr.fedorainfracloud.org', search:str =None):
        """[summary]
        Lists copr repos as a list of dictionaries.

        Returns: List of Copr projects as a dictionary, included with the full details of the project

        Arguments:
        page_amount: int, the amount of project to fetch for each page
        page: int, the page to fetch
        copr_url: string, the Copr API URL
        """
        if search != None:
            query = search
        else:
            query = platform.machine()
        params = {
            'limit': page_amount,
            'offset': page_amount * (page - 1),
            'search_query': query
        }
        # Get the latest X projects from the Copr API
        response = self.request.get(copr_url + '/api_2/projects', params=params)
        # Parse the response
        try:
            response.raise_for_status()
            return response.json()['projects']
        except requests.exceptions.HTTPError as e:
            print(e)
    def get_repo(self, copr, chroot, copr_url='https://copr.fedorainfracloud.org'):
        """[summary]
        Fetches the Copr repo file from Copr
        Returns: The Repo file as a string

        Arguments:

        copr: string, the Copr project path
        Example: cappyishihara/ultramarine

        chroot: string, the chroot to fetch the repo for
        Example: fedora-35-x86_64

        copr_url: string, the Copr API URL

        """
        # check format of copr if it follows the format of xxx/yyy
        if '/' in copr:
            path = copr.split('/')
            username = path[0]
            projectname = path[1]
        else:
            return None
        # Get the repo file from the Copr API
        response = self.request.get(f'{copr_url}/coprs/{username}/{projectname}/repo/{chroot}/{username}-{projectname}-{chroot}.repo')
        return response.text