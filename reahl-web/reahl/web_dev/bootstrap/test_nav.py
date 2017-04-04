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

from reahl.tofu import scenario, expected, Fixture, uses
from reahl.tofu.pytest_support import with_fixtures

from reahl.webdev.tools import WidgetTester, Browser, XPath

from reahl.component.exceptions import ProgrammerError
from reahl.component.i18n import Translator
from reahl.web.fw import Bookmark, Url
from reahl.web.bootstrap.ui import A, Div, P
from reahl.web.bootstrap.navs import Menu, Nav, PillLayout, TabLayout, DropdownMenu, DropdownMenuLayout

from reahl.web_dev.fixtures import WebFixture2

_ = Translator('reahl-web')


@with_fixtures(WebFixture2)
def test_navs(web_fixture):
    """A Nav is a menu with css classes for styling by Bootstrap."""
    with web_fixture.context:

        bookmarks = [Bookmark('', '/one', 'One'),
                     Bookmark('', '/two', 'Two')]
        menu = Nav(web_fixture.view).with_bookmarks(bookmarks)

        # A nav is an ul.nav
        assert menu.html_representation.tag_name == 'ul'
        assert 'nav' in menu.html_representation.get_attribute('class')

        # Containing a li for each menu item
        [one, two] = menu.html_representation.children

        for item, expected_href, expected_description in [(one, '/one', 'One'),
                                                          (two, '/two', 'Two')]:
            assert item.tag_name == 'li'
            assert item.get_attribute('class') == 'nav-item'

            [a] = item.children
            assert a.get_attribute('href') == expected_href
            assert a.children[0].value ==  expected_description
            assert a.get_attribute('class') == 'nav-link'


@with_fixtures(WebFixture2)
def test_populating(web_fixture):
    """Navs can be populated with a list of A's or Bookmarks."""
    with web_fixture.context:

        # Case: a normal menu from bookmarks
        item_specs = [Bookmark('/', '/href1', 'description1'),
                      Bookmark('/', '/go_to_href', 'description2')]
        menu = Nav(web_fixture.view).with_bookmarks(item_specs)
        tester = WidgetTester(menu)

        [item1, item2] = menu.menu_items
        assert item1.a.href.path == '/href1'
        assert item1.a.children[0].value == 'description1'

        assert item2.a.href.path == '/go_to_href'
        assert item2.a.children[0].value == 'description2'

        #case: using A's
        a_list = [A.from_bookmark(web_fixture.view, i) for i in item_specs]
        menu = Nav(web_fixture.view).with_a_list(a_list)
        [item1, item2] = menu.menu_items
        assert item1.a is a_list[0]
        assert item2.a is a_list[1]


@uses(web_fixture=WebFixture2)
class VisualFeedbackScenarios(Fixture):

    @property
    def context(self):
        return self.web_fixture.context

    @scenario
    def disabled(self):
        """The mouse cursor is shown as no-access on disabled items."""
        def not_allowed():
            return False
        self.menu_item_with_state = A(self.web_fixture.view, Url('/another_url'), write_check=not_allowed)
        self.state_indicator_class = 'disabled'

    @scenario
    def active(self):
        """The currently active item is highlighted."""
        current_url = Url(self.web_fixture.request.url)
        self.menu_item_with_state = A(self.web_fixture.view, current_url)
        self.state_indicator_class = 'active'


@with_fixtures(WebFixture2, VisualFeedbackScenarios)
def test_visual_feedback_on_items(web_fixture, visual_feedback_scenarios):
    """The state of a MenuItem is visually indicated to a user."""
    with web_fixture.context:

        menu = Nav(web_fixture.view)
        menu.add_a(A(web_fixture.view, Url('/an_url')))
        menu.add_a(visual_feedback_scenarios.menu_item_with_state)

        [defaulted_item, item_with_state] = menu.html_representation.children

        [defaulted_a] = defaulted_item.children
        [a_with_state] = item_with_state.children

        assert visual_feedback_scenarios.state_indicator_class not in defaulted_a.get_attribute('class')
        assert visual_feedback_scenarios.state_indicator_class in a_with_state.get_attribute('class')


@uses(web_fixture=WebFixture2)
class MenuItemScenarios(Fixture):
    description = 'The link'
    href = Url('/link')

    @property
    def context(self):
        return self.web_fixture.context

    @scenario
    def not_active(self):
        self.active_regex = None
        self.web_fixture.request.environ['PATH_INFO'] = '/something/else'
        self.active = False

    @scenario
    def active_exact_path(self):
        self.active_regex = None
        self.web_fixture.request.environ['PATH_INFO'] = '/link'
        self.active = True

    @scenario
    def active_partial_path(self):
        self.active_regex = None
        self.web_fixture.request.environ['PATH_INFO'] = '/link/something/more'
        self.active = True

    @scenario
    def inactive_partial_path(self):
        self.active_regex = '^/link$'
        self.web_fixture.request.environ['PATH_INFO'] = '/link/something/more'
        self.active = False


