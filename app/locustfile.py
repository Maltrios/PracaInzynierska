from locust import HttpUser, task, between
import requests

requests.packages.urllib3.disable_warnings()
class MyApiUser(HttpUser):
    wait_time = between(1, 3)

    email = "user@example.com"
    password = "Password1!"

    @task(2)
    def login(self):
        self.client.post("/auth/login", json={"email": self.email, "password": self.password}, verify=False)

    def get_user_info(self):
        response = self.client.post("/auth/login", json={"email": self.email, "password": self.password}, verify=False)

        token = response.json()["access_token"]

        if token:
            with open("csvFIle/drug200.csv", "rb") as file:
                self.client.post("/file/upload-csv/show_column",
                    files={"file": ("drug200.csv", file, "text/csv")},
                    headers={"Authorization": f"Bearer {token}"})