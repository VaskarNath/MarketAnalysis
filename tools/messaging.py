import threading
from typing import List


class Message:
    """
    Is used in conjunction with Listener, below, to allow multiple threads to print to the console
    at once without becoming interwoven or overlapping.

    Simply contains a list of strings to be printed to the console as a discrete block, newlines to be
    placed automatically after each element of the list by Listener.

    Attributes:
        _lines : List[str]
            the list of strings that make up this Message

    """

    def __init__(self):
        """
        Create a new, empty Message.
        """
        self._lines = []

    def add_line(self, line: str):
        """
        Append <line> to this Message
        """
        self._lines.append(line)

    def get_lines(self) -> List[str]:
        """
        Return a COPY of this message's contents; a list of all the lines added to this Message since its creation
        """
        return self._lines.copy()

    def reset(self):
        """
        Reset this Message, emptying its contents so that it can be reused
        """
        self._lines = []


class Listener:
    """
    This object exists as a barrier between multiple threads and the console, acting as a go-between so that threads
    that need to write consecutive lines of text to the screen don't interweave with each other. It interfaces with
    threads through the use of a Message object, which is essentially a wrapper for multiple lines of text that a thread
    wants printed to the screen in a discrete block.

    Attributes:
        _lock : thread.Lock
            The Lock that this object uses to ensure orderly access to the console by client threads
    """

    def __init__(self):
        """
        Create a new Listener, ready for use
        """
        self._lock = threading.Lock()

    def send(self, message: Message):
        """
        Sends the given message to this Listener. The Listener gets the _lines attribute from the message and prints
        all the lines, in order, to the screen. One element of the list per line of the console.

        This method is thread-safe, meaning that if multiple threads send Messages to one Listener, the messages will
        each be printed in their entirety and without interweaving, in the order in which they made their calls to the
        Listener
        """
        with self._lock:
            for line in message.get_lines():
                print(line)
