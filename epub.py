import base64
import os
import re
from dataclasses import dataclass
from typing import List

import lxml.html
import lxml.etree
from pynliner import Pynliner

container_file = "META-INF/container.xml"
mimetype_file = 'mimetype'
mimetype_css = 'text/css'
mimetype_epub = "application/epub+zip"


def get_opf_path(container: str) -> str:
    root = lxml.html.fromstring(container)
    return root[0][0].get("full-path")


@dataclass
class ManifestItem:
    item_id: str
    media_type: str
    href: str


def _load_mimetype(temp_dir):
    mimetype_path = os.path.join(temp_dir, mimetype_file)
    with open(mimetype_path) as myfile:
        return myfile.read()


def _is_epub(mimetype: str) -> bool:
    return mimetype_epub == mimetype.strip()


def load_opf(opf: str):
    root = lxml.html.fromstring(opf)
    manifest = root[1]
    manifests = dict()
    for item in manifest:
        item_id = item.get("id")
        media_type = item.get("media-type")
        href = item.get("href")
        m = ManifestItem(item_id, media_type, href)
        manifests[item_id] = m

    page_list = []
    for ref in root[2]:
        page_list.append(ref.get("idref"))
    return manifests, page_list


def _get_opf_file(container_file_path):
    with open(container_file_path) as container_file:
        opf_file = get_opf_path(container_file.read())
        return opf_file


def _load_opf_file(opf_file_path: str):
    with open(opf_file_path) as opf_file:
        opf = opf_file.read()
        return load_opf(opf)


def _load_nox_file(ncx_file_path: str):
    with open(ncx_file_path) as ncx_file:
        ncx_content = ncx_file.read()
        # print(ncx_content)
        return ncx_content


def is_css(item: ManifestItem) -> bool:
    return item.media_type == mimetype_css


def _get_css_files(manifests: List[ManifestItem]) -> List[str]:
    return [manifest.href for manifest in manifests if is_css(manifest)]


def _load_css_content(temp_dir, css_files: List[str]) -> str:
    css_content = ""
    for css_file in css_files:
        css_file_path = os.path.join(temp_dir, css_file)
        with open(css_file_path) as css_file:
            css_content += css_file.read()
    return css_content


def _load_page_content(temp_dir: str, page_file: str) -> str:
    page_path = os.path.join(temp_dir, page_file)
    with open(page_path) as page_file:
        page_content = page_file.read()
        return page_content


def _remove_css_link(page_content: str) -> str:
    return re.sub(r"<link .*>", "", page_content)


def css_inline(html: str, css: str) -> str:
    p = Pynliner()
    p.from_string(html).with_cssString(css)
    content = p.run()
    return content


def _image_inline(temp_dir, page_content: str) -> str:

    images = re.findall(r'xlink:href="(.*)"', page_content)
    # print(x)
    for image in images:
        image_file_path = os.path.join(temp_dir, image)
        with open(image_file_path, 'rb') as image_file:
            image_b64 = base64.b64encode(
                image_file.read())
            image_suffix = image.split(".")[-1]
            base64_image = f'data:image/{image_suffix};base64,{image_b64}'
            page_content = page_content.replace(
                image, base64_image)
    return page_content


def _img_inline(temp_dir, page_content: str):
    root = lxml.html.fromstring(page_content)
    images_svg = root.xpath("//*[local-name() = 'image']")
    files = dict()
    for i in images_svg:
        for k, v in i.items():
            if k.endswith('href'):
                image_src = v
                image_name = v

                if image_src.startswith("../"):
                    image_name = image_src[3:]
                image_suffix = image_name.split('.')[-1]
                image_block_name = image_name.replace("/", "_")
                i.set(k, f'name:{image_block_name}')
                image_path = os.path.join(temp_dir, image_name)
                with open(image_path, 'rb') as image_file:
                    files[image_block_name] = (image_block_name,
                                               image_file.read(),
                                               f'image/{image_suffix}')
                break
    images = root.xpath("//*[local-name() = 'img']")

    for image in images:
        image_src = image.get('src')
        image_name = image_src
        if image_src.startswith("../"):
            image_name = image_src[3:]
        image_suffix = image_name.split('.')[-1]
        image_block_name = image_name.replace("/", "_")
        image.set('src', f'name:{image_block_name}')
        image_path = os.path.join(temp_dir, image_name)
        with open(image_path, 'rb') as image_file:
            files[image_block_name] = (image_block_name,
                                       image_file.read(),
                                       f'image/{image_suffix}')
    return lxml.etree.tostring(root, encoding='utf-8'), files


if __name__ == '__main__':
    pass
