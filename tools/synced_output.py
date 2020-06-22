import threading
from tools.messaging import Message


class SyncedFile:
    """
    This class provides a thread-safe way for a script to save results, for example a list of securities that have
    produced buy signals, in a file.
    """

    def __init__(self, file: str):
        """
        Create a new SyncedFile set to send output to the given file
        Args:
            file: a path to the file that this object should write to
        """
        self._file = open(file, "w")
        self._lock = threading.Lock()

    def save(self, msg: Message):
        """
        Write the contents of the given Message to this object's file
        Args:
            msg: an object containing the content that this object should write to the console

        Returns:
            Nothing
        """
        with self._lock:
            lines = msg.get_lines()
            for line in lines:
                self._file.write(line + "\n")
            self._file.flush()
