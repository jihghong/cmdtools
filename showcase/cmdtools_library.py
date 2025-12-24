from cmdtools import command, execute, register_relation


class Chapter:
    def __init__(self, book, index):
        self.book = book
        self.index = index
        self.cid = f"{book.isbn}-C{index}"

    @command
    def read(self, page: int = 1):
        print(f"read {self.book.isbn}.[{self.index}] page={page}")

    @command
    def quote(self, words: int):
        print(f"quote {self.book.isbn}.[{self.index}] words={words}")


class Book:
    def __init__(self, isbn, title, n):
        self.isbn = isbn
        self.title = title
        self.chapters = [Chapter(self, i) for i in range(n)]

    @command
    def describe(self):
        print(f"describe {self.isbn} {self.title!r}")

    @command
    def rename(self, title: str):
        self.title = title
        print(f"rename {self.isbn} {self.title!r}")


books = [
    Book("B100", "Alpha", 2),
    Book("B200", "Beta", 1),
]

register_relation(
    main_class=Book,
    sub_class=Chapter,
    subattr="chapters",
    main_id_attr="isbn",
    sub_id_attr="cid",
    all=books,
)


book1 = books[0]
chapter0 = book1.chapters[0]

execute("describe")
execute("describe all")
execute("describe for B200")
execute("describe", self=book1)
execute("rename title=Gamma", self=books[1])

execute("read", self=book1)
execute("read page=3 for self.[1]", self=book1)
execute("read for all", self=book1)
execute("read for all")
execute("read for B200")
execute("read for B200.[0]")
execute(f"read for {chapter0.cid}")
execute("read", self=chapter0)
execute("quote 12 for B100.[0]")
