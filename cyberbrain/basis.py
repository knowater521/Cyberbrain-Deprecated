"""Some basic data structures used throughout the project."""

import sys
from collections import defaultdict
from typing import Dict, Tuple, NamedTuple, Union


# "surrounding" is a 2-element tuple (start_lineno, end_lineno), representing a
# logical line. Line number is frame-wise.
#
# For single-line statement, start_lineno = end_lineno, and is the line number of the
# physical line returned by get_lineno_from_lnotab.
#
# For multiline statement, start_lineno is the line number of the first physical line,
# end_lineno is the last. Lines from start_lineno to end_lineno -1 should end with
# token.NL(or tokenize.NL before 3.7), line end_lineno should end with token.NEWLINE.
#
# Example:
# 0    a = true
# 1    a = true
# 2    b = {
# 3        'foo': 'bar'
# 4    }
# 5    c = false
#
# For the assignment of b, start_lineno = 2, end_lineno = 4
Surrounding = NamedTuple("Surrounding", [("start_lineno", int), ("end_lineno", int)])

SourceLocation = NamedTuple("SourceLocation", [("filepath", str), ("lineno", int)])


class FrameID:
    """Class that represents a frame.

    Basically, a frame id is just a tuple, where each element represents the frame index
    within the same parent frame. For example, consider this snippet:

    def f(): g()

    def g(): pass

    f()
    f()

    Assuming the frame id for global frame is (0,). We called f two times with two
    frames (0, 0) and (0, 1). f calls g, which also generates two frames (0, 0, 0) and
    (0, 1, 0). By comparing prefixes, it's easy to know whether one frame is the parent
    frame of the other.

    We also maintain the frame id of current code location. New frame ids are generated
    based on event type and current frame id.
    """

    current_ = (0,)

    # Mapping from parent frame id to max child frame index.
    child_index: Dict[Tuple, int] = defaultdict(int)

    def __init__(self, frame_id_tuple):
        self._frame_id_tuple = frame_id_tuple

    def __eq__(self, other):
        return self._frame_id_tuple == other._frame_id_tuple

    @property
    def tuple(self):
        return self._frame_id_tuple

    @classmethod
    def current(cls):
        return FrameID(cls.current_)

    @property
    def parent(self):
        return FrameID(self._frame_id_tuple[:-1])

    def is_child_of(self, other):
        return other == self._frame_id_tuple

    def is_parent_of(self, other):
        return self == other._frame_id_tuple

    @classmethod
    def create(cls, event: str):
        if event == "line":
            return cls.current()
        elif event == "call":
            frame_id = cls.current()
            cls.current_ = cls.current_ + (cls.child_index[cls.current_],)
            return frame_id  # callsite is in caller frame.
        elif event == "return":
            cls.current_ = cls.current_[:-1]
            # After exiting call frame, increments call frame's child index.
            cls.child_index[cls.current_] += 1
            return cls.current()
        else:
            raise AttributeError("event type wrong: ", event)

    def __str__(self):
        """Prints the tuple representation."""
        return str(self._frame_id_tuple)


class ID:
    """A class that represents an identifier.

    Since the same identifer can exist in different scopes, we have to differenciate
    them by saving their frame id.
    """

    def __init__(self, name, frame_id_or_tuple: Union[FrameID, Tuple[int, ...]]):
        """For simplicity, accepts both a FramdID and its tuple representation."""
        self.name = name
        if isinstance(frame_id_or_tuple, FrameID):
            self.frame_id = frame_id_or_tuple
        elif isinstance(frame_id_or_tuple, tuple):
            self.frame_id = FrameID(frame_id_or_tuple)
        self._key = (name, self.frame_id.tuple)

    def __eq__(self, other):
        return self._key == other._key

    def __hash__(self):
        return hash(self._key)

    def __repr__(self):
        return str(self._key)
