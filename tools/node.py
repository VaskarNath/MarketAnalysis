"""
Represents a Node in a linked list, with a value (a string) and a next pointer
"""


class Node:
    def __init__(self, val: str, init_next=None):
        self.val = val
        self.next = init_next
