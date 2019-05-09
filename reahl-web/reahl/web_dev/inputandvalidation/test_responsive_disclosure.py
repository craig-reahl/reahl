# Copyright 2018 Reahl Software Services (Pty) Ltd. All rights reserved.
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

import threading

from sqlalchemy import Column, Integer, Boolean

from reahl.tofu import Fixture, expected, scenario, uses
from reahl.tofu.pytestsupport import with_fixtures

from reahl.web_dev.fixtures import WebFixture, BasicPageLayout
from reahl.webdev.tools import XPath, Browser
from reahl.web.fw import Widget, UserInterface
from reahl.web.ui import Form, Div, SelectInput, Label, P, RadioButtonSelectInput, CheckboxSelectInput, \
    CheckboxInput, ButtonInput, TextInput, HTML5Page
from reahl.component.modelinterface import Field, BooleanField, MultiChoiceField, ChoiceField, Choice, exposed, \
    IntegerField, EmailField, Event, Action
from reahl.component.exceptions import ProgrammerError, DomainException
from reahl.web.dynamic import DynamicSection
from reahl.web_dev.inputandvalidation.test_widgetqueryargs import QueryStringFixture
from reahl.sqlalchemysupport import Base, Session
from reahl.sqlalchemysupport_dev.fixtures import SqlAlchemyFixture


@uses(web_fixture=WebFixture)
class ResponsiveDisclosureFixture(Fixture):

    def new_ModelObject(self):
        class ModelObject(object):
            def __init__(self):
                self.choice = 1

            @exposed
            def fields(self, fields):
                fields.choice = ChoiceField([Choice(1, IntegerField(label='One')),
                                             Choice(2, IntegerField(label='Two')),
                                             Choice(3, IntegerField(label='Three'))],
                                            label='Choice')
        return ModelObject

    def new_MyChangingWidget(self):
        class MyChangingWidget(Div):
            def __init__(self, view, model_object):
                super(MyChangingWidget, self).__init__(view, css_id='dave')
                self.model_object = model_object
                self.add_child(P(self.view, text='My state is now %s' % self.model_object.choice))

        return MyChangingWidget

    def new_MainWidget(self):
        fixture = self
        class MainWidget(Widget):
            def __init__(self, view):
                super(MainWidget, self).__init__(view)
                an_object = fixture.ModelObject()
                self.add_child(fixture.MyForm(view, an_object))

        return MainWidget

    def new_MyForm(self):
        fixture = self
        class MyForm(Form):
            def __init__(self, view, an_object):
                super(MyForm, self).__init__(view, 'myform')
                self.enable_refresh()
                self.change_trigger_input = fixture.create_trigger_input(self, an_object)
                self.add_child(Label(view, for_input=self.change_trigger_input))
                self.add_child(self.change_trigger_input)
                self.add_child(fixture.MyChangingWidget(view, an_object))

        return MyForm

    def create_trigger_input(self, form, an_object):
        return SelectInput(form, an_object.fields.choice, refresh_widget=form)



