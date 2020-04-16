


from sqlalchemy import Column, Integer, UnicodeText
from reahl.sqlalchemysupport import Session, Base

from reahl.web.fw import UserInterface, Widget
from reahl.web.bootstrap.page import HTML5Page
from reahl.web.bootstrap.ui import Div, P, H
from reahl.web.bootstrap.forms import Form, TextInput, Button, FieldSet, FormLayout, ButtonLayout
from reahl.web.bootstrap.grid import Container
from reahl.component.modelinterface import exposed, EmailField, Field, Event, Action


class AddressBookUI(UserInterface):
    def assemble(self):
        self.define_view('/', title='Addresses', page=AddressBookPage.factory())


class AddressBookPage(HTML5Page):
    def __init__(self, view):
        super(AddressBookPage, self).__init__(view)
        self.body.use_layout(Container())
        self.body.add_child(AddressBookPanel(view))


class AddressBookPanel(Div):
    def __init__(self, view):
        super(AddressBookPanel, self).__init__(view)

        self.add_child(H(view, 1, text='Addresses'))
        
        for address in Session.query(Address).all():
            self.add_child(AddressBox(view, address))

        self.add_child(AddAddressForm(view))


class AddAddressForm(Form):
    def __init__(self, view):
        super(AddAddressForm, self).__init__(view, 'add_form')

        new_address = Address()

        grouped_inputs = self.add_child(FieldSet(view, legend_text='Add an address'))
        grouped_inputs.use_layout(FormLayout())
        grouped_inputs.layout.add_input(TextInput(self, new_address.fields.name))
        grouped_inputs.layout.add_input(TextInput(self, new_address.fields.email_address))

        self.define_event_handler(new_address.events.save)
        btn = grouped_inputs.add_child(Button(self, new_address.events.save))
        btn.use_layout(ButtonLayout(style='primary'))


class AddressBox(Widget):
    def __init__(self, view, address):
        super(AddressBox, self).__init__(view)
        self.add_child(P(view, text='%s: %s' % (address.name, address.email_address)))


class Address(Base):
    __tablename__ = 'addressbook2bootstrap_address'

    id            = Column(Integer, primary_key=True)
    email_address = Column(UnicodeText)
    name          = Column(UnicodeText)

    @exposed
    def fields(self, fields):
        fields.name = Field(label='Name', required=True)
        fields.email_address = EmailField(label='Email', required=True)

    def save(self):
        Session.add(self)
        
    @exposed
    def events(self, events):
        events.save = Event(label='Save', action=Action(self.save))

