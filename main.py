import os
import json
import requests

from utils import parse_env_variables_to_properties

# Payload from GitHub event webhook
EVENT_PATH = os.environ.get("GITHUB_EVENT_PATH")

# Github secrets and environment variables
BRACKET_TYPE = os.environ["BRACKET_TYPE"]
DATABASE_ID = os.environ["DATABASE_ID"]
DEBUGGING = os.environ.get("DEBUGGING")
NOTION_API_TOKEN = os.environ["NOTION_API_TOKEN"]

ASSIGNEES_PROPERTY_NAME = os.environ["ASSIGNEES_PROPERTY_NAME"]
LABELS_PROPERTY_NAME = os.environ["LABELS_PROPERTY_NAME"]
STATUS_PROPERTY_NAME = os.environ["STATUS_PROPERTY_NAME"]
TITLE_PROPERTY_NAME = os.environ["TITLE_PROPERTY_NAME"]

CUSTOM_PROPERTIES = parse_env_variables_to_properties()

if DEBUGGING:
    print(
        os.environ["GH_ASSIGNEES_TO_NOTION"],
        os.environ["GH_STATUSES_TO_NOTION"],
        CUSTOM_PROPERTIES,
        sep="\n-----\n",
    )

GH_ASSIGNEES_TO_NOTION = json.loads(os.environ["GH_ASSIGNEES_TO_NOTION"])
GH_STATUSES_TO_NOTION = json.loads(os.environ["GH_STATUSES_TO_NOTION"])

# Authentication
HEADERS = {
    "Accept": "application/json",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {NOTION_API_TOKEN}",
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
    issue_labels: list,
    issue_assignees: list,
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
            ASSIGNEES_PROPERTY_NAME: {
                "id": "%24v1Q",
                "type": "people",
                "people": [
                    {"id": GH_ASSIGNEES_TO_NOTION[assignee]}
                    for assignee in issue_assignees
                ],
            },
        },
    }

    if issue_labels:
        payload["properties"][LABELS_PROPERTY_NAME] = {
            "multi_select": [{"name": label["name"]} for label in issue_labels]
        }
    if not page:
        payload["properties"][STATUS_PROPERTY_NAME] = {
            "status": {"name": GH_STATUSES_TO_NOTION["opened"]}
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


def get_page(issue_number: str) -> dict:
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


def patch_page(page, payload: dict) -> None:
    url = "https://api.notion.com/v1/pages/" + page["id"]
    payload = {**PARENT, **payload}
    response = requests.patch(url, json=payload, headers=HEADERS)

    if DEBUGGING:
        print("/" * 10, "UPDATE LABELS RESPONSE", "/" * 10)
        print(response.text)
        print("/" * 10, "UPDATE LABELS RESPONSE", "/" * 10)


def update_labels(page: dict, labels: list) -> None:
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
            STATUS_PROPERTY_NAME: {"status": {"name": GH_STATUSES_TO_NOTION["closed"]}},
        },
    }
    payload = {**PARENT, **payload}
    patch_page(page, payload)


def reopen_issue(page: dict) -> None:
    payload = {
        "properties": {
            STATUS_PROPERTY_NAME: {
                "status": {"name": GH_STATUSES_TO_NOTION["reopened"]}
            },
        },
    }
    payload = {**PARENT, **payload}
    patch_page(page, payload)


def delete_page(page: dict) -> None:
    payload = {"archived": True}
    payload = {**PARENT, **payload}
    patch_page(page, payload)


def update_assignees(page, issue_assignees: list) -> None:
    payload = {
        "properties": {
            ASSIGNEES_PROPERTY_NAME: {
                "id": "%24v1Q",
                "type": "people",
                "people": [
                    {"id": GH_ASSIGNEES_TO_NOTION[assignee]}
                    for assignee in issue_assignees
                ]
                if issue_assignees
                else [],
            },
        },
    }
    payload = {**PARENT, **payload}
    patch_page(page, payload)


def set_body(page: dict) -> None:
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
    issue_assignees = [
        assignee["login"] for assignee in EVENT_JSON["issue"]["assignees"]
    ]

    if action_type == "opened":
        page = create_or_update_page(
            None, issue_title, issue_number, issue_labels, issue_assignees
        )
        set_body(page)
    else:
        page = get_page(issue_number)

        match action_type:
            case "edited":
                create_or_update_page(
                    page, issue_title, issue_number, issue_labels, issue_assignees
                )
            case "deleted":
                delete_page(page)
            case "closed":
                close_issue(page)
            case "reopened":
                reopen_issue(page)
            case "assigned" | "unassigned":
                update_assignees(page, issue_assignees)
            case "labeled" | "unlabeled":
                update_labels(page, issue_labels)
            case _:
                print("-" * 15, "WARNING", "-" * 15)
                print(f"Unsupported action type! Action: {action_type}")
                print("-" * 15, "WARNING", "-" * 15)


if __name__ == "__main__":
    main()
