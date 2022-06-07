import os
import json
import requests

# Data from GitHub environment
EVENT_PATH = os.environ.get("GITHUB_EVENT_PATH")
TOKEN = os.environ.get("NOTION_API_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

STATE_OPENED = os.environ.get("STATE_OPENED")
STATE_CLOSED = os.environ.get("STATE_CLOSED")
STATE_REOPENED = os.environ.get("STATE_REOPENED")


def create_issue(title, number):
    url = "https://api.notion.com/v1/pages"

    payload = {
        "parent": {
            "type": "database_id",
            "database_id": DATABASE_ID,
        },
        "properties": {
            "Задачи": {
                "id": "title",
                "type": "title",
                "title": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"{title} #{number}",
                        },
                    }
                ],
            },
            "Тип": {"select": {"name": "Задача"}},
            "Статус": {"select": {"name": {STATE_OPENED}}},
            # "Вид": {"multi_select": [{"name": "Баг"}]},
        },
    }
    headers = {
        "Accept": "application/json",
        "Notion-Version": "2022-02-22",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    }

    response = requests.post(url, json=payload, headers=headers)


def get_issue():
    pass


def update_issue():
    pass


# TO DO
# def get_issue_body():
#     pass


def main():
    with open(EVENT_PATH, "r") as f:
        EVENT_STR = f.read()

    EVENT_JSON = json.loads(EVENT_STR)

    print("-" * 10, "TEST", "-" * 10)
    print(EVENT_JSON)
    print("-" * 10, "TEST", "-" * 10)

    action_type = EVENT_JSON["action"]
    issue_title = EVENT_JSON["issue"]["title"]
    issue_number = EVENT_JSON["issue"]["number"]

    GITHUB_TO_NOTION_ISSUE_STATES = {
        "opened": STATE_OPENED,
        "closed": STATE_CLOSED,
        "reopened": STATE_REOPENED,
    }

    if action_type == "opened":
        create_issue(issue_title, issue_number)
    else:
        if action_type == "edited":
            pass
        elif action_type == "closed":
            pass
        elif action_type == "deleted":
            pass
        elif action_type == "reopened":
            pass
        elif action_type == "labeled" or action_type == "unlabeled":
            pass


main()
