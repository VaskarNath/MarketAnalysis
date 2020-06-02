from typing import List, Optional
from node import Node
import threading
import time
import concurrent


class SyncedList:
    """
    A LinkedList modified so as to be thread-safe. It houses a list of Strings, and provides a quick, efficient, and
    synchronized way for multiple threads to have access to a central list of stock symbols to analyze.

    Only allows values to be read from the beginning of the list, which is perfectly suited to the desired end.
    """

    """
    Initialize this synced list using the given list
    """

    def __init__(self, init: List[str]):
        self._lock = threading.Lock()
        if len(init) >= 1:
            self._head = Node(init[0])
            last = self._head

            for val in init[1:]:
                node = Node(val)
                last.next = node
                last = node

    """
    Removes the first element of the list and returns it.
    
    This method is thread-safe.
    """

    def pop(self) -> Optional[str]:
        with self._lock:
            if self._head is None:
                return None
            else:
                print("Entering lock")
                head = self._head
                self._head = self._head.next
                print("Exiting lock")
                return head.val

    """
    Return a string representation of this object. Mimics exactly the String representation of a normal list.
    """

    def __str__(self):
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
