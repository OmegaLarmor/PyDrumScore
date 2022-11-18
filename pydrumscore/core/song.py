"""
Contains the API for the pydrumscore exporter.
All the objects and functions here are meant to be exploited
by the user in their scoring code.
"""

import math
import logging
from copy import deepcopy
from typing import List

############ Utilities ############
def note_range(start:float, stop:float, step:float, excl: List[float] = None) -> list:
    """Creates a list based on a range and step provided as argument.
    Functions the same way as python's built-in range function, but
    using floats instead of ints. As such, start bound is inclusive and stop
    bound is exclusive.

    Example for eighth notes filling a measure:

    note_range(1, END, 0.5) -> [1, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]

    :param start: (float): First number in the range
    :param stop: (float): Last number in the range (exclusive bound)
    :param step: (float): Step between entries
    :param excl(opt): list(float): List of values to exclude from range

    :returns:
        list: Range of notes from 'start' to 'stop', separated by 'step'
    """
    if not excl:
        excl = []

    # Note: Equivalent to numpy arange(), but without dependency on it
    res = []
    v = start
    while v < stop:
        res.append(v)
        v += step
    return [v for v in res if v not in excl]

END = 5
""" Represents the numerical value of the end of a measure."""
# TODO: Dynamic reassign based on current time sig

############ API Classes ############

class Metadata():
    """
    Contains all the metadata necessary for exporting a song.
    In a song generation file, the global 'metadata' instance of
    this class must be filled with all the relevant information.

    :raises:
        RuntimeError: If data in constructor is not part of valid tags
    """
    # Disable invalid name warning to match the ones in XML
    # For public methods, constructor validation justifies class
    # pylint: disable=invalid-name, too-few-public-methods

    ALL_TAGS = ["arranger" ,
                "composer",
                "copyright",
                "creationDate",
                "lyricist",
                "movementNumber",
                "movementTitle",
                "mscVersion",
                "platform",
                "poet",
                "source",
                "translator",
                "workNumber",
                "subtitle",
                "workTitle"]
    """All tags allowed to be edited in the metadata."""

    def __init__(self, **kwargs) -> None:
        has_error = False
        if kwargs is None:
            kwargs = {}

        # Init all tags to default
        for t in self.ALL_TAGS:
            setattr(self, t, "")

        # Fill from keyword args
        for k,v in kwargs.items():
            if k not in self.ALL_TAGS:
                logging.getLogger(__name__).error("Error: metadata value '%s' is not a valid tags.\
                                                   Check for spelling.", k)
                has_error = True
                continue

            if not has_error:
                setattr(self, k, v)

        if has_error:
            print("See supported tags: ")
            print(*self.ALL_TAGS, sep=", ")
            raise RuntimeError("Metadata creation failed.")

    # pylint: enable=invalid-name

