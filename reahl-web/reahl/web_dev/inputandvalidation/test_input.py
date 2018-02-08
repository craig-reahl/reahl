# Copyright 2013-2016 Reahl Software Services (Pty) Ltd. All rights reserved.
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
import re

from reahl.tofu import Fixture, scenario, expected, uses, NoException
from reahl.tofu.pytestsupport import with_fixtures
from reahl.stubble import EmptyStub, stubclass

from reahl.web.ui import HTMLElement, PrimitiveInput, Form, CheckboxInput, TextInput, Label, ButtonInput,\
                          PasswordInput, TextArea, SelectInput, RadioButtonSelectInput, CheckboxSelectInput

from reahl.component.modelinterface import Field, EmailField, BooleanField, Event, Allowed, exposed, \
    Action, Choice, ChoiceGroup, ChoiceField, IntegerField, MultiChoiceField, DateField
from reahl.component.exceptions import IsInstance, ProgrammerError
from reahl.webdev.tools import WidgetTester
from reahl.webdev.tools import XPath

from reahl.web_dev.fixtures import WebFixture
from reahl.component_dev.test_field import FieldFixture


@uses(web_fixture=WebFixture, field_fixture=FieldFixture)
class SimpleInputFixture(Fixture):

    def new_field(self):  # not a delegated property, because some scenarios override this by setting self.field
        return self.field_fixture.new_field()

    def new_model_object(self): # not a delegated property, because some classes override it
        return self.field_fixture.new_model_object()

    def new_form(self):
        return Form(self.web_fixture.view, 'test')

    def new_event(self, label='click me'):
        event = Event(label=label)
        event.bind('aname', None)
        self.form.define_event_handler(event)
        return event


class SimpleInputFixture2(SimpleInputFixture):
    def new_field(self, label='the label'):
        return Field(label=label)
    def new_model_object(self):
        fixture = self
        class ModelObject(object):
            def handle_event(self):
                pass
            @exposed
            def events(self, events):
                events.an_event = Event(label='click me', action=Action(self.handle_event))
            @exposed
            def fields(self, fields):
                fields.an_attribute = fixture.field
        return ModelObject()

    def new_Form(self, input_widget_class=None):
        fixture = self
        input_widget_class = input_widget_class or CheckboxSelectInput
        class MyForm(Form):
            def __init__(self, view, name):
                super(MyForm, self).__init__(view, name)
                checkbox = self.add_child(input_widget_class(self, fixture.model_object.fields.an_attribute))
                self.define_event_handler(fixture.model_object.events.an_event)
                self.add_child(ButtonInput(self, fixture.model_object.events.an_event))
                fixture.checkbox = checkbox
        return MyForm


class InputStateFixture(SimpleInputFixture):
    def new_field(self):
        field = EmailField(default='default value')
        field.bind('an_attribute', self.model_object)
        return field

    def new_input(self):
        @stubclass(PrimitiveInput)
        class InputStub(PrimitiveInput):
            def create_html_widget(self):
                return HTMLElement(self.view, 'input')

        return InputStub(self.form, self.field)

    @scenario
    def defaulted_input_no_value_on_domain(self):
        del self.model_object.an_attribute
        self.input.prepare_input()

        self.expected_state = 'defaulted'
        self.expected_value = 'default value'

    @scenario
    def defaulted_input_value_on_domain(self):
        self.input.prepare_input()
        self.model_object.an_attribute = 'something'

        self.expected_state = 'defaulted'
        self.expected_value = 'something'

    @scenario
    def validly_entered(self):
        self.input.enter_value('someone@home.org')
        self.input.prepare_input()

        self.expected_state = 'validly_entered'
        self.expected_value = 'someone@home.org'

    @scenario
    def empty_input_non_required_field(self):
        self.input.enter_value('')
        self.input.prepare_input()

        self.expected_state = 'validly_entered'
        self.expected_value = ''

    @scenario
    def empty_input_required_field(self):
        self.field.make_required('')
        self.input.enter_value('')
        self.input.prepare_input()

        self.expected_state = 'invalidly_entered'
        self.expected_value = ''

    @scenario
    def invalidly_entered(self):
        self.input.enter_value('not an email address')
        self.input.prepare_input()

        self.expected_state = 'invalidly_entered'
        self.expected_value = 'not an email address'


