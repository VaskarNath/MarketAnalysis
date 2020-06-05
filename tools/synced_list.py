import threading
from typing import List, Optional

from tools.node import Node


class SyncedList:
    """
    A pop-only and thread-safe Stack implemented using a LinkedList. Houses a list of strings, and makes use of a thread
    Lock so as to allow the list to be shared safe as an input between multiple threads. Provides fast and efficient
    access to the front of the list thanks to the LinkedList implementation.

    Works especially well, for example, as a repository for a central list of stock symbols being operated on by
    multiple different threads.
    """

    def __init__(self, init: List[str]):
        """
        Creates a LinkedList copy of <init>
        """
        self._lock = threading.Lock()
        if len(init) >= 1:
            self._head = Node(init[0])
            last = self._head

            for val in init[1:]:
                node = Node(val)
                last.next = node
                last = node

    def pop(self) -> Optional[str]:
        """
        Removes the first element of the list and returns it. Returns null if the list is empty.

        This method is thread-safe.
        """
        with self._lock:
            if self._head is None:
                return None
            else:
                head = self._head
                self._head = self._head.next
                return head.val

    def __str__(self):
        """
        Return a string representation of this object. Mimics exactly the String representation of a normal list. That
        is, returns the contents of the list, comma-delimited and encased in "[...]"
        """
        rep = "["

        node = self._head
        while node is not None:
            if node.next is None:
                rep += node.val
            else:
                rep += node.val + ", "

            node = node.next

        rep += "]"

        return rep