class Measure():
    """
    Contains the time values of all the notes in a given measure,
    as well as any accompanying data such as time signature, text,
    or tempo marking.

    :raises:
        RuntimeError: If assigning to a drumset piece that does not exist
    """

    # pylint: disable=too-many-instance-attributes

    # Filled at init, constant after
    ALL_OPTIONS = None
    ALL_PIECES = None

    def __init__(self, *args, **kwargs) -> None:
        """Creates a Measure based on the given time values for each
        drumset piece.

        Example for a measure of snare, drum, and hi-hat:
        Measure(
            hh = note_range(1, END, 0.5),
            sd = [2,4],
            bd = [1,3],
        )
        (see :func: '~note_range')

        :param kwargs: Times for each instrument in named lists.

        :raises:
            RuntimeError: If data in constructor is not part of valid tags
        """
        # pylint: disable=invalid-name

        if args:
            assert isinstance(args[0], Measure)
            self.__dict__ = deepcopy(args[0].__dict__)
            assert self.ALL_PIECES
            assert self.ALL_OPTIONS
            assert self.USED_PIECES is not None

        else:
            self.ac = []
            self.bd = []
            self.ft = []
            self.sd = []
            self.c1 = []
            self.hh = []
            self.ho = []
            self.rd = []
            self.rb = []
            self.ht = []
            self.hf = []
            self.fm = []
            self.mt = []
            self.cs = []
            self.ALL_PIECES = dict(vars(self))
            self.USED_PIECES = []  # filled at pre-export

            self.has_line_break = False
            """Whether or not to add a line break at the end"""

            self.time_sig = None
            """Time sig to be added at measure start"""

            self.tempo = None
            """Tempo starting from this measure"""

            self.no_repeat = False
            """Do not use repeat symbol for this measure"""

            self.start_repeat = False
            self.end_repeat = False

            self.text = None
            """Text at the beginning of the measure. Useful for lyrics."""

            self.dynamic = None
            """Dynamic of the measure (f, ff, p, mf)..."""

            self.ALL_OPTIONS = {k: v for k,v in vars(self).items() if k not in self.ALL_PIECES}

        has_error = False

        if kwargs is None:
            kwargs = {}

        # Init from user args
        for k,v in kwargs.items():
            if k not in self.ALL_PIECES and k not in self.ALL_OPTIONS:
                logging.getLogger(__name__).error("Measure argument + '%s' is not supported.", k)
                has_error = True
                continue
            setattr(self, k, v)

        if has_error:
            print("Valid drumset pieces:")
            print(*self.ALL_PIECES, sep=", ")
            raise RuntimeError("Measure contained invalid drumset pieces or options.")

        # These limit note durations to insert rests instead
        self.separators = []



    def replace(self, from_notes: List[float], to_notes: List[float], times: List[int]):
        """Replaces a set of notes from one list to another.
        Useful for introducing slight variations in a measure, such as replacing
        a single hi-hat note with an open hi-hat.

        :param from_notes: List from which to remove the times
        :type from_notes: List[float]
        :param to_notes: List from which to insert the times
        :type to_notes: List[float]
        :param times: Times that should be replaced
        :type times: List[int]
        """
        # TODO: Assert that they are both owned by self?
        for time in times:
            if time in from_notes:
                from_notes.remove(time)
                to_notes.append(time)


    def __iter__(self):
        return iter([deepcopy(self)])


    def get_combined_times(self) -> List[int]:
        """
        Creates a list of all the times in the measure,
        regardless of the instrument. Used in exporting
        logic.

        :returns:
            List[int]: All the times in the measure, for all instruments
        """
        res = []
        for p in self.USED_PIECES:
            if p == "ac":
                continue  # accents don't count

            assert hasattr(self,p)
            res += getattr(self,p)

        res.sort()

        return res


    def __eq__(self, obj):
        if isinstance(obj, Measure):
            for p in self.USED_PIECES:
                assert hasattr(self,p)
                assert hasattr(obj,p)
                if set(getattr(self,p)) != set(getattr(obj,p)):
                    return False

            for p in self.ALL_OPTIONS:
                assert hasattr(self,p)
                assert hasattr(obj,p)
                if getattr(self,p) != getattr(obj,p):
                    return False

        return True


    def pre_export(self):
        """
        Pre-formats the measure content in preparation
        for use by the exporter. In particular, indices
        are shifted to start at 0.
        """
        def pre_export_list(l):

            # Sanitizes the arrays to start at 0 internally
            for i, _ in enumerate(l):
                l[i] -= 1
                l[i] = round(l[i],3)
                assert(l[i]) >= 0

            l.sort()

            # Insert separators for tuplets that have a gap
            # TODO: Support for all tuplet types
            # TODO: Won't work for tuplets of different pieces
            gaps = [0.66]
            for i, v in enumerate(l):
                if i+1 < len(l):
                    for g in gaps:
                        until_next = l[i+1] - v
                        if math.isclose(until_next, g, rel_tol=0.1):
                            self.separators.append(v + g/2.0)

        self.USED_PIECES = [k for k,v in self.ALL_PIECES.items() if v is not None]

        for p in self.USED_PIECES:
            assert hasattr(self,p)
            pre_export_list(getattr(self,p))

        combined_times = self.get_combined_times()
        self.separators.append(0.0)
        for _, t in enumerate(combined_times):
            sep = float(int(t))
            if sep not in self.separators:
                self.separators.append(sep)


    def debug_print(self):
        """
        Prints the contents of the measure to the console, in a visual "ASCII" format.

        :warning Does not yet support subdivisions of more than 16th... Still experimental.
        """
        first_line = "    "
        for i in note_range(1, END, 1):
            first_line += str(i) + "   &   "
        print(first_line)

        for p in self.USED_PIECES:
            vals = getattr(self, p)
            if not vals:
                continue

            res_str = p + "  "
            sym = 'o' if p not in ["hh", "ho", "c1"] else "x" # TODO: Use notedef

            sep = "-"
            if p == "ac":
                sym = ">"
                sep = " "

            step = 0.125

            for _ in note_range(1, vals[0], step):
                res_str += sep

            for i,v in enumerate(vals):
                res_str += sym
                next_v = vals[i+1] if i != len(vals)-1 else END
                until_next = next_v - v

                assert until_next > step or math.isclose(until_next, step), "Debug not yet supported for 32 notes or more"

                for _ in note_range(v,next_v-step, step):
                    res_str += sep

            print(res_str)