class ResponsiveWidgetScenarios(ResponsiveDisclosureFixture):
    @scenario
    def select_input(self):
        fixture = self

        def change_value(browser):
            browser.select(XPath.select_labelled('Choice'), 'Three')
        self.change_value = change_value
        self.initial_state = 1
        self.changed_state = 3

    @scenario
    def radio_buttons(self):
        fixture = self

        def create_trigger_input(form, an_object):
            return RadioButtonSelectInput(form, an_object.fields.choice, refresh_widget=form)
        self.create_trigger_input = create_trigger_input

        def change_value(browser):
            browser.click(XPath.input_labelled('Three'))
        self.change_value = change_value
        self.initial_state = 1
        self.changed_state = 3

    @scenario
    def single_valued_checkbox(self):
        fixture = self

        class ModelObject(object):
            def __init__(self):
                self.choice = False
            @exposed
            def fields(self, fields):
                fields.choice = BooleanField(label='Choice',
                                             true_value='✓', false_value='⍻')
        self.ModelObject = ModelObject

        def create_trigger_input(form, an_object):
            the_input = CheckboxInput(form, an_object.fields.choice, refresh_widget=form)
            the_input.set_id('marvin')
            return the_input
        self.create_trigger_input = create_trigger_input

        def change_value(browser):
            browser.click(XPath.input_labelled('Choice'))
        self.change_value = change_value
        self.initial_state = False
        self.changed_state = True

    @scenario
    def multi_valued_checkbox_select(self):
        fixture = self

        class ModelObject(object):
            def __init__(self):
                self.choice = [1]

            @exposed
            def fields(self, fields):
                fields.choice = MultiChoiceField([Choice(1, IntegerField(label='One')),
                                                  Choice(2, IntegerField(label='Two')),
                                                  Choice(3, IntegerField(label='Three'))],
                                                 label='Choice')
        self.ModelObject = ModelObject

        def create_trigger_input(form, an_object):
            the_input = CheckboxSelectInput(form, an_object.fields.choice, refresh_widget=form)
            the_input.set_id('marvin')
            return the_input
        self.create_trigger_input = create_trigger_input

        def change_value(browser):
            browser.click(XPath.input_labelled('Three'))
        self.change_value = change_value
        self.initial_state = [1]
        self.changed_state = [1, 3]

    @scenario
    def multi_valued_checkbox_select_with_single_choice_corner_case_empty_a_list(self):
        self.multi_valued_checkbox_select()
        fixture = self

        class ModelObject(object):
            def __init__(self):
                self.choice = [1]
                
            @exposed
            def fields(self, fields):
                fields.choice = MultiChoiceField([Choice(1, IntegerField(label='One'))],
                                                 label='Choice')
        self.ModelObject = ModelObject

        def change_value(browser):
            browser.click(XPath.input_labelled('One'))
        self.change_value = change_value
        self.initial_state = [1]
        self.changed_state = []

    @scenario
    def multi_valued_checkbox_select_with_single_choice_corner_case_add_to_empty_list(self):
        self.multi_valued_checkbox_select()
        fixture = self

        class ModelObject(object):
            def __init__(self):
                self.choice = []

            @exposed
            def fields(self, fields):
                fields.choice = MultiChoiceField([Choice(1, IntegerField(label='One'))],
                                                 label='Choice')
        self.ModelObject = ModelObject
        #self.MyForm from multi_valued_checkbox_select

        def change_value(browser):
            browser.click(XPath.input_labelled('One'))
        self.change_value = change_value
        self.initial_state = []
        self.changed_state = [1]

    @scenario
    def multi_valued_select(self):
        fixture = self

        class ModelObject(object):
            def __init__(self):
                self.choice = [1]

            @exposed
            def fields(self, fields):
                fields.choice = MultiChoiceField([Choice(1, IntegerField(label='One')),
                                                  Choice(2, IntegerField(label='Two')),
                                                  Choice(3, IntegerField(label='Three'))],
                                                 label='Choice')
        self.ModelObject = ModelObject

        def create_trigger_input(form, an_object):
            the_input = SelectInput(form, an_object.fields.choice, refresh_widget=form)
            the_input.set_id('marvin')
            return the_input
        self.create_trigger_input = create_trigger_input

        def change_value(browser):
            browser.select(XPath.select_labelled('Choice'), 'Three')
        self.change_value = change_value
        self.initial_state = [1]
        self.changed_state = [1, 3]


@with_fixtures(WebFixture, QueryStringFixture, ResponsiveWidgetScenarios)
def test_inputs_can_refresh_parent_widgets(web_fixture, query_string_fixture, responsive_widget_scenarios):
    """An Input can cause another Widget to be re-rendered if the input value changes."""

    fixture = responsive_widget_scenarios

    wsgi_app = web_fixture.new_wsgi_app(enable_js=True, child_factory=fixture.MainWidget.factory())
    web_fixture.reahl_server.set_app(wsgi_app)
    browser = web_fixture.driver_browser
    browser.open('/')

