"""
pyTableMaker — The module to create, edit and show tables conveniently.
Classes
-------
InvalidSettings
    The settings passed via kwargs of the constructor is invalid.
CustomTable
    With specific styles, a table can be created.
Column
    The class for table columns.
ModernTable
    A type of table formed with double lines.
ClassicTable
    A type of table formed with + - and |.
OnelineTable
    `ModernTable` but with single lines.
"""
import typing

DEFAULT_SETTINGS = {
    "align": "left",
    "linespacing": 0,
    "exp": True,
    "cellwrap": 40,
}


class InvalidSettings(Exception):
    """
    The settings passed via kwargs of the constructor is invalid.
    """

    def __init__(self, message, possible=None, reason=""):
        super().__init__()
        self.message = message
        self.possible = possible
        self.reason = reason

    def __str__(self):
        return self.message


class CustomTable:
    """
    With specific styles, a table can be created.
    Examples
    --------
    ```
    table = CustomTable(
        ["╔", "═", "╗", "╦", "╠", "═", "╣", "╬", "╚", "═", "╝", "╩", "║"]
    )
    table.new_col('Column 2')
    table.new_col('Column 3')
    table.new_col('Column 1').move(0)
    table.insert(1, 2, 3)
    table.insert("just", "random", "stuff")
    print(table[0])  # Column 1
    print(table["Column 2"])  # [2, "random"]
    table.show()
    ```
    Methods
    -------
    copy()
        Make a copy of this table.
    add_col
    add_column
    new_col
    new_column(name: str)
        Add a new column into the table.
    insert(*values)
        Insert a row.
    remove(index: int)
        Remove a row.
    get()
        Returns the built table.
    show()
        print() the return value of get()
    Attributes
    ----------
    style : List[str]
        table styles
    data : Dict[str, List[int]]
        rows of the table
    col_width : List[int]
        maximum required width of columns
    row : int
        number of rows
    settings : dict
        settings for pyTableMaker, by default `DEFAULT_SETTINGS`
    cols : List[Column]
        columns
    """

    style: typing.List[str]
    data: typing.Dict[str, typing.List[str]]
    col_width: typing.List[int]
    row: int = 0  # number of rows
    settings: dict = DEFAULT_SETTINGS.copy()
    cols: list = []

    def __init__(
        self,
        style: list,
        data: dict = {},
        col_width: list = [],
        **kws,
    ):
        """
        Initialize a table creation.
        If you want to replicate tables, pass in both `data` and `col_width`.
        You may also pass in special settings as keyword arguments (**kws).
        Parameters
        ----------
        style : list
            The list of characters for the table style.
        data : dict, optional
            `table.data`, by default None
        col_width : list, optional
            `table.col_width`, by default []
        """
        self.style = style
        self.data = data
        self.col_width = col_width
        self.settings.update(kws)

    def __getitem__(self, items: typing.Union[str, int, slice]):
        if isinstance(items, str):
            return self.data[items]
        if isinstance(items, int):
            for i, col in enumerate(self.data):
                if i == items:
                    return col
            raise IndexError("table index out of range")
        if isinstance(items, slice):
            keys = list(self.data.keys())
            return keys[items]

    def copy(self):
        """
        Make a copy of this table.
        Returns
        -------
        CustomTable
            The copied table.
        """
        return CustomTable(self.style, self.data, self.col_width, **self.settings)

    def new_column(self, name: str):
        """
        Add a new column into the table.
        The column will be placed at the end (aka most right hand side).
        Parameters
        ----------
        name : str
            The name (first row) of the column
        Returns
        -------
        Column
            The new column
        """
        self.cols.append(col := Column(self, name))
        return col

    add_column = add_col = new_col = new_column

    def insert(self, *vals):
        """
        Insert a row.
        Returns
        -------
        Optional[CustomTable]
            Only in exp mode.
        """
        self.row += 1
        for i, col in enumerate(self.data):
            self.data[col].append(str(vals[i]))
            self.col_width[i] = max([len(v) for v in self.data[col]] + [len(col)])
        return self if self.settings["exp"] else self.row - 1

    def inserts(self, *matrix: typing.Iterable[typing.Iterable]):
        """
        Insert multiple rows.
        Returns
        -------
        Optional[CustomTable]
            Only in exp mode.
        """
        for last in (self.insert(*row) for row in matrix):
            pass
        return last

    def remove(self, index: int):
        """
        Remove a row.
        Parameters
        ----------
        index : int
            row number count from 0.
        Returns
        -------
        Union[Any, CustomTable]
            the removed values.
        """
        self.row -= 1

        def proc(i, col):
            self.col_width[i] = max(column := self.data[col])
            return column.pop(index)

        res = [proc(*x) for x in enumerate(self.data)]
        return self if self.settings["exp"] else res

    def get(self, rowcount: int = 0) -> str:
        """
        Returns the built table.
        All the calculations and buildings are done here.
        Parameters
        ----------
        rowcount : int, optional
            the number of rows to be displayed, by default 0
        Returns
        -------
        str
            The built table
        """
        rowcount = rowcount or self.row
        res = self._get_struct(*(s := self.style)[0:4])  # top bar
        res += self._get_l(s[12])  # column names
        # every row and every top bar
        for i, row in enumerate(range(self.row)):
            if i >= rowcount:
                break
            # divider
            res += self._get_struct(*s[4:8])
            # the values
            res += self._get_l(s[12], row)
        # finish the bottom of the table
        res += self._get_struct(*s[8:12])
        return res

    def _add_linespacing(self, s: str) -> str:
        result = ""
        for i in range(self.settings["linespacing"]):
            for col in range(len(self.data)):
                result += (
                    s
                    + " "
                    + " "
                    * (
                        self.col_width[col]
                        if self.col_width[col]
                        <= (size := self.settings["cellwrap"] - 2)
                        else size
                    )
                    + " "
                )
            result += s + "\n"
        return result

    def _get_l(self, s: str, row: int = -1):
        res = self._add_linespacing(s)
        next_val = []  # store next line to be placed if wrapping is needed
        # val: either column name or column[row]
        # max_len: without the spaces around the separators, so -2
        for col, (k, v) in enumerate(self.data.items()):
            if len(val := k if row == -1 else v[row]) > (
                max_len := self.settings["cellwrap"] - 2
            ):  # len of val > max len allowed
                next_val.append(val[max_len:])
                val = val[:max_len]
            else:
                next_val.append("")  # just put a new line in the future
            spaces_needed = (
                width if (width := self.col_width[col]) <= max_len else max_len
            ) - len(val)
            res += f"{s} {val} " + " " * spaces_needed
        res = f"{res[:-1]} {s}\n"
        while any(next_val):  # wrapping required
            vals = []
            for i, val in enumerate(next_val):
                if len(val) > max_len:
                    vals.append(val[max_len:])
                    val = val[:max_len]
                else:
                    vals.append("")
                # max len defined in settings or calc'd width
                # minus len of existing chars
                spaces_needed = (
                    width if (width := self.col_width[i]) <= max_len else max_len
                ) - len(val)
                res += f"{s} {val} " + " " * spaces_needed
            res = f"{res[:-1]} {s}\n"
            if not any(vals):  # ["", "", ..., ""]
                break
            next_val = vals

        return res + self._add_linespacing(s)

    def _get_struct(self, left, mid, right, cross, col=0):
        result = left
        for _ in self.data:
            result += mid * (
                width  # with spaces and separators
                if (width := self.col_width[col] + 2)
                < (cellwrap := self.settings["cellwrap"])
                else cellwrap
            )
            result += cross
            col += 1
        return result[:-1] + right + "\n"

    def show(self, rowcount=0):
        """
        print() the return value of get()
        Parameters
        ----------
        rowcount : int, optional
            the number of rows to be shown, by default 0 (meaning all)
        Returns
        -------
        Optional[CustomTable]
            Only in exp mode.
        """
        print(self.get(rowcount))
        if self.settings["exp"]:
            return self


