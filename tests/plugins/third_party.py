import os
import pytest
import pkg_resources

from pluginbase import PluginBase
from buildstream._elementfactory import ElementFactory
from buildstream._sourcefactory import SourceFactory

from tests.testutils.setuptools import entry_fixture

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'third_party'
)


# Simple fixture to create a PluginBase object that
# we use for loading plugins.
@pytest.fixture()
def plugin_fixture():
    return {
        'base': PluginBase(package='buildstream.plugins')
    }


##################################################################
#                              Tests                             #
##################################################################
# Test that external element plugin loading works.
@pytest.mark.datafiles(os.path.join(DATA_DIR, 'third_party_element'))
def test_custom_pip_element(plugin_fixture, entry_fixture, datafiles):
    factory = ElementFactory(plugin_fixture['base'], [])
    assert(isinstance(factory, ElementFactory))

    entry_fixture(datafiles, 'buildstream.plugins', 'third_party_element:foop')

    foo_type, _ = factory.lookup('third_party_element:foop')
    assert(foo_type.__name__ == 'FooElement')


# Test that external source plugin loading works.
@pytest.mark.datafiles(os.path.join(DATA_DIR, 'third_party_source'))
def test_custom_pip_source(plugin_fixture, entry_fixture, datafiles):
    factory = SourceFactory(plugin_fixture['base'], [])
    assert(isinstance(factory, SourceFactory))

    entry_fixture(datafiles, 'buildstream.plugins', 'third_party_source:foop')

    foo_type, _ = factory.lookup('third_party_source:foop')
    assert(foo_type.__name__ == 'FooSource')