#    web_fixture.pdb()
    assert browser.wait_for(query_string_fixture.is_state_now, fixture.initial_state)
    fixture.change_value(browser)
    assert browser.wait_for(query_string_fixture.is_state_now, fixture.changed_state)


@with_fixtures(WebFixture, QueryStringFixture, ResponsiveDisclosureFixture)
def test_overridden_names(web_fixture, query_string_fixture, responsive_disclosure_fixture):
    """The overridden names of inputs correctly ensures that that input's state is distinguished from another with the same name."""
    fixture = responsive_disclosure_fixture

    class ModelObject(object):
        def __init__(self):
            self.choice = [1]

        @exposed
        def fields(self, fields):
            fields.choice = MultiChoiceField([Choice(1, IntegerField(label='One')),
                                                Choice(2, IntegerField(label='Two')),
                                                Choice(3, IntegerField(label='Three'))],
                                                label='Choice')
    fixture.ModelObject = ModelObject

    def create_trigger_input(form, an_object):
        the_input = CheckboxSelectInput(form, an_object.fields.choice, name='first_choice', refresh_widget=form)
        the_input.set_id('marvin')
        return the_input
    fixture.create_trigger_input = create_trigger_input

    class MyForm(fixture.MyForm):
        def __init__(self, view, an_object):
            super(MyForm, self).__init__(view, an_object)
            another_model_object = fixture.ModelObject()
            another_input = CheckboxSelectInput(self, another_model_object.fields.choice)
            self.add_child(Label(view, for_input=another_input))
            self.add_child(another_input)
            
    fixture.MyForm = MyForm
    
    wsgi_app = web_fixture.new_wsgi_app(enable_js=True, child_factory=fixture.MainWidget.factory())
    web_fixture.reahl_server.set_app(wsgi_app)
    browser = web_fixture.driver_browser
    browser.open('/')

    browser.click('//input[@name="first_choice[]" and @value="3"]')
    assert browser.wait_for(query_string_fixture.is_state_now, [1,3])


class BlockingRefreshFixture(ResponsiveDisclosureFixture):
    should_pause_to_simulate_long_refresh = False

    def new_block_event(self):
        return threading.Event()

    def simulate_long_refresh_start(self):
        self.block_event.wait()

    def simulate_long_refresh_done(self):
        self.block_event.set()

    def new_MyChangingWidget(self):
        fixture = self
        class ChangingWidgetThatPauses(super(BlockingRefreshFixture, self).new_MyChangingWidget()):
            def __init__(self, view, model_object):
                super(ChangingWidgetThatPauses, self).__init__(view, model_object)
                if fixture.should_pause_to_simulate_long_refresh:
                    fixture.simulate_long_refresh_start()

        return ChangingWidgetThatPauses

    def is_form_blocked(self, browser):
        form_xpath = XPath('//form[@id="myform"]')
        form_blocked_xpath = XPath('%s/div[@class="blockUI"]' % form_xpath)
        return browser.is_element_present(form_blocked_xpath)


@with_fixtures(WebFixture, BlockingRefreshFixture, QueryStringFixture)
def test_the_form_is_blocked_while_the_widget_is_being_refreshed(web_fixture, blocking_refresh_fixture, query_string_fixture):
    """The form is blocked until the responsive widget has refreshed it contents."""

    fixture = blocking_refresh_fixture

    wsgi_app = web_fixture.new_wsgi_app(enable_js=True, child_factory=fixture.MainWidget.factory())
    web_fixture.reahl_server.set_app(wsgi_app)
    browser = web_fixture.driver_browser

    fixture.should_pause_to_simulate_long_refresh = False
    browser.open('/')

    fixture.should_pause_to_simulate_long_refresh = True
    with web_fixture.reahl_server.in_background(wait_till_done_serving=False):
        browser.click(XPath.option_with_text('Three'))

    assert fixture.is_form_blocked(browser)

    fixture.simulate_long_refresh_done()
    assert browser.wait_for(query_string_fixture.is_state_now, 3)
    assert not fixture.is_form_blocked(browser)


