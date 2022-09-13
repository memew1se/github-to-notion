import os
import json
import requests

from utils import parse_env_variables_to_properties

# Payload from GitHub event webhook
EVENT_PATH = os.environ.get("GITHUB_EVENT_PATH")

# Github secrets and environment variables
API_TOKEN = os.environ["NOTION_API_TOKEN"]
AUTHORS_IDS = json.loads(os.environ.get("AUTHORS_IDS"))
BRACKET_TYPE = os.environ["BRACKET_TYPE"]
DATABASE_ID = os.environ["DATABASE_ID"]
DEBUGGING = os.environ.get("DEBUGGING")

LABELS_PROPERTY_NAME = os.environ["LABELS_PROPERTY_NAME"]
STATUS_PROPERTY_NAME = os.environ["STATUS_PROPERTY_NAME"]
TITLE_PROPERTY_NAME = os.environ["TITLE_PROPERTY_NAME"]

GITHUB_STATUSES_TO_NOTION = json.loads(os.environ["GITHUB_STATUSES_TO_NOTION"])

CUSTOM_PROPERTIES = parse_env_variables_to_properties()

# Authentication
HEADERS = {
    "Accept": "application/json",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_TOKEN}",
}

# Database
PARENT = {
    "parent": {
        "type": "database_id",
        "database_id": DATABASE_ID,
    }
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
    "4": {
        "left_bracket": "<",
        "right_bracket": ">",
    },
    "5": {
        "left_bracket": "«",
        "right_bracket": "»",
    },
}

LB = BRACKETS[BRACKET_TYPE]["left_bracket"]
RB = BRACKETS[BRACKET_TYPE]["right_bracket"]

with open(EVENT_PATH, "r") as f:
    EVENT_JSON = json.loads(f.read())


def create_or_update_page(
    page: dict | None,
    issue_title: str,
    issue_number: str,
    issue_labels: dict,
    issue_assignee: str,
) -> dict:
    url = "https://api.notion.com/v1/pages/"
    payload = {
        "properties": {
            TITLE_PROPERTY_NAME: {
                "title": [
                    {
                        "text": {"content": f"{issue_title} {LB}#{issue_number}{RB}"},
                    }
                ],
            },
            "Ответственный": {
                "id": "%24v1Q",
                "type": "people",
                "people": [{"id": AUTHORS_IDS[issue_assignee]}],
            },
        },
    }

    if issue_labels:
        payload["properties"][LABELS_PROPERTY_NAME] = {
            "multi_select": [{"name": label["name"]} for label in issue_labels]
        }
    if not page:
        payload["properties"][STATUS_PROPERTY_NAME] = {
            "select": {"name": GITHUB_STATUSES_TO_NOTION["opened"]}
        }

    payload = {**PARENT, **payload}

    if page:
        url = url + page["id"]
        response = requests.patch(url, json=payload, headers=HEADERS)
    else:
        payload["properties"].update(CUSTOM_PROPERTIES)
        response = requests.post(url, json=payload, headers=HEADERS)

    if DEBUGGING:
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


def patch_page(page, payload: dict):
    url = "https://api.notion.com/v1/pages/" + page["id"]
    payload = {**PARENT, **payload}
    response = requests.patch(url, json=payload, headers=HEADERS)

    if DEBUGGING:
        print("/" * 10, "UPDATE LABELS RESPONSE", "/" * 10)
        print(response.text)
        print("/" * 10, "UPDATE LABELS RESPONSE", "/" * 10)


def update_labels(page: dict, labels: dict) -> None:
    payload = {
        "properties": {
            LABELS_PROPERTY_NAME: {
                "multi_select": [{"name": label["name"]} for label in labels]
            },
        },
    }
    payload = {**PARENT, **payload}
    patch_page(page, payload)


def close_issue(page: dict) -> None:
    payload = {
        "properties": {
            STATUS_PROPERTY_NAME: {
                "select": {"name": GITHUB_STATUSES_TO_NOTION["closed"]}
            },
        },
    }
    payload = {**PARENT, **payload}
    patch_page(page, payload)


def reopen_issue(page: dict) -> None:
    payload = {
        "properties": {
            STATUS_PROPERTY_NAME: {
                "select": {"name": GITHUB_STATUSES_TO_NOTION["reopened"]}
            },
        },
    }
    payload = {**PARENT, **payload}
    patch_page(page, payload)


def delete_page(page: dict):
    payload = {"archived": True}
    payload = {**PARENT, **payload}
    patch_page(page, payload)


def update_assignee(page, author: str):
    payload = {
        "properties": {
            "Ответственный": {
                "id": "%24v1Q",
                "type": "people",
                "people": [{"id": AUTHORS_IDS[author]}],
            },
        },
    }
    payload = {**PARENT, **payload}
    patch_page(page, payload)


def remove_assignee(page):
    payload = {
        "properties": {
            "Ответственный": {
                "id": "%24v1Q",
                "type": "people",
                "people": [],
            },
        },
    }
    payload = {**PARENT, **payload}
    patch_page(page, payload)


def set_body(page: dict):
    pass


def main():
    if DEBUGGING:
        print("-" * 15, "EVENT_JSON", "-" * 15)
        print(EVENT_JSON)
        print("-" * 15, "EVENT_JSON", "-" * 15)

    action_type = EVENT_JSON["action"]
    issue_title = EVENT_JSON["issue"]["title"]
    issue_number = EVENT_JSON["issue"]["number"]
    issue_labels = EVENT_JSON["issue"]["labels"]

    try:
        issue_author = EVENT_JSON["issue"]["assignee"]["login"]
    except TypeError as e:
        print("!" * 15, "ERROR", "!" * 15)
        print(e)
        print("!" * 15, "ERROR", "!" * 15)
        issue_author = ""

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
            close_issue(page)

        elif action_type == "reopened":
            reopen_issue(page)

        elif action_type == "assigned":
            update_assignee(page, issue_author)

        elif action_type == "unassigned":
            remove_assignee(page)

        elif action_type == "labeled" or action_type == "unlabeled":
            update_labels(page, issue_labels)

        else:
            print("-" * 15, "WARNING", "-" * 15)
            print(f"Unsupported action type! Action: {action_type}")
            print("-" * 15, "WARNING", "-" * 15)


if __name__ == "__main__":
    main()
