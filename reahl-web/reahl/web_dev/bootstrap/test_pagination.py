# Copyright 2015, 2016 Reahl Software Services (Pty) Ltd. All rights reserved.
#-*- encoding: utf-8 -*-
#
#    This file is part of Reahl.
#
#    Reahl is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation; version 3 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import print_function, unicode_literals, absolute_import, division
import six
from reahl.stubble import stubclass
from reahl.tofu import Fixture, scenario, uses
from reahl.tofu.pytest_support import with_fixtures

from reahl.webdev.tools import XPath
from reahl.web.bootstrap.ui import P, Div
from reahl.web.bootstrap.pagination import PageMenu, PagedPanel, PageIndex, SequentialPageIndex, AnnualItemOrganiserProtocol, AnnualPageIndex

from reahl.web_dev.fixtures import WebFixture2

@uses(web_fixture=WebFixture2)
class PageMenuFixture(Fixture):

    @property
    def context(self):
        return self.web_fixture.context

    def new_number_of_pages(self):
        return 10

    def new_max_page_links(self):
        return 5

    def new_PageIndexStub(self):
        fixture = self
        @stubclass(PageIndex)
        class PageIndexStub(PageIndex):
            def __init__(self, max_page_links, number_of_pages):
                super(PageIndexStub, self).__init__(max_page_links=max_page_links)
                self.number_of_pages = number_of_pages

            @property
            def total_number_of_pages(self):
                return self.number_of_pages

            def get_contents_for_page(self, page_number):
                return 'contents of page %s' % page_number

            def get_description_for_page(self, page_number):
                return 'p%s' % page_number

        return PageIndexStub

    def new_PageContainer(self):
        class PageContainer(PagedPanel):
            def __init__(self, parent, page_index):
                super(PageContainer, self).__init__(parent, page_index, 'container')
                self.add_child(P(self.view, text=self.current_contents))

        return PageContainer

    def new_MainWidget(self):
        fixture = self
        class MainWidget(Div):
            def __init__(self, view):
                super(MainWidget, self).__init__(view)
                page_index = fixture.PageIndexStub(fixture.max_page_links, fixture.number_of_pages)
                page_container = self.add_child(fixture.PageContainer(self.view, page_index))
                self.add_child(PageMenu(self.view, 'page_menu_widget', page_index, page_container))
        return MainWidget

    def container_contents_is(self, expected):
        return self.web_fixture.driver_browser.execute_script('return window.jQuery("div p").html() == "%s"' % expected)

    def page_range_links_match(self, link_labels):
        return self.web_fixture.driver_browser.execute_script('return window.jQuery(".pagination a").slice(2,-2).map(function(){return window.jQuery(this).html();}).toArray() == "%s"' % link_labels)

    def is_marked_active(self, link_label, nth=1):
        [li] = self.web_fixture.driver_browser.xpath('%s/..' % (XPath.link_with_text(link_label, nth=nth)))
        return 'active' in li.attrib.get('class', '')

    def new_wsgi_app(self):
        return self.web_fixture.new_wsgi_app(enable_js=True, child_factory=self.MainWidget.factory())


# Please see fixture for how to declare a PageIndex, PageContainer and PageMenu
@with_fixtures(WebFixture2, PageMenuFixture)
def test_selecting_a_page(web_fixture, page_menu_fixture):
    """Clicking the link of a page results in the contents of the PageContainer being refreshed."""
    with web_fixture.context:

        web_fixture.reahl_server.set_app(page_menu_fixture.wsgi_app)
        browser = web_fixture.driver_browser
        browser.open('/')

        browser.wait_for(page_menu_fixture.container_contents_is, 'contents of page 1')
        browser.click(XPath.link_with_text('p2'))
        browser.wait_for(page_menu_fixture.container_contents_is, 'contents of page 2')


@with_fixtures(WebFixture2, PageMenuFixture)
def test_navigating_the_page_numbers(web_fixture, page_menu_fixture):
    """One can navigate the range of page links displayed by the PageMenu using the special links."""

    fixture = page_menu_fixture
    with web_fixture.context:

        fixture.number_of_pages = 30
        fixture.max_page_links = 5
        web_fixture.reahl_server.set_app(page_menu_fixture.wsgi_app)
        browser = web_fixture.driver_browser
        browser.open('/')

        # Case: next link
        browser.click(XPath.link_starting_with_text('»'))
        assert browser.wait_for(fixture.page_range_links_match, 'p6,p7,p8,p9,p10')
        browser.click(XPath.link_starting_with_text('»'))
        assert browser.wait_for(fixture.page_range_links_match, 'p11,p12,p13,p14,p15')

        # Case: prev link
        browser.click(XPath.link_starting_with_text('«'))
        assert browser.wait_for(fixture.page_range_links_match, 'p6,p7,p8,p9,p10')

        # Case: last link
        browser.click(XPath.link_starting_with_text('→'))
        assert browser.wait_for(fixture.page_range_links_match, 'p26,p27,p28,p29,p30')

        # Case: first link
        browser.click(XPath.link_starting_with_text('←'))
        assert browser.wait_for(fixture.page_range_links_match, 'p1,p2,p3,p4,p5')