@with_fixtures(WebFixture, ResponsiveDisclosureFixture, SqlAlchemyFixture, QueryStringFixture)
def test_form_values_are_not_persisted_until_form_is_submitted(web_fixture, responsive_disclosure_fixture, sql_alchemy_fixture, query_string_fixture):
    """Values submitted via ajax are used only to redraw the screen; they are only changed on the underlying domain once the form is submitted."""

    fixture = responsive_disclosure_fixture

    class ModelObject(Base):
        __tablename__ = 'test_responsive_disclosure_rollback'
        id = Column(Integer, primary_key=True)
        number = Column(Integer)
        choice = Column(Integer, default=1)

        @exposed
        def fields(self, fields):
            fields.choice = ChoiceField([Choice(1, IntegerField(label='One')),
                                         Choice(2, IntegerField(label='Two')),
                                         Choice(3, IntegerField(label='Three'))],
                                         label='Choice')
    fixture.ModelObject = ModelObject

    class FormWithButton(fixture.MyForm):
        def __init__(self, view, an_object):
            super(FormWithButton, self).__init__(view, an_object)

            self.define_event_handler(self.events.submit)
            self.add_child(ButtonInput(self, self.events.submit))

        @exposed
        def events(self, events):
            events.submit = Event(label='Submit')

    fixture.MyForm = FormWithButton

    with sql_alchemy_fixture.persistent_test_classes(ModelObject):

        model_object = ModelObject(number=123)
        Session.add(model_object)

        class MainWidget(Widget):
            def __init__(self, view):
                super(MainWidget, self).__init__(view)
                an_object = model_object
                self.add_child(fixture.MyForm(view, an_object))
        fixture.MainWidget = MainWidget

        wsgi_app = web_fixture.new_wsgi_app(enable_js=True, child_factory=MainWidget.factory())
        web_fixture.reahl_server.set_app(wsgi_app)
        browser = web_fixture.driver_browser
        browser.open('/')

        assert model_object.choice == 1
        browser.click(XPath.option_with_text('Three'))

        assert browser.wait_for(query_string_fixture.is_state_now, 3)  # The screen was updated,
        assert model_object.choice == 1                                # but the database not.

        browser.click(XPath.button_labelled('Submit'))
        assert browser.wait_for(query_string_fixture.is_state_now, 3)
        assert model_object.choice == 3                                # Now the database is updated too.


class DisclosedInputFixture(Fixture):

    def new_trigger_input_type(self):
        return CheckboxInput

    def new_raise_domain_exception_on_submit(self):
        return False

    def new_default_trigger_field_value(self):
        return True

    def new_MyForm(self):
        fixture = self
        class ModelObject(object):
            def __init__(self):
                self.trigger_field = fixture.default_trigger_field_value
                self.email = None

            @exposed
            def events(self, events):
                events.an_event = Event(label='click me', action=Action(self.submit))

            def submit(self):
                if fixture.raise_domain_exception_on_submit:
                    raise DomainException()
                fixture.submitted_model_object = self

            @exposed
            def fields(self, fields):
                fields.trigger_field = BooleanField(label='Trigger field')
                fields.email = EmailField(required=True, label='Email')

        class MyForm(Form):
            def __init__(self, view):
                super(MyForm, self).__init__(view, 'myform')
                self.enable_refresh()
                if self.exception:
                    self.add_child(P(view, text='Exception raised'))

                model_object = ModelObject()
                checkbox_input = fixture.trigger_input_type(self, model_object.fields.trigger_field, refresh_widget=self)
                self.add_child(Label(view, for_input=checkbox_input))
                self.add_child(checkbox_input)

                self.add_child(fixture.MyChangingWidget(self, model_object))

                self.define_event_handler(model_object.events.an_event)
                self.add_child(ButtonInput(self, model_object.events.an_event))
        return MyForm

    def new_MyChangingWidget(self):
        fixture = self
        class MyChangingWidget(Div):
            def __init__(self, form, model_object):
                self.model_object = model_object
                super(MyChangingWidget, self).__init__(form.view, css_id='requiredinfoid')

                if self.model_object.trigger_field:
                    email_input = TextInput(form, self.model_object.fields.email)
                    self.add_child(Label(form.view, for_input=email_input))
                    self.add_child(email_input)

        return MyChangingWidget