@with_fixtures(WebFixture, InputStateFixture)
def test_the_states_of_an_input(web_fixture, input_state_fixture):
    """An Input can be in one of three states: defaulted, invalidly_entered or validly_entered. Depending
       on the state of the input, it will have a different value when rendering.

       The states:
         - defaulted: the user has not entered anything
           value:     the value on the model object which is bound to its Field if that object
                      has such an an_attribute, else the default value of the Field.
         - invalidly_entered: the user entered a value which failed validation
           value:             the invalid value which the user entered
         - validly_entered: the user entered a valid value
           value:           the value which the user entered even if the underlying
                            model object has a corresponding value
    """
    fixture = input_state_fixture

    assert fixture.input.get_input_status() == fixture.expected_state
    assert fixture.input.value == fixture.expected_value


class InputScenarios(SimpleInputFixture):
    @scenario
    def text_input(self):
        self.widget = TextInput(self.form, self.field)
        self.expected_html = r'<input name="an_attribute" form="test" type="text" value="field value" class="reahl-textinput">'
        self.field_controls_visibility = True

    @scenario
    def text_input_placeholder_default(self):
        self.widget = TextInput(self.form, self.field, placeholder=True)
        self.expected_html = r'<input name="an_attribute" aria-label="the label" form="test" placeholder="the label" type="text" value="field value" class="reahl-textinput">'
        self.field_controls_visibility = True

    @scenario
    def text_input_placeholder_specified(self):
        self.widget = TextInput(self.form, self.field, placeholder="some text")
        self.expected_html = r'<input name="an_attribute" aria-label="some text" form="test" placeholder="some text" type="text" value="field value" class="reahl-textinput">'
        self.field_controls_visibility = True

    @scenario
    def input_label(self):
        html_input = TextInput(self.form, self.field)
        self.widget = Label(self.web_fixture.view, for_input=html_input)
        self.expected_html = r'<label for="%s">the label</label>' % html_input.css_id
        self.field_controls_visibility = True

    @scenario
    def input_label_with_text(self):
        html_input = TextInput(self.form, self.field)
        self.widget = Label(self.web_fixture.view, for_input=html_input, text='some text')
        self.expected_html = r'<label for="%s">some text</label>' % html_input.css_id
        self.field_controls_visibility = True

    @scenario
    def button_input(self):
        self.widget = self.form.add_child(ButtonInput(self.form, self.event))
        self.expected_html = r'<input name="event.aname\?" form="test" type="submit" value="click me">'
        self.field_controls_visibility = False

    @scenario
    def password(self):
        self.widget = self.form.add_child(PasswordInput(self.form, self.field))
        self.expected_html = r'<input name="an_attribute" form="test" type="password">'
        self.field_controls_visibility = True

    def setup_checkbox_scenario(self, boolean_value):
        self.model_object.an_attribute = boolean_value

        self.field = BooleanField(required=True, label='my text', required_message='$label is needed here')
        self.field.bind('an_attribute', self.model_object)

        self.widget = self.form.add_child(CheckboxInput(self.form, self.field))
        self.field_controls_visibility = True

    @scenario
    def checkbox_true(self):
        """A checkbox needs a 'checked' an_attribute if its field is True. It also renders ONLY the
            validation message for its required validation_constraint, not for all constraints"""
        self.setup_checkbox_scenario(True)
        self.expected_html = r'<input name="an_attribute" checked="checked" data-msg-required="my text is needed here" form="test" required="\*" type="checkbox">'

    @scenario
    def checkbox_false(self):
        self.setup_checkbox_scenario(False)
        self.expected_html = r'<input name="an_attribute" data-msg-required="my text is needed here" form="test" required="\*" type="checkbox">'

    @scenario
    def text_area_input(self):
        self.widget = self.form.add_child(TextArea(self.form, self.field, rows=30, columns=20))
        self.expected_html = r'<textarea name="an_attribute" cols="20" rows="30">field value</textarea>'
        self.field_controls_visibility = True

    @scenario
    def select_input(self):
        self.model_object.an_attribute = 2

        choices = [Choice(False, BooleanField(label='None')),
                   ChoiceGroup('grouped', [
                       Choice(1, IntegerField(label='One')),
                       Choice(2, IntegerField(label='Two'))])
                  ]
        self.field = ChoiceField(choices)
        self.field.bind('an_attribute', self.model_object)

        self.widget = self.form.add_child(SelectInput(self.form, self.field))
        group = r'<optgroup label="grouped"><option value="1">One</option><option selected="selected" value="2">Two</option></optgroup>'
        option = r'<option value="off">None</option>'
        self.expected_html = r'<select name="an_attribute" form="test">%s%s</select>' % (option, group)
        self.field_controls_visibility = True

    @scenario
    def select_input_multi(self):
        self.model_object.an_attribute = [2]

        choices = [Choice(1, IntegerField(label='One')),
                   Choice(2, IntegerField(label='Two'))
                  ]
        self.field = MultiChoiceField(choices)
        self.field.bind('an_attribute', self.model_object)

        self.widget = self.form.add_child(SelectInput(self.form, self.field))
        options = r'<option value="1">One</option><option selected="selected" value="2">Two</option>'
        self.expected_html = r'<select name="an_attribute" form="test" multiple="multiple">%s</select>' % (options)
        self.field_controls_visibility = True

    @scenario
    def checkbox_input_multi(self):
        selected_checkboxes = [2, 3]
        self.model_object.an_attribute = selected_checkboxes

        choices = [Choice(1, IntegerField(label='One')),
                   Choice(2, IntegerField(label='Two')),
                   Choice(3, IntegerField(label='Three'))
                  ]
        self.field = MultiChoiceField(choices)
        self.field.bind('an_attribute', self.model_object)

        self.widget = self.form.add_child(CheckboxSelectInput(self.form, self.field))
        not_checked_option = r'<label><input name="an_attribute" form="test" type="checkbox" value="1">One</label>'
        checked_options = r'<label><input name="an_attribute" checked="checked" form="test" type="checkbox" value="2">Two</label>'
        checked_options += r'<label><input name="an_attribute" checked="checked" form="test" type="checkbox" value="3">Three</label>'
        options = not_checked_option + checked_options
        self.expected_html = r'<div class="reahl-checkbox-input">%s</div>' % (options)
        self.field_controls_visibility = True

    @scenario
    def radio_button(self):
        self.model_object.an_attribute = 2

        choices = [ Choice(1, IntegerField(label='One')),
                    Choice(2, IntegerField(label='Two')) ]
        self.field = ChoiceField(choices)
        self.field.bind('an_attribute', self.model_object)

        self.widget = self.form.add_child(RadioButtonSelectInput(self.form, self.field))

        radio_button = r'<label>'\
                       r'<input name="an_attribute"%s '\
                              r'data-msg-pattern="an_attribute should be one of the following: 1|2" '\
                              r'form="test" pattern="\(1\|2\)" '\
                              r'title="an_attribute should be one of the following: 1\|2" '\
                              r'type="radio" value="%s">%s'\
                       r'</label>'

        outer_div = r'<div class="reahl-radio-button-input">%s</div>'
        buttons = (radio_button % ('', '1', 'One')) +\
                  (radio_button % (' checked="checked"', '2', 'Two'))
        self.expected_html = outer_div % buttons
        self.field_controls_visibility = True


