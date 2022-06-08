import os
import json
import requests

from notion.client import NotionClient
from md2notion.upload import upload

# Data from GitHub environment
EVENT_PATH = os.environ.get("GITHUB_EVENT_PATH")

API_TOKEN = os.environ.get("NOTION_API_TOKEN")
USER_TOKEN = os.environ.get("USER_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")
BRACKET_TYPES = os.environ.get("BRACKET_TYPES")

ISSUE_STATES = {
    "opened": "Запланировано",
    "closed": "Сделано",
    "reopened": "Запланировано",
}

BRACKETS = {
    "1": {
        "left_bracket": "(",
        "right_bracket": ")",
    },
    "2": {
        "left_bracket": "[",
        "right_bracket": "]",
    },
    "3": {
        "left_bracket": "{",
        "right_bracket": "}",
    },
}

LB = BRACKETS[BRACKET_TYPES]["left_bracket"]
RB = BRACKETS[BRACKET_TYPES]["right_bracket"]


def create_page(title: str, number: str, labels: dict) -> dict:
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
                            "content": f"{title} {LB}#{number}{RB}",
                        },
                    }
                ],
            },
            "Тип": {"select": {"name": "Задача"}},
            "Статус": {"select": {"name": ISSUE_STATES["opened"]}},
            "Вид": {"multi_select": [{"name": label["name"] for label in labels}]},
        },
    }
    headers = {
        "Accept": "application/json",
        "Notion-Version": "2022-02-22",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_TOKEN}",
    }

    response = requests.post(url, json=payload, headers=headers)

    return json.loads(response.text)


def update_page():
    pass


def get_page(issue_number: str):
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    payload = {
        "filter": {
            "property": "title",
            "rich_text": {"ends_with": f"{LB}#{issue_number}{RB}"},
        },
    }
    headers = {
        "Accept": "application/json",
        "Notion-Version": "2022-02-22",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_TOKEN}",
    }

    response = requests.post(url, json=payload, headers=headers)

    results = json.loads(response.text)["results"]
    pages_amount = len(results)

    if pages_amount != 1:
        raise ValueError(
            f"Cannot find a specific page. Number of pages found: {pages_amount}."
            f"Urls are: {', '.join([page['url'] for page in results])}"
        )
    else:
        return results[0]


def set_body(url: str, body: str):
    client = NotionClient(token_v2=USER_TOKEN)
    page_block = client.get_block(url)

    with open("body.md", "w") as f:
        f.write(body)

    with open("body.md", "r", encoding="utf-8") as md:
        upload(md, page_block)


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
    issue_labels = EVENT_JSON["issue"]["labels"]
    issue_body = EVENT_JSON["issue"]["body"]

    if action_type == "opened":
        r = create_page(issue_title, issue_number, issue_labels)
        print('/' * 10)
        print(r)
        set_body(r["url"], issue_body)
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


if __name__ == "__main__":
    main()