class Column:
    """
    The class for table columns.
    Attributes
    ----------
    name : str
        Name of the column
    location : int
        The location of the column
    table : CustomTable
        The table the column belongs to
    """

    name: str
    location: int
    table: CustomTable

    def __init__(self, table: CustomTable, name: str):
        """
        Create a new column.
        Parameters
        ----------
        name : str
            The name of the column.
        """
        table.data[name] = []
        table.col_width.append(len(name))
        self.name = name
        self.location = len(table.col_width) - 1
        self.table = table

    def __iter__(self):
        return self.table.data[self.name]

    def rename(self, newname: str):
        """
        Rename the column.
        Parameters
        ----------
        newname : str
            The new name.
        Returns
        -------
        Union[str, Column]
            The old name.
        """
        oldname = self.name
        newdata = {}
        for k, v in self.table.data.items():
            newdata[newname if k == oldname else k] = v
        self.table.data = newdata
        return self if self.table.settings["exp"] else oldname

    def delete(self):
        """
        Delete the column.
        Returns
        -------
        Union[Tuple[list, int], Column]
            The erased values and col_width, Column only in exp mode.
        Examples
        --------
        ```
        vals, col_width = col.delete()
        for row in vals:
            print(row)
        print("Column width: " + col_width)
        ```
        """
        vals = self.table.data.pop(self.name)
        col_width = self.table.col_width.pop(self.location)
        return self if self.table.settings["exp"] else vals, col_width

    def move(self, index: int):
        """
        Move the column.
        Parameters
        ----------
        index : int
            Move the column to this index.
        Returns
        -------
        Union[int, Column]
            The old index, Column only in exp mode.
        """
        newdata = {}
        i = 0  # new index

        for k, v in self.table.data.items():  # n: old index
            if i == index:
                newdata[self.name] = self.table.data[self.name]
                i += 1
            if k == self.name:
                continue
            newdata[k] = v
            i += 1

        # move col_width too
        width = self.table.col_width.pop(self.location)
        self.table.col_width.insert(index, width)

        oldindex = self.location
        self.location = index

        return self if self.table.settings["exp"] else oldindex