@with_fixtures(WebFixture2, PageMenuFixture)
def test_contents_when_navigating_the_page_numbers(web_fixture, page_menu_fixture):
    """When navigating the range of page links, the currently displayed contents stay unchanged."""
    with web_fixture.context:

        page_menu_fixture.number_of_pages = 30
        page_menu_fixture.max_page_links = 5
        web_fixture.reahl_server.set_app(page_menu_fixture.wsgi_app)
        browser = web_fixture.driver_browser
        browser.open('/')

        browser.click(XPath.link_with_text('p2'))
        browser.wait_for(page_menu_fixture.container_contents_is, 'contents of page 2')
        browser.click(XPath.link_starting_with_text('»'))
        browser.wait_for(page_menu_fixture.container_contents_is, 'contents of page 2')


@with_fixtures(WebFixture2, PageMenuFixture)
def test_active_state_of_page_links(web_fixture, page_menu_fixture):
    """When choosing a page, the new page link is marked as active, without a server round-trip."""
    fixture = page_menu_fixture

    with web_fixture.context:
        fixture.number_of_pages = 30
        fixture.max_page_links = 5
        web_fixture.reahl_server.set_app(fixture.wsgi_app)
        web_fixture.driver_browser.open('/')

        with web_fixture.driver_browser.no_load_expected_for('.pagination>*'):
            assert not fixture.is_marked_active('p2')
            web_fixture.driver_browser.click(XPath.link_with_text('p2'))
            web_fixture.driver_browser.wait_for(fixture.is_marked_active, 'p2')


@with_fixtures(WebFixture2, PageMenuFixture)
def test_active_state_on_multiple_menus(web_fixture, page_menu_fixture):
    """If there's more than one PageMenu on the page, the active page is switched for both of them"""
    fixture = page_menu_fixture

    with web_fixture.context:

        class MainWidget(Div):
            def __init__(self, view):
                super(MainWidget, self).__init__(view)
                page_index = fixture.PageIndexStub(fixture.max_page_links, fixture.number_of_pages)
                page_container = self.add_child(fixture.PageContainer(self.view, page_index))
                self.add_child(PageMenu(self.view, 'page_menu_widget', page_index, page_container))
                self.add_child(PageMenu(self.view, 'page_menu_widget2', page_index, page_container))
        fixture.MainWidget = MainWidget

        web_fixture.reahl_server.set_app(fixture.wsgi_app)
        browser = web_fixture.driver_browser
        browser.open('/')

        assert not fixture.is_marked_active('p2', nth=1)
        assert not fixture.is_marked_active('p2', nth=2)
        browser.click(XPath.link_with_text('p2'))
        browser.wait_for(fixture.is_marked_active, 'p2', 1)
        browser.wait_for(fixture.is_marked_active, 'p2', 2)


@with_fixtures(WebFixture2, PageMenuFixture)
def test_active_state_of_next_prev_links(web_fixture, page_menu_fixture):
    """Next and Last links are only active when not on the last range of pages,
       and Prev and First are similarly deactive when on the first range of pages."""
    fixture = page_menu_fixture

    with web_fixture.context:
        fixture.number_of_pages = 15
        fixture.max_page_links = 5
        web_fixture.reahl_server.set_app(fixture.wsgi_app)
        browser = web_fixture.driver_browser
        browser.open('/')
    
        # Case: when you are on the left of the page range
        assert not browser.is_active(XPath.link_starting_with_text('←'))
        assert not browser.is_active(XPath.link_starting_with_text('«'))
        assert browser.is_active(XPath.link_starting_with_text('»'))
        assert browser.is_active(XPath.link_starting_with_text('→'))
    
        # Case: when you are in the middle of the page range
        browser.click(XPath.link_starting_with_text('»'))
        browser.wait_for_element_present(XPath.link_with_text('p6'))
        assert browser.is_active(XPath.link_starting_with_text('←'))
        assert browser.is_active(XPath.link_starting_with_text('«'))
        assert browser.is_active(XPath.link_starting_with_text('»'))
        assert browser.is_active(XPath.link_starting_with_text('→'))
    
        # Case: when you are at the end of the page range
        browser.click(XPath.link_starting_with_text('»'))
        browser.wait_for_element_present(XPath.link_with_text('p11'))
        assert browser.is_active(XPath.link_starting_with_text('←'))
        assert browser.is_active(XPath.link_starting_with_text('«'))
        assert not browser.is_active(XPath.link_starting_with_text('»'))
        assert not browser.is_active(XPath.link_starting_with_text('→'))


