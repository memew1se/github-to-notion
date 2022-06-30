import os
import json
import requests

# Data from GitHub environment
EVENT_PATH = os.environ.get("GITHUB_EVENT_PATH")

API_TOKEN = os.environ.get("NOTION_API_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")
BRACKET_TYPES = os.environ.get("BRACKET_TYPES")
PROJECT_NAME = os.environ.get("PROJECT_NAME")
AUTHORS_IDS = json.loads(os.environ.get("AUTHORS_IDS"))

HEADERS = {
    "Accept": "application/json",
    "Notion-Version": "2022-02-22",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_TOKEN}",
}

PARENT = {
    "parent": {
        "type": "database_id",
        "database_id": DATABASE_ID,
    }
}

# Property
ISSUE_STATES = {
    "opened": "Запланировано",
    "closed": "Сделано",
    "reopened": "Запланировано",
}

# Property
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
    "4": {
        "left_bracket": "<",
        "right_bracket": ">",
    },
    "5": {
        "left_bracket": "«",
        "right_bracket": "»",
    },
}

LB = BRACKETS[BRACKET_TYPES]["left_bracket"]
RB = BRACKETS[BRACKET_TYPES]["right_bracket"]


def create_or_update_page(
    page: dict or None, title: str, number: str, labels: dict, author: str
) -> dict:
    url = "https://api.notion.com/v1/pages/"

    payload = {
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
            "Ответственный": {
                "id": "%24v1Q",
                "type": "people",
                "people": [{"id": AUTHORS_IDS[author]}],
            },
        },
    }
    if PROJECT_NAME:
        payload["properties"]["Проект"] = {"select": {"name": PROJECT_NAME}}
    if labels:
        payload["properties"]["Вид"] = {
            "multi_select": [{"name": label["name"]} for label in labels]
        }
    if not page:
        payload["properties"]["Статус"] = {"select": {"name": ISSUE_STATES["opened"]}}

    payload = {**PARENT, **payload}

    if page:
        url = url + page["id"]
        response = requests.patch(url, json=payload, headers=HEADERS)
    else:
        response = requests.post(url, json=payload, headers=HEADERS)

    print("/" * 10, "CREATE OR UPDATE RESPONSE", "/" * 10)
    print(response.text)
    print("/" * 10, "CREATE OR UPDATE RESPONSE", "/" * 10)
    return json.loads(response.text)


def get_page(issue_number: str):
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    payload = {
        "filter": {
            "property": "title",
            "rich_text": {"ends_with": f"{LB}#{issue_number}{RB}"},
        },
    }

    response = requests.post(url, json=payload, headers=HEADERS)

    results = json.loads(response.text)["results"]
    pages_amount = len(results)

    if pages_amount != 1:
        raise ValueError(
            f"Cannot find a specific page. Number of pages found: {pages_amount}. "
            f"Urls are: {', '.join([page['url'] for page in results])}"
        )
    else:
        return results[0]


def update_labels(page: dict, labels: dict) -> None:
    url = "https://api.notion.com/v1/pages/" + page["id"]

    payload = {
        "properties": {
            "Вид": {"multi_select": [{"name": label["name"]} for label in labels]},
        },
    }

    payload = {**PARENT, **payload}
    response = requests.patch(url, json=payload, headers=HEADERS)

    print("/" * 10, "UPDATE LABELS RESPONSE", "/" * 10)
    print(response.text)
    print("/" * 10, "UPDATE LABELS RESPONSE", "/" * 10)


def update_status(page: dict) -> None:
    url = "https://api.notion.com/v1/pages/" + page["id"]

    payload = {
        "properties": {
            "Статус": {"select": {"name": ISSUE_STATES["closed"]}},
        },
    }

    payload = {**PARENT, **payload}
    response = requests.patch(url, json=payload, headers=HEADERS)

    print("/" * 10, "UPDATE STATUS RESPONSE", "/" * 10)
    print(response.text)
    print("/" * 10, "UPDATE STATUS RESPONSE", "/" * 10)


def delete_page(page: dict):
    url = "https://api.notion.com/v1/pages/" + page["id"]

    payload = {"archived": True}

    payload = {**PARENT, **payload}
    response = requests.patch(url, json=payload, headers=HEADERS)

    print("/" * 10, "DELETE RESPONSE", "/" * 10)
    print(response.text)
    print("/" * 10, "DELETE RESPONSE", "/" * 10)


def set_body(page: dict):
    pass


def main():
    with open(EVENT_PATH, "r") as f:
        EVENT_STR = f.read()

    EVENT_JSON = json.loads(EVENT_STR)

    print("-" * 15, "TEST", "-" * 15)
    print(EVENT_JSON)
    print("-" * 15, "TEST", "-" * 15)

    action_type = EVENT_JSON["action"]
    issue_title = EVENT_JSON["issue"]["title"]
    issue_number = EVENT_JSON["issue"]["number"]
    issue_labels = EVENT_JSON["issue"]["labels"]
    issue_author = EVENT_JSON["issue"]["assignee"]["login"]

    if action_type == "opened":
        page = create_or_update_page(
            None, issue_title, issue_number, issue_labels, issue_author
        )
        set_body(page)

    else:
        page = get_page(issue_number)

        if action_type == "edited":
            create_or_update_page(
                page, issue_title, issue_number, issue_labels, issue_author
            )

        elif action_type == "deleted":
            delete_page(page)

        elif action_type == "closed":
            update_status(page)

        elif action_type == "labeled" or action_type == "unlabeled":
            update_labels(page, issue_labels)

        else:
            print("-" * 15, "WARNING", "-" * 15)
            print(f"Unsupported action type! Action: {action_type}")
            print("-" * 15, "WARNING", "-" * 15)


if __name__ == "__main__":
    main()