@with_fixtures(WebFixture, DisclosedInputFixture)
def test_validation_of_undisclosed_yet_required_input(web_fixture, disclosed_input_fixture):
    """If a Field has a required constraint, but its Input is not currently displayed as part of the form (because of the
       state of another Input), and the form is submitted, the constraint should not cause an exception(input was omitted)."""

    fixture = disclosed_input_fixture

    wsgi_app = web_fixture.new_wsgi_app(enable_js=True, child_factory=fixture.MyForm.factory())
    web_fixture.reahl_server.set_app(wsgi_app)
    browser = web_fixture.driver_browser
    browser.open('/')

    assert browser.is_element_present(XPath.input_labelled('Email'))
    browser.click(XPath.input_labelled('Trigger field'))
    assert not browser.is_element_present(XPath.input_labelled('Email'))
    browser.click(XPath.button_labelled('click me'))

    assert not fixture.submitted_model_object.email


@with_fixtures(WebFixture, DisclosedInputFixture)
def test_input_values_retained_upon_domain_exception(web_fixture, disclosed_input_fixture):
    """When a domain exception occurs the values typed into an input are retained on the error page."""
    # Note: the implementation of this is different for dynamic stuff than for plain old forms.
    #
    # Client state is maintained (for a subsequent GET) by posting it to the server in a hidden input; and also saved on an exception.
    # This state is used at Widget construction stage (before the POST is handled) to ensure all Widgets on the View are built as 
    # before, and as per the client state.
    # 
    # This test is about how that state is managed and when which version of the state (saved in DB, POSTed etc) takes precedence.

    fixture = disclosed_input_fixture

    fixture.raise_domain_exception_on_submit = True
    fixture.default_trigger_field_value = False

    wsgi_app = web_fixture.new_wsgi_app(enable_js=True, child_factory=fixture.MyForm.factory())
    web_fixture.reahl_server.set_app(wsgi_app)
    browser = web_fixture.driver_browser
    browser.open('/')

    assert not browser.is_element_present(XPath.input_labelled('Email'))
    browser.click(XPath.input_labelled('Trigger field'))
    browser.type(XPath.input_labelled('Email'), 'expectme@example.org')
    browser.click(XPath.button_labelled('click me'))

    assert browser.is_element_present(XPath.paragraph_containing('Exception raised'))
    assert browser.is_checked(XPath.input_labelled('Trigger field'))
    assert browser.get_value(XPath.input_labelled('Email')) == 'expectme@example.org'


@with_fixtures(WebFixture, DisclosedInputFixture)
def test_inputs_cleared_after_domain_exception_resubmit(web_fixture, disclosed_input_fixture):
    """After a domain exception followed by a successful submit, saved state on the server is 
       cleared, so that newly rendered inputs on the same URL will have defaulted values again."""
    # Also see related comment on test_input_values_retained_upon_domain_exception

    fixture = disclosed_input_fixture


    wsgi_app = web_fixture.new_wsgi_app(enable_js=True, child_factory=fixture.MyForm.factory())
    web_fixture.reahl_server.set_app(wsgi_app)
    browser = web_fixture.driver_browser

    # First get a domain exception
    fixture.raise_domain_exception_on_submit = True
    fixture.default_trigger_field_value = False
    browser.open('/')
 
    browser.click(XPath.input_labelled('Trigger field'))
    browser.type(XPath.input_labelled('Email'), 'expectme@example.org')
    browser.click(XPath.button_labelled('click me'))
    assert browser.is_element_present(XPath.paragraph_containing('Exception raised'))

    # Then successful commit
    fixture.raise_domain_exception_on_submit = False

    browser.click(XPath.button_labelled('click me'))

    # Values are all defaulted like on a first render
    assert not browser.is_element_present(XPath.paragraph_containing('Exception raised'))
    assert not browser.is_checked(XPath.input_labelled('Trigger field'))
    assert not browser.is_element_present(XPath.paragraph_containing('Email'))
    browser.click(XPath.input_labelled('Trigger field'))
    assert browser.get_value(XPath.input_labelled('Email')) == ''