@with_fixtures(WebFixture2, MenuItemScenarios)
def test_rendering_active_menu_items(web_fixture, menu_item_scenarios):
    """A MenuItem is marked as active based on its active_regex or the A it represents."""
    description = 'The link'
    href = Url('/link')

    with web_fixture.context:

        menu = Nav(web_fixture.view)
        menu_item_a = A(web_fixture.view, href, description=description)
        menu.add_a(menu_item_a, active_regex=menu_item_scenarios.active_regex)
        tester = WidgetTester(menu)

        actual = tester.get_html_for('//li')
        active_str = '' if not menu_item_scenarios.active else 'active '
        expected_menu_item_html = '<li class="nav-item"><a href="/link" class="%snav-link">The link</a></li>'  % (active_str)
        assert actual == expected_menu_item_html


@uses(web_fixture=WebFixture2)
class CustomMenuItemFixture(Fixture):

    @property
    def context(self):
        return self.web_fixture.context

    def new_href(self):
        return Url('/link')

    def new_menu_item_a(self):
        description = 'The link'
        href = Url('/link')

        menu_item_a = A(self.web_fixture.view, self.href, description=description)
        return menu_item_a

    def new_menu(self):
        menu = Nav(self.web_fixture.view)
        menu.add_a(self.menu_item_a)
        return menu

    @property
    def menu_item(self):
        return self.menu.menu_items[0]

    def new_tester(self):
        return WidgetTester(self.menu)

    def item_displays_as_active(self):
        actual = self.tester.get_html_for('//li')
        active_str = 'active '
        expected_menu_item_html = '<li class="nav-item"><a href="/link" class="%snav-link">The link</a></li>'  % (active_str)
        return actual == expected_menu_item_html

    def set_request_url(self, href):
        self.web_fixture.request.environ['PATH_INFO'] = str(href)

    @scenario
    def default(self):
        # The default behaviour happens when no custom method is supplied
        self.go_to_href = self.href
        self.expects_active = True
        self.overriding_callable = None

    @scenario
    def overridden(self):
        # Overriding behaviour happens when supplied
        self.go_to_href = self.href
        self.expects_active = False
        self.overriding_callable = lambda: False

    @scenario
    def overridden_on_unrelated_url(self):
        # On an unrelated url, active is forced
        url_on_which_item_is_usually_inactive = Url('/another_href')
        self.go_to_href = url_on_which_item_is_usually_inactive

        self.expects_active = True
        self.overriding_callable = lambda: True


@with_fixtures(WebFixture2, CustomMenuItemFixture)
def test_custom_active_menu_items(web_fixture, custom_menu_item_fixture):
    """You can specify a custom method by which a MenuItem determines its active state."""
    fixture = custom_menu_item_fixture

    with web_fixture.context:
        fixture.set_request_url(fixture.go_to_href)

        if fixture.overriding_callable:
            fixture.menu_item.determine_is_active_using(fixture.overriding_callable)
        assert fixture.expects_active == fixture.item_displays_as_active()


@with_fixtures(WebFixture2)
def test_language_menu(web_fixture):
    """A Nav can also be constructed to let a user choose to view the same page in
       another of the supported languages."""

    class PanelWithMenu(Div):
        def __init__(self, view):
            super(PanelWithMenu, self).__init__(view)
            self.add_child(Menu(view).with_languages())
            self.add_child(P(view, text=_('This is an English sentence.')))

    with web_fixture.context:

        wsgi_app = web_fixture.new_wsgi_app(child_factory=PanelWithMenu.factory())

        browser = Browser(wsgi_app)
        browser.open('/')

        assert browser.is_element_present(XPath.paragraph_containing('This is an English sentence.'))

        browser.click(XPath.link_with_text('Afrikaans'))
        assert browser.is_element_present(XPath.paragraph_containing('Hierdie is \'n sin in Afrikaans.'))

        browser.click(XPath.link_with_text('English (United Kingdom)'))
        assert browser.is_element_present(XPath.paragraph_containing('This is an English sentence.'))