class ModernTable(CustomTable):
    """
    A type of table formed with double lines.
    Doesn't work on ASCII.
    Subclasses
    ----------
    CustomTable
    Examples
    --------
    ```
    table = ModernTable()
    table.new_col('Column 2')
    table.new_col('Column 3')
    table.new_col('Column 1').move(0)
    table.inserts((1, 2, 3), ("just", "random", "stuff"))
    print(table[0])  # Column 1
    print(table["Column 2"])  # [2, "random"]
    table.show()
    ```
    Methods
    -------
    copy()
        Make a copy of this table.
    add_col
    add_column
    new_col
    new_column(name: str)
        Add a new column into the table.
    insert(*values)
        Insert a row.
    remove(index: int)
        Remove a row.
    get()
        Returns the built table.
    show()
        print() the return value of get()
    Attributes
    ----------
    style : List[str]
        table styles
    data : Dict[str, List[int]]
        rows of the table
    col_width : List[int]
        maximum required width of columns
    row : int
        number of rows
    settings : dict
        settings for pyTableMaker, by default `DEFAULT_SETTINGS`
    cols : List[Column]
        columns
    """

    def __init__(self, data: dict = {}, col_width: list = [], **kwargs):
        """
        Create a modern table.
        A type of table formed with double lines.
        Doesn't work on ASCII.
        Parameters
        ----------
        data : dict, optional
            table.data, by default {}
        col_width : list, optional
            table.col_width, by default []
        """
        super().__init__(
            ["╔", "═", "╗", "╦", "╠", "═", "╣", "╬", "╚", "═", "╝", "╩", "║"],
            data,
            col_width,
            **kwargs,
        )


class ClassicTable(CustomTable):
    """
    A type of table formed with + - and |.
    Subclasses
    ----------
    CustomTable
    Examples
    --------
    ```
    table = ClassicTable()
    table.new_col('Column 2')
    table.new_col('Column 3')
    table.new_col('Column 1').move(0)
    table.inserts((1, 2, 3), ("just", "random", "stuff"))
    print(table[0])  # Column 1
    print(table["Column 2"])  # [2, "random"]
    table.show()
    ```
    Methods
    -------
    copy()
        Make a copy of this table.
    add_col
    add_column
    new_col
    new_column(name: str)
        Add a new column into the table.
    insert(*values)
        Insert a row.
    remove(index: int)
        Remove a row.
    get()
        Returns the built table.
    show()
        print() the return value of get()
    Attributes
    ----------
    style : List[str]
        table styles
    data : Dict[str, List[int]]
        rows of the table
    col_width : List[int]
        maximum required width of columns
    row : int
        number of rows
    settings : dict
        settings for pyTableMaker, by default `DEFAULT_SETTINGS`
    cols : List[Column]
        columns
    """

    def __init__(self, data: dict = {}, col_width: list = [], **kws):
        """
        Create a classic table.
        A type of table formed with + - and |.
        Parameters
        ----------
        data : dict, optional
            table.data, by default {}
        col_width : list, optional
            table.col_width, by default []
        """
        super().__init__(
            ["+", "-", "+", "+", "+", "-", "+", "+", "+", "-", "+", "+", "|"],
            data,
            col_width,
            **kws,
        )


class OnelineTable(CustomTable):
    """
    `ModernTable` but with single lines.
    Doesn't work on ASCII.
    Subclasses
    ----------
    CustomTable
    Examples
    --------
    ```
    table = OnelineTable()
    table.new_col('Column 2')
    table.new_col('Column 3')
    table.new_col('Column 1').move(0)
    table.inserts((1, 2, 3), ("just", "random", "stuff"))
    print(table[0])  # Column 1
    print(table["Column 2"])  # [2, "random"]
    table.show()
    ```
    Methods
    -------
    copy()
        Make a copy of this table.
    add_col
    add_column
    new_col
    new_column(name: str)
        Add a new column into the table.
    insert(*values)
        Insert a row.
    remove(index: int)
        Remove a row.
    get()
        Returns the built table.
    show()
        print() the return value of get()
    Attributes
    ----------
    style : List[str]
        table styles
    data : Dict[str, List[int]]
        rows of the table
    col_width : List[int]
        maximum required width of columns
    row : int
        number of rows
    settings : dict
        settings for pyTableMaker, by default `DEFAULT_SETTINGS`
    cols : List[Column]
        columns
    """

    def __init__(self, data: dict = {}, col_width: list = [], **kws):
        """
        Create a one line table.
        It's basically `ModernTable` but with single lines.
        Doesn't work on ASCII.
        Parameters
        ----------
        data : dict, optional
            table.data, by default {}
        col_width : list, optional
            table.col_width, by default []
        """
        super().__init__(
            ["┌", "─", "┐", "┬", "├", "─", "┤", "┼", "└", "─", "┘", "┴", "│"],
            data,
            col_width,
            **kws,
        )