@with_fixtures(InputScenarios)
def test_basic_rendering(input_scenarios):
    """What the rendered html for a number of simple inputs look like."""

    fixture = input_scenarios

    tester = WidgetTester(fixture.widget)
    actual = tester.render_html()
    assert re.match(fixture.expected_html, actual)


@with_fixtures(InputScenarios)
def test_rendering_when_not_allowed(input_scenarios):
    """When not allowed to see the Widget, it is not rendered."""
    fixture = input_scenarios

    tester = WidgetTester(fixture.widget)

    fixture.field.access_rights.readable = Allowed(False)
    fixture.field.access_rights.writable = Allowed(False)
    actual = tester.render_html()
    if fixture.field_controls_visibility:
        assert actual == ''
    else:
        assert re.match(fixture.expected_html, actual)


@with_fixtures(FieldFixture, SimpleInputFixture)
def test_input_wrapped_widgets(field_fixture, simple_input_fixture):
    """An Input is an empty Widget; its contents are supplied by overriding its
       .create_html_widget() method. Several methods for setting HTML-things, like
       css id are delegated to this Widget which represents the Input in HTML.
    """
    fixture = simple_input_fixture

    class MyInput(PrimitiveInput):
        def create_html_widget(self):
            return HTMLElement(self.view, 'x')

    test_input = MyInput(fixture.form, field_fixture.field)
    tester = WidgetTester(test_input)

    rendered = tester.render_html()
    assert rendered == '<x>'

    test_input.set_id('myid')
    test_input.set_title('mytitle')
    test_input.add_to_attribute('list-attribute', ['one', 'two'])
    test_input.set_attribute('an-attribute', 'a value')

    rendered = tester.render_html()
    assert rendered == '<x id="myid" an-attribute="a value" list-attribute="one two" title="mytitle">'