@with_fixtures(WebFixture, DisclosedInputFixture)
def test_correct_tab_order_for_responsive_widgets(web_fixture, disclosed_input_trigger_fixture):
    """When a user TAB's out of an input that then triggers a change, the tab is ignored and focus stays on the original input so that the tab order can be recalculated."""

    fixture = disclosed_input_trigger_fixture
    fixture.trigger_input_type = TextInput
    fixture.default_trigger_field_value = False

    wsgi_app = web_fixture.new_wsgi_app(enable_js=True, child_factory=fixture.MyForm.factory())

    web_fixture.reahl_server.set_app(wsgi_app)
    browser = web_fixture.driver_browser
    browser.open('/')

    # Case: a new input appears in next tab order position
    assert browser.get_value(XPath.input_labelled('Trigger field')) == 'off'
    browser.press_tab()
    assert browser.is_focus_on(XPath.input_labelled('Trigger field'))
    browser.type(XPath.input_labelled('Trigger field'), 'on')
    browser.press_tab()
    browser.press_tab()
    assert browser.is_focus_on(XPath.input_labelled('Email'))
    
    # Case: an input disappears from the next tab order position
    browser.type(XPath.input_labelled('Trigger field'), 'off')
    browser.press_tab()
    browser.press_tab()
    assert browser.is_focus_on(XPath.button_labelled('click me'))


@with_fixtures(WebFixture, DisclosedInputFixture)
def test_ignore_button_click_on_change(web_fixture, disclosed_input_trigger_fixture):
    """If a button click triggers a change to the page (due to a modified TextInput losing focus), the click is ignored."""

    fixture = disclosed_input_trigger_fixture
    fixture.trigger_input_type = TextInput
    fixture.default_trigger_field_value = False

    wsgi_app = web_fixture.new_wsgi_app(enable_js=True, child_factory=fixture.MyForm.factory())

    web_fixture.reahl_server.set_app(wsgi_app)
    browser = web_fixture.driver_browser
    browser.open('/')

    assert browser.get_value(XPath.input_labelled('Trigger field')) == 'off'
    assert not browser.is_element_present(XPath.input_labelled('Email'))

    browser.type(XPath.input_labelled('Trigger field'), 'on')
    with browser.no_page_load_expected():
        browser.click(XPath.button_labelled('click me'))

    assert browser.is_focus_on(XPath.input_labelled('Trigger field'))
    assert browser.is_element_present(XPath.input_labelled('Email'))
    assert browser.is_on_top(XPath.button_labelled('click me'))


class NestedResponsiveDisclosureFixture(Fixture):

    def new_ModelObject(self):
        class ModelObject(object):
            def __init__(self):
                self.trigger_field = False
                self.nested_trigger_field = False

            @exposed
            def fields(self, fields):
                fields.trigger_field = BooleanField(label='Trigger field')
                fields.nested_trigger_field = BooleanField(label='Nested trigger field')

        return ModelObject

    def new_MyForm(self):
        fixture = self
        class MyForm(Form):
            def __init__(self, view):
                super(MyForm, self).__init__(view, 'myform')
                model_object = fixture.ModelObject()
                self.add_child(fixture.MyChangingWidget(self, model_object))
        return MyForm

    def new_MyChangingWidget(self):
        fixture = self

        class MyNestedChangingWidget(Div):
            def __init__(self, form, model_object):
                self.model_object = model_object
                super(MyNestedChangingWidget, self).__init__(form.view, css_id='nested_changing_widget')
                self.enable_refresh()

                nested_checkbox_input = CheckboxInput(form, model_object.fields.nested_trigger_field, refresh_widget=self)
                self.add_child(Label(self.view, for_input=nested_checkbox_input))
                self.add_child(nested_checkbox_input)

                if self.model_object.nested_trigger_field:
                    self.add_child(P(self.view, 'My state is now showing nested responsive content'))


        class MyChangingWidget(Div):
            def __init__(self, form, model_object):
                self.model_object = model_object
                super(MyChangingWidget, self).__init__(form.view, css_id='requiredinfoid')
                self.enable_refresh()

                checkbox_input = CheckboxInput(form, model_object.fields.trigger_field, refresh_widget=self)
                self.add_child(Label(self.view, for_input=checkbox_input))
                self.add_child(checkbox_input)

                if self.model_object.trigger_field:
                    self.add_child(P(self.view, 'My state is now showing outer responsive content'))
                    self.add_child(MyNestedChangingWidget(form, model_object))

        return MyChangingWidget

    def are_all_parts_enabled(self, browser):
        return browser.is_interactable(XPath.input_labelled('Trigger field')) and \
            browser.is_interactable(XPath.input_labelled('Nested trigger field')) and \
            browser.is_on_top(XPath.paragraph_containing('showing nested responsive content'))


