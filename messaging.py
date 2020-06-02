import threading
from typing import List


class Message:
    def __init__(self):
        self._lines = []

    def add_line(self, line: str):
        self._lines.append(line)

    def get_lines(self) -> List[str]:
        return self._lines.copy()


class Listener:
    def __init__(self):
        self._lock = threading.Lock()

    """
    Sends the given message to this Listener. The Listener gets the _lines attribute from the message and prints
    all the lines, in order, to the screen. One element of the list per line of the console.
    
    This method is thread-safe, meaning that if multiple threads send Messages to one Listener, the messages will each
    be printed in their entirety and without interweaving, in the order in which they made their calls to the Listener
    """

    def send(self, message: Message):
        with self._lock:
            for line in message.get_lines():
                print(line)