@with_fixtures(SimpleInputFixture)
def test_wrong_args_to_input(simple_input_fixture):
    """Passing the wrong arguments upon constructing an Input results in an error."""

    fixture = simple_input_fixture

    with expected(IsInstance):
        PrimitiveInput(fixture.form, EmptyStub())

    with expected(IsInstance):
        PrimitiveInput(EmptyStub(), Field())


@with_fixtures(WebFixture, SimpleInputFixture2)
def test_marshalling_of_checkbox_input(web_fixture, checkbox_fixture):
    """When a form is submitted, the value of a checkbox is derived from
       whether the checkbox is included in the submission or not."""

    fixture = checkbox_fixture
    fixture.field = BooleanField(label='my text')

    model_object = fixture.model_object
    wsgi_app = web_fixture.new_wsgi_app(child_factory=fixture.new_Form(input_widget_class=CheckboxInput).factory('myform'))
    web_fixture.reahl_server.set_app(wsgi_app)
    web_fixture.driver_browser.open('/')

    # Case: checkbox is submitted with form (ie checked)
    web_fixture.driver_browser.check("//input[@type='checkbox']")
    web_fixture.driver_browser.click("//input[@value='click me']")

    assert model_object.an_attribute
    assert fixture.checkbox.value == 'on'

    # Case: checkbox is not submitted with form (ie unchecked)
    web_fixture.driver_browser.uncheck("//input[@type='checkbox']")
    web_fixture.driver_browser.click("//input[@value='click me']")

    assert not model_object.an_attribute
    assert fixture.checkbox.value == 'off'


@with_fixtures(WebFixture, SimpleInputFixture2)
def test_marshalling_of_checkbox_select_input(web_fixture, checkbox_fixture):
    """CheckboxSelectInput is used to choose many things from a list."""

    fixture = checkbox_fixture
    choices = [Choice(1, IntegerField(label='One')),
               Choice(2, IntegerField(label='Two')),
               Choice(3, IntegerField(label='Three'))]
    fixture.field = MultiChoiceField(choices)

    model_object = fixture.model_object
    model_object.an_attribute = [1]
    wsgi_app = web_fixture.new_wsgi_app(child_factory=fixture.new_Form(input_widget_class=CheckboxSelectInput).factory('myform'))
    web_fixture.reahl_server.set_app(wsgi_app)
    web_fixture.driver_browser.open('/')

    assert web_fixture.driver_browser.is_checked(XPath.input_labelled('One'))
    assert not web_fixture.driver_browser.is_checked(XPath.input_labelled('Two'))
    assert not web_fixture.driver_browser.is_checked(XPath.input_labelled('Three'))

    # Case: checkbox is submitted with form (ie checked)
    web_fixture.driver_browser.uncheck(XPath.input_labelled('One'))
    web_fixture.driver_browser.check(XPath.input_labelled('Two'))
    web_fixture.driver_browser.check(XPath.input_labelled('Three'))
    web_fixture.driver_browser.click(XPath.button_labelled('click me'))

    assert model_object.an_attribute == [2, 3]
    assert fixture.checkbox.value == ['2', '3']
    assert not web_fixture.driver_browser.is_checked(XPath.input_labelled('One'))
    assert web_fixture.driver_browser.is_checked(XPath.input_labelled('Two'))
    assert web_fixture.driver_browser.is_checked(XPath.input_labelled('Three'))


class RadioButtonInputFieldScenarios(Fixture):
    @scenario
    def choice_field(self):
        self.default_domain_value = 1
        self.selected_domain_value = 2
        self.field_class = ChoiceField

    @scenario
    def multi_choice_field(self):
        self.default_domain_value = [1]
        self.selected_domain_value = [2]
        self.field_class = MultiChoiceField