@with_fixtures(WebFixture, QueryStringFixture, NestedResponsiveDisclosureFixture)
def test_inputs_and_widgets_work_when_nested(web_fixture, query_string_fixture, nested_responsive_disclosure_fixture):
    """Refreshable widgets can be nested inside a target widget."""
    
    fixture = nested_responsive_disclosure_fixture
    wsgi_app = web_fixture.new_wsgi_app(enable_js=True, child_factory=fixture.MyForm.factory())

    web_fixture.reahl_server.set_app(wsgi_app)
    browser = web_fixture.driver_browser
    browser.open('/')

    assert browser.wait_for_not(query_string_fixture.is_state_now, 'showing outer responsive content')
    assert browser.wait_for_not(query_string_fixture.is_state_now, 'showing nested responsive content')

    browser.click(XPath.input_labelled('Trigger field'))
    assert browser.wait_for(query_string_fixture.is_state_now, 'showing outer responsive content')
    assert browser.wait_for_not(query_string_fixture.is_state_now, 'showing nested responsive content')
    
    browser.click(XPath.input_labelled('Nested trigger field'))
    assert browser.wait_for(query_string_fixture.is_state_now, 'showing outer responsive content')
    assert browser.wait_for(query_string_fixture.is_state_now, 'showing nested responsive content')

    assert browser.wait_for(fixture.are_all_parts_enabled, browser)

    browser.click(XPath.input_labelled('Trigger field'))
    assert browser.wait_for_not(query_string_fixture.is_state_now, 'showing outer responsive content')
    assert browser.wait_for_not(query_string_fixture.is_state_now, 'showing nested responsive content')

    # Case: after having loaded the nested bits via ajax (and their Javascript - a second time)
    #  the nested case still works (necessary to test because loading JS a second time can cause bugs)
    browser.click(XPath.input_labelled('Trigger field'))
    assert browser.wait_for(query_string_fixture.is_state_now, 'showing outer responsive content')
    assert browser.wait_for_not(query_string_fixture.is_state_now, 'showing nested responsive content')

    browser.click(XPath.input_labelled('Nested trigger field'))
    assert browser.wait_for(query_string_fixture.is_state_now, 'showing outer responsive content')
    assert browser.wait_for(query_string_fixture.is_state_now, 'showing nested responsive content')

    assert browser.wait_for(fixture.are_all_parts_enabled, browser)



@with_fixtures(WebFixture, DisclosedInputFixture)
def test_clear_previously_given_user_input(web_fixture, disclosed_input_fixture):
    """If a an input is refreshed as part of a Widget, and disappears, then reappears after a second refresh, its input is defaulted to the model value."""

    fixture = disclosed_input_fixture
    wsgi_app = web_fixture.new_wsgi_app(enable_js=True, child_factory=fixture.MyForm.factory())

    web_fixture.reahl_server.set_app(wsgi_app)
    browser = web_fixture.driver_browser

    user_input = 'valid.email@example.org'
    browser.open('/')

    browser.type(XPath.input_labelled('Email'), user_input)

    browser.click(XPath.input_labelled('Trigger field'))
    browser.wait_for_not(browser.is_visible, XPath.input_labelled('Email'))
    browser.click(XPath.input_labelled('Trigger field'))
    retained_value = browser.get_value(XPath.input_labelled('Email'))
    assert retained_value == ''
    assert retained_value != user_input


