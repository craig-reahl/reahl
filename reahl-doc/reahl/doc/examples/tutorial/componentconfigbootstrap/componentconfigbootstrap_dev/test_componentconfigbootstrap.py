
from __future__ import print_function, unicode_literals, absolute_import, division


from reahl.tofu import Fixture, uses
from reahl.tofu.pytest_support import with_fixtures

from reahl.webdev.tools import Browser, XPath

from reahl.doc.examples.tutorial.componentconfigbootstrap.componentconfigbootstrap import AddressBookUI, Address

from reahl.web_dev.fixtures import WebFixture2


@uses(web_fixture=WebFixture2)
class ConfigFixture(Fixture):

    def new_wsgi_app(self):
        return self.web_fixture.new_wsgi_app(site_root=AddressBookUI)

    def new_existing_address(self):
        address = Address(name='John Doe', email_address='johndoe@some.org')
        address.save()
        return address

    def new_browser(self):
        return Browser(self.wsgi_app)

    def address_is_listed_as(self, name, email_address):
        return self.browser.is_element_present(XPath.paragraph_containing('%s: %s' % (name, email_address)))

    def heading_is_displayed(self):
        return self.browser.is_element_present(XPath.heading_with_text(1, 'Addresses'))


@with_fixtures(WebFixture2, ConfigFixture)
def test_add_address(web_fixture, config_fixture):
    """A user can add an address, after which the address is listed."""
    browser = config_fixture.browser

    with web_fixture.context:
        browser.open('/')
        browser.type(XPath.input_labelled('Name'), 'John')
        browser.type(XPath.input_labelled('Email'), 'johndoe@some.org')

        browser.click(XPath.button_labelled('Save'))

        assert config_fixture.address_is_listed_as('John', 'johndoe@some.org')


@with_fixtures(WebFixture2)
def test_config_was_read_from_file(web_fixture):
    """The tests are run with config read from an actual config file, not the default config."""
    assert web_fixture.context.config.componentconfig.showheader == True


@with_fixtures(WebFixture2, ConfigFixture)
def test_configurable_heading(web_fixture, config_fixture):
    """Whether the heading is displayed or not, is configurable."""
    browser = config_fixture.browser
    
    with web_fixture.context:
        web_fixture.context.config.componentconfig.showheader = False
        browser.open('/')
        assert not config_fixture.heading_is_displayed()

        web_fixture.context.config.componentconfig.showheader = True
        browser.open('/')
        assert config_fixture.heading_is_displayed()