@with_fixtures(WebFixture, SimpleInputFixture2, RadioButtonInputFieldScenarios)
def test_marshalling_of_radio_button_select_input(web_fixture, input_fixture, field_scenario):
    """When a form is submitted, the value of the selected radio button is persisted."""

    fixture = input_fixture
    choices = [Choice(1, IntegerField(label='One')),
               Choice(2, IntegerField(label='Two'))]
    fixture.field = field_scenario.field_class(choices)

    model_object = fixture.model_object
    model_object.an_attribute = field_scenario.default_domain_value

    wsgi_app = web_fixture.new_wsgi_app(child_factory=fixture.new_Form(input_widget_class=RadioButtonSelectInput).factory('myform'))
    web_fixture.reahl_server.set_app(wsgi_app)
    web_fixture.driver_browser.open('/')

    radio_one = XPath.input_labelled('One')
    radio_two = XPath.input_labelled('Two')
    # One is pre selected
    assert web_fixture.driver_browser.is_checked(radio_one)
    assert not web_fixture.driver_browser.is_checked(radio_two)

    # click on Two
    web_fixture.driver_browser.click(radio_two)
    assert not web_fixture.driver_browser.is_checked(radio_one)

    web_fixture.driver_browser.click(XPath.button_labelled('click me'))

    assert model_object.an_attribute == field_scenario.selected_domain_value


@with_fixtures(WebFixture)
def test_checkbox_input_restricted_to_use_with_boolean(web_fixture):
    """CheckboxInput is for toggling a true or false answer."""
    model_object = web_fixture
    form = Form(web_fixture.view, 'test')

    # case: with BooleanField
    boolean_field = BooleanField(label='Boolean')
    boolean_field.bind('a_choice', model_object)
    with expected(NoException):
        CheckboxInput(form, boolean_field)

    # case: with disallowed field
    not_a_boolean_field = IntegerField(label='Other')
    not_a_boolean_field.bind('not_a_boolean', model_object)

    with expected(IsInstance):
        CheckboxInput(form, not_a_boolean_field)


class ManyChoicesScenarios(Fixture):
    @scenario
    def checkbox_select_input(self):
        self.input_type = CheckboxSelectInput
        self.xpath_function_to_choice = XPath.input_labelled

    @scenario
    def select_input(self):
        self.input_type = SelectInput
        self.xpath_function_to_choice = XPath.option_with_text


@with_fixtures(WebFixture, SimpleInputFixture2, ManyChoicesScenarios)
def test_choices_disabled(web_fixture, checkbox_fixture, choice_type_scenario):
    """A choice that is not writable renders as disabled."""

    fixture = checkbox_fixture
    choices = [Choice(1, IntegerField(label='One')),
               Choice(2, IntegerField(label='Two', writable=Allowed(False)))]
    fixture.field = MultiChoiceField(choices)

    model_object = fixture.model_object
    model_object.an_attribute = [1]
    wsgi_app = web_fixture.new_wsgi_app(child_factory=fixture.new_Form(input_widget_class=choice_type_scenario.input_type).factory('myform'))
    web_fixture.reahl_server.set_app(wsgi_app)
    web_fixture.driver_browser.open('/')

    assert web_fixture.driver_browser.is_element_enabled(choice_type_scenario.xpath_function_to_choice('One'))
    assert not web_fixture.driver_browser.is_element_enabled(choice_type_scenario.xpath_function_to_choice('Two'))



class FuzzyTextInputFixture(SimpleInputFixture2):
    def new_field(self, label='the label'):
        return DateField(label=label)


@with_fixtures(WebFixture, FuzzyTextInputFixture)
def test_fuzzy(web_fixture, fuzzy_text_input_fixture):
    """A TextInput can be created as fuzzy=True. Doing this results in the possibly imprecise
       input that was typed by the user to be interpreted server-side and changed to the
       more exact representation in the client browser.  This happens upon the input losing focus."""
    fixture = fuzzy_text_input_fixture

    model_object = fixture.model_object
    class MyForm(Form):
        def __init__(self, view, name):
            super(MyForm, self).__init__(view, name)
            self.add_child(TextInput(self, model_object.fields.an_attribute, fuzzy=True))
            self.define_event_handler(model_object.events.an_event)
            self.add_child(ButtonInput(self, model_object.events.an_event))

    wsgi_app = web_fixture.new_wsgi_app(child_factory=MyForm.factory('myform'), enable_js=True)
    web_fixture.reahl_server.set_app(wsgi_app)
    browser = web_fixture.driver_browser
    browser.open('/')

    browser.type(XPath.input_named('an_attribute'), '20 November 2012')
    browser.press_tab()
    browser.wait_for(browser.is_element_value, XPath.input_named('an_attribute'), '20 Nov 2012')

