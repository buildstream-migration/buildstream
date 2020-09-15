#
#  Copyright (C) 2020 Bloomberg Finance LP
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library. If not, see <http://www.gnu.org/licenses/>.
#

# XXX: we should reorganize those modules after the source tests have
#      been refactored
# pylint: disable=cyclic-import

from .build_checkout import BuildCheckoutBstStandardSourceTests
from .fetch import FetchBstStandardSourceTests
from .mirror import MirroBstStandardSourceTests

__all__ = ["BstStandardSourceTests"]


class BstStandardSourceTests(
    BuildCheckoutBstStandardSourceTests, FetchBstStandardSourceTests, MirroBstStandardSourceTests
):
    """Definition of standardized tests that each source should pass."""
