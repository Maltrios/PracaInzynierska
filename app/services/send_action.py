import requests

def send_action(user_id, action_type):
    url = "http://localhost:8081/action"
    # url = "http://action-service:8081/action"
    payload = {
        "user_id": user_id,
        "action_type": action_type
    }
    response = requests.post(url, json=payload)

    if response.status_code >= 400:
        try:
            msg_error = response.json().get("error", response.text)
        except ValueError:
            msg_error = response.text

        raise Exception(f"[Error] {response.status_code}: {msg_error}")
    return response.text

