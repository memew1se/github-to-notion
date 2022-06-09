import os
import json
import requests

# Data from GitHub environment
EVENT_PATH = os.environ.get("GITHUB_EVENT_PATH")

API_TOKEN = os.environ.get("NOTION_API_TOKEN")
USER_TOKEN = os.environ.get("USER_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")
BRACKET_TYPES = os.environ.get("BRACKET_TYPES")

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


def create_page(page: dict or None, title: str, number: str, labels: dict) -> dict:
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
            "Статус": {"select": {"name": ISSUE_STATES["opened"]}},
        },
    }
    if labels:
        payload["properties"]["Вид"] = {
            "multi_select": [{"name": label["name"]} for label in labels]
        }

    payload = {**PARENT, **payload}

    if page:
        url = url + page["id"]
        response = requests.patch(url, json=payload, headers=HEADERS)
    else:
        response = requests.post(url, json=payload, headers=HEADERS)

    return json.loads(response.text)


def update_page(page: dict, title: str, number: str, labels: dict):
    return dict()


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


def update_labels(page: dict, labels: dict):
    url = "https://api.notion.com/v1/pages/" + page["url"]

    payload = {
        "properties": {
            "Вид": {"multi_select": [{"name": label["name"]} for label in labels]},
        },
    }

    payload = {**PARENT, **payload}
    requests.patch(url, json=payload, headers=HEADERS)


def delete_page(page: dict):
    pass


def set_body(url: str, body: str):
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
    issue_body = EVENT_JSON["issue"]["body"]

    if action_type == "opened":
        page = create_page(None, issue_title, issue_number, issue_labels)
        set_body(page["url"], issue_body)

    else:
        page = get_page(issue_number)

        if action_type == "edited":
            pass

        elif action_type == "deleted":
            delete_page(page)

        elif action_type == "labeled" or action_type == "unlabeled":
            update_labels(page, issue_labels)

        else:
            print("-" * 15, "WARNING", "-" * 15)
            print(f"Unsupported action type! Action: {action_type}")
            print("-" * 15, "WARNING", "-" * 15)


if __name__ == "__main__":
    main()
