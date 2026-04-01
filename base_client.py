import requests

class BaseClient:
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def get(self, url):
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def post(self, url, data):
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()

    # Additional HTTP methods (put, delete) can be added similarly.