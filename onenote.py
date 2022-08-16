from dataclasses import dataclass
from typing import Dict
import requests
import app_config


@dataclass
class NoteBook:
    id: str
    self: str
    displayName: str
    sectionsUrl: str
    sectionGroupsUrl: str


@dataclass
class Section:
    isDefault: bool
    pagesUrl: str
    displayName: str


def notebooks(token: str):
    graph_data = requests.get(  # Use token to call downstream service
        f"{app_config.ENDPOINT}/me/onenote/notebooks",
        headers={'Authorization': 'Bearer ' + token['access_token']},
    ).json()
    return graph_data


def create_notebook(token: str, name: str):
    resp = requests.post(
        f"{app_config.ENDPOINT}/me/onenote/notebooks",
        headers={'Authorization': f'Bearer {token}'},
        json=dict(displayName=name)
    )

    return resp.status_code, resp.json()


def create_section(token: str, notebook_id: str, name: str):
    resp = requests.post(
        f"{app_config.ENDPOINT}/me/onenote/notebooks/{notebook_id}/sections",
        headers={'Authorization': f'Bearer {token}'},
        json=dict(displayName=name)
    )

    return resp.status_code, resp.json()


def create_page(token: str, section_url: str, data: Dict[str, bytes]):
    return requests.post(
        section_url,
        headers={
            'Authorization': f'Bearer {token}'
        },
        files=data
    ).json()


def get_page_content(token: str, page_content_url: str):
    return requests.get(
        page_content_url,
        headers={
            'Authorization': f'Bearer {token}'
        }
    ).content