class LayoutScenarios(Fixture):
    @scenario
    def pill_layouts(self):
        """PillLayouts are used to make Navs MenuItems look almost like buttons."""
        self.layout_css_class = {'nav-pills'}
        self.layout = PillLayout()

    @scenario
    def stacked_pill_layouts(self):
        """Using a PillLayout, you can also make MenuItems appear stacked on top of
           one another instead of being placed next to one another."""
        self.layout_css_class = {'nav-pills', 'nav-stacked'}
        self.layout = PillLayout(stacked=True)

    @scenario
    def tab_layouts(self):
        """TabLayouts are used to make Navs MenuItems look like a series of tabs."""
        self.layout_css_class = {'nav-tabs'}
        self.layout = TabLayout()


@with_fixtures(WebFixture2, LayoutScenarios)
def test_nav_layouts(web_fixture, layout_scenarios):
    """Navs can be laid out in different ways."""
    with web_fixture.context:

        menu = Nav(web_fixture.view)

        assert not layout_scenarios.layout_css_class.issubset(menu.html_representation.attributes['class'].value)
        menu.use_layout(layout_scenarios.layout)
        assert layout_scenarios.layout_css_class.issubset(menu.html_representation.attributes['class'].value)


class DifferentLayoutTypes(Fixture):
    @scenario
    def pills(self):
        self.layout_type = PillLayout

    @scenario
    def tabs(self):
        self.layout_type = TabLayout


@with_fixtures(WebFixture2, DifferentLayoutTypes)
def test_justified_items(web_fixture, different_layout_types):
    """Both a PillLayout or TabLayout can be set to make the MenuItems of
       their Nav fill the width of the parent, with the text of each item centered."""

    with web_fixture.context:

        menu = Nav(web_fixture.view).use_layout(different_layout_types.layout_type())
        assert 'nav-justified' not in menu.html_representation.get_attribute('class')

        menu = Nav(web_fixture.view).use_layout(different_layout_types.layout_type(justified=True))
        assert 'nav-justified' in menu.html_representation.get_attribute('class')


def test_pill_layouts_cannot_mix_justified_and_stacked():
    """A PillLayout cannot be both stacked and justified at the same time."""

    with expected(ProgrammerError):
        PillLayout(stacked=True, justified=True)


@with_fixtures(WebFixture2)
def test_dropdown_menus(web_fixture):
    """You can add a DropdownMenu as a dropdown inside a Nav."""
    with web_fixture.context:

        menu = Nav(web_fixture.view)
        sub_menu = DropdownMenu(web_fixture.view)
        sub_menu.add_a(A(web_fixture.view, Url('/an/url'), description='sub menu item'))
        menu.add_dropdown('Dropdown title', sub_menu)

        [item] = menu.html_representation.children

        assert item.tag_name == 'li'
        assert 'dropdown' in item.get_attribute('class')

        [toggle, added_sub_menu] = item.children
        assert 'dropdown-toggle' in toggle.get_attribute('class')
        assert 'dropdown' in toggle.get_attribute('data-toggle')
        assert '-' in toggle.get_attribute('data-target')
        assert 'caret' in toggle.children[1].get_attribute('class')

        title_text = toggle.children[0].value
        assert title_text == 'Dropdown title'

        assert added_sub_menu is sub_menu
        assert 'dropdown-menu' in added_sub_menu.html_representation.get_attribute('class').split()
        assert isinstance(added_sub_menu.html_representation, Div)

        [dropdown_item] = added_sub_menu.html_representation.children
        assert isinstance(dropdown_item, A)
        assert 'dropdown-item' in dropdown_item.get_attribute('class').split()


@with_fixtures(WebFixture2)
def test_dropdown_menus_can_drop_up(web_fixture):
    """Dropdown menus can drop upwards instead of downwards."""
    with web_fixture.context:

        menu = Nav(web_fixture.view)
        sub_menu = Nav(web_fixture.view)
        menu.add_dropdown('Dropdown title', sub_menu, drop_up=True)

        [item] = menu.html_representation.children

        assert item.tag_name == 'li'
        assert 'dropup' in item.get_attribute('class')


@with_fixtures(WebFixture2)
def test_dropdown_menus_right_align(web_fixture):
    """Dropdown menus can be aligned to the bottom right of their toggle, instead of the default (left)."""

    with web_fixture.context:

        defaulted_sub_menu = DropdownMenu(web_fixture.view).use_layout(DropdownMenuLayout())
        assert 'dropdown-menu-right' not in defaulted_sub_menu.html_representation.get_attribute('class')

        right_aligned_sub_menu = DropdownMenu(web_fixture.view).use_layout(DropdownMenuLayout(align_right=True))
        assert 'dropdown-menu-right' in right_aligned_sub_menu.html_representation.get_attribute('class')
