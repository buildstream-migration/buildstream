#
#  Copyright (C) 2018 Bloomberg Finance LP
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
#  Authors: Benjamin Schubert <bschubert15@bloomberg.net>
#

"""Collection utilities not present in the standard library."""


import heapq


class UniquePriorityQueue:
    """
    Implements a priority queue that adds only each key once.

    The queue will store an compute the priority based on the tuple (key, item).
    """

    def __init__(self):
        """Create a new priority queue."""
        self._items = set()
        self._heap = []

    def push(self, key, item):
        """
        Push a new item in the queue.

        If the item is already present in the queue as identified by the key,
        this is a noop.

        :param key: unique key to use for checking for the object's existence
                    and used for ordering.
        :param item: item to store in the queue.
        """
        if key not in self._items:
            self._items.add(key)
            heapq.heappush(self._heap, (key, item))

    def pop(self):
        """
        Pop the next item in the queue, by priority order.

        :return: the next item, without its key.
        """
        key, item = heapq.heappop(self._heap)
        self._items.remove(key)
        return item

    def __len__(self):
        return len(self._heap)