class LinkScenarios(PageMenuFixture):
    @scenario
    def only_one_page(self):
        self.number_of_pages = 1
        self.max_page_links = 5
        self.goto_last_range = False
        self.visible_page_descriptions = 'p1'
        self.visible_last_page_descriptions = self.visible_page_descriptions

    @scenario
    def fewer_pages_than_max_links(self):
        self.number_of_pages = 2
        self.max_page_links = 5
        self.goto_last_range = False
        self.visible_page_descriptions = 'p1,p2'
        self.visible_last_page_descriptions = self.visible_page_descriptions

    @scenario
    def more_pages_than_max_links(self):
        self.number_of_pages = 10
        self.max_page_links = 5
        self.goto_last_range = True
        self.visible_page_descriptions = 'p1,p2,p3,p4,p5'
        self.visible_last_page_descriptions = 'p6,p7,p8,p9,p10'

    @scenario
    def more_than_one_range_last_range_not_complete(self):
        self.number_of_pages = 7
        self.max_page_links = 5
        self.goto_last_range = True
        self.visible_page_descriptions = 'p1,p2,p3,p4,p5'
        self.visible_last_page_descriptions = 'p3,p4,p5,p6,p7'

    @scenario
    def changing_number_of_links(self):
        self.number_of_pages = 10
        self.max_page_links = 3
        self.goto_last_range = False
        self.visible_page_descriptions = 'p1,p2,p3'
        self.visible_last_page_descriptions = self.visible_page_descriptions


@with_fixtures(WebFixture2, LinkScenarios)
def test_which_links_display(web_fixture, link_scenarios):
    """The menu displays the correct range of page links, depending on the starting page in the range, the
       total number of pages and the max number of links in a range"""
    fixture = link_scenarios
    with web_fixture.context:
        web_fixture.reahl_server.set_app(fixture.wsgi_app)

        browser = web_fixture.driver_browser
        browser.open('/')
        assert browser.wait_for(fixture.page_range_links_match, fixture.visible_page_descriptions)

        if fixture.goto_last_range:
            browser.click(XPath.link_starting_with_text('→'))

        assert browser.wait_for(fixture.page_range_links_match, fixture.visible_last_page_descriptions)


def test_annual_page_index():
    """The AnnualPageIndex breaks a query of items up into pages containing items with the same year."""

    @stubclass(AnnualItemOrganiserProtocol)
    class ItemOrganiser(AnnualItemOrganiserProtocol):
        def get_years(self):                return [2000, 2001]
        def get_items_for_year(self, year): return [year]*3

    page_index = AnnualPageIndex(ItemOrganiser())

    assert page_index.get_contents_for_page(2) == [2001, 2001, 2001]
    assert page_index.get_description_for_page(1) == '2000'
    assert page_index.years == [2000, 2001]
    assert page_index.total_number_of_pages == 2


class SequentialScenarios(Fixture):
    def new_items(self):
        return list(range(0, self.number_of_items))

    def new_page_index(self):
        return SequentialPageIndex(self.items, items_per_page=self.items_per_page, max_page_links=12)

    @scenario
    def less_than_a_page_items(self):
        self.number_of_items = 2
        self.items_per_page = 10
        self.expected_pages = 1
        self.last_page_contents = self.items[0:2]

    @scenario
    def exactly_one_page_items(self):
        self.number_of_items = 10
        self.items_per_page = 10
        self.expected_pages = 1
        self.last_page_contents = self.items[0:10]

    @scenario
    def just_more_than_one_page_items(self):
        self.number_of_items = 15
        self.items_per_page = 10
        self.expected_pages = 2
        self.last_page_contents = self.items[10:15]


@with_fixtures(WebFixture2, SequentialScenarios)
def test_sequential_page_index(sequential_scenarios):
    """The SequentialPageIndex breaks a query of items up into pages of sequential items"""

    fixture = sequential_scenarios

    assert fixture.page_index.total_number_of_pages == fixture.expected_pages
    page = fixture.page_index.get_page_number(fixture.expected_pages)
    assert page.description == six.text_type(fixture.expected_pages)
    assert page.contents == fixture.last_page_contents
    assert fixture.page_index.max_page_links == 12