@with_fixtures(WebFixture, QueryStringFixture, ResponsiveDisclosureFixture)
def test_browser_back_after_state_changes_goes_to_previous_url(web_fixture, query_string_fixture, responsive_disclosure_fixture):
    """If a browser stores an URL in its history, which is the same as the one a user is currently on, 
       when you navigate history to get back to that URL, the page is rendered with newer state."""

    fixture = responsive_disclosure_fixture

    wsgi_app = web_fixture.new_wsgi_app(enable_js=True, child_factory=fixture.MainWidget.factory())
    web_fixture.reahl_server.set_app(wsgi_app)
    browser = web_fixture.driver_browser

    class FormWithButton(fixture.MyForm):
        def __init__(self, view, an_object):
            super(FormWithButton, self).__init__(view, an_object)

            self.define_event_handler(self.events.submit)
            self.add_child(ButtonInput(self, self.events.submit))

        @exposed
        def events(self, events):
            events.submit = Event(label='Submit')

    fixture.MyForm = FormWithButton

    # create some state on the server side for this URL
    browser.open('/')
    assert browser.wait_for(query_string_fixture.is_state_now, 1)
    browser.select(XPath.select_labelled('Choice'), 'Two')
    assert browser.wait_for(query_string_fixture.is_state_now, 2)

    # submit the page, so we get redirected to the same URL, leaving itself in browser history (webkit only)
    browser.click(XPath.button_labelled('Submit'))
    assert browser.current_url.path == '/'

    # create different state on the same URL we were redirected to 
    browser.select(XPath.select_labelled('Choice'), 'Three')

    # when the user navigates back to the same url in history, the page retains the youngest state
    browser.go_back() 
    browser.wait_for_page_to_load() # to prevent it from flipping - we know it is reloaded in js
    assert browser.current_url.path == '/'
    assert browser.wait_for(query_string_fixture.is_state_now, 3)


# TODO: 
# - dealing with nestedforms that appear inside a DynamicWidget

# TODO:
# - change responsive disclosure example to include updating AllocationDetailSection
#   eg, percentage and amount columns always displayed; wen tabbing out of a percentage, recalculate corresponding amount
#   

# TODO:
# - You can make an input refresh a refreshable widget by adding an argument to its constructor
# - You can make the widget do stuff upon refresh by adding an Event to its constructor
# - check that read-only inputs in state are not inputted / become validation errors?
# - check that input values are updated with values recalculated on the model
#    - also for read-only ones
# - check that other stuff, such as P with content based on recalculated model values are updated
# - check that the model is NOT updated during an ajax call... only once you submit the form.
# - something to say here about working with a persisted vs transient object and what will work/not

# - update_value_in_disambiguated_input for MultiChoiceField still needs to be implemented
# Unrelated: get_value_from_input of CheckboxSelectInput | a bug - see test_marshalling_of_checkbox_select_input, and add a similar test using a BooleanField
    # def get_value_from_input(self, input_values):
    #     if self.bound_field.allows_multiple_selections:
    #         return input_values.getall(self.name)
    #     else:
    #         return input_values.get(self.name, self.bound_field.false_value) #TODO: this fixes a bug - see test_marshalling_of_checkbox_select_input, and add a similar test using a BooleanField


# Nuke core related to using inputs as trigger inputs aka widget arguments
# nuke javascript code that used to block and unblock stuff

# Nuke enable_refresh(on_refresh=on_refresh) and DynamicSection
#- reahl/web_dev/inputandvalidation/test_widgetqueryargs.py:228 test_refresh_widget_without_query_fields_raises_error[web_fixture0]
#--> no need to check this anymore..see  enable_refresh(code commented out)
