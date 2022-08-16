import os
import unittest
from app import _get_opf_file

from epub import (_get_css_files, _image_inline, _img_inline,
                  _load_css_content,
                  _load_mimetype,
                  _load_opf_file, _load_page_content, _remove_css_link,
                  container_file, css_inline)


temp_dir = "/tmp/epub"


class EPubTest(unittest.TestCase):

    def test_mimetype(self):
        print(_load_mimetype(temp_dir))

    def test_opf(self):
        container_file_path = os.path.join(temp_dir, container_file)
        opf_file = _get_opf_file(container_file_path)
        opf_file_path = os.path.join(temp_dir, opf_file)
        a, b = _load_opf_file(opf_file_path)
        print(a)
        print(b)

    def test_page_content(self):
        page_file = "titlepage.xhtml"
        # page_file = "text/part0003.html"
        container_file_path = os.path.join(temp_dir, container_file)
        opf_file = _get_opf_file(container_file_path)
        opf_file_path = os.path.join(temp_dir, opf_file)
        a, b = _load_opf_file(opf_file_path)
        css_files = _get_css_files(a.values())
        css = _load_css_content(temp_dir, css_files)
        c = _load_page_content(temp_dir, page_file)
        c = _remove_css_link(c)
        c = css_inline(c, css)
        # c = _image_inline(temp_dir, c)
        c = _img_inline(temp_dir, c)
        print(c)
