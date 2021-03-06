
from reahl.web.fw import UserInterface, Widget
from reahl.web.bootstrap.page import HTML5Page
from reahl.web.bootstrap.ui import TextNode, Div, H, P
from reahl.web.bootstrap.navbar import Navbar, ResponsiveLayout
from reahl.web.bootstrap.grid import Container


class AddressBookPage(HTML5Page):
    def __init__(self, view):
        super().__init__(view)
        self.body.use_layout(Container())

        layout = ResponsiveLayout('md', colour_theme='dark', bg_scheme='primary')
        navbar = Navbar(view, css_id='my_nav').use_layout(layout)
        navbar.layout.set_brand_text('Address book')
        navbar.layout.add(TextNode(view, 'All your addresses in one place'))

        self.body.add_child(navbar)
        self.body.add_child(AddressBookPanel(view))


class AddressBookPanel(Div):
    def __init__(self, view):
        super().__init__(view)

        self.add_child(H(view, 1, text='Addresses'))

        for address in [Address('John', 'john.doe@example.org'),
                        Address('Jane', 'jane.doe@example.org')]:
            self.add_child(AddressBox(view, address))


class AddressBox(Widget):
    def __init__(self, view, address):
        super().__init__(view)
        self.add_child(P(view, text='%s: %s' % (address.name, address.email_address)))


class AddressBookUI(UserInterface):
    def assemble(self):
        self.define_view('/', title='Address book', page=AddressBookPage.factory())


class Address:
    def __init__(self, name, email_address):
        self.name = name
        self.email_address = email_address

