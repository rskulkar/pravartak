"""
City Library Management System
================================
All data and logic live in this single module (no sub-modules).
Data is held in three in-memory stores:
  - BOOKS      : dict keyed by book_id
  - MEMBERS    : dict keyed by member_id
  - BORROW_LOG : list of transaction records
"""

from datetime import datetime
from collections import Counter

# ---------------------------------------------------------------------------
# In-memory data stores
# ---------------------------------------------------------------------------

BOOKS: dict = {}        # {book_id: {title, author, genre, availability}}
MEMBERS: dict = {}      # {member_id: {name, age, contact, borrowed_books}}
BORROW_LOG: list = []   # [{book_id, member_id, action, timestamp}]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return current timestamp as a formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Book management
# ---------------------------------------------------------------------------

def add_book(book_id: str, title: str, author: str, genre: str) -> dict:
    """
    Add a new book to the library.

    Parameters
    ----------
    book_id : unique identifier (e.g. 'B001')
    title   : book title
    author  : author name
    genre   : genre label (e.g. 'Fiction', 'Science')

    Returns
    -------
    The newly created book record, or raises ValueError if ID already exists.
    """
    if book_id in BOOKS:
        raise ValueError(f"Book ID '{book_id}' already exists.")

    book = {
        "book_id":      book_id,
        "title":        title.strip(),
        "author":       author.strip(),
        "genre":        genre.strip(),
        "availability": "Available",
    }
    BOOKS[book_id] = book
    return book


def update_book_availability(book_id: str, status: str) -> dict:
    """
    Manually set the availability of a book.

    Parameters
    ----------
    book_id : target book
    status  : 'Available' or 'Issued'
    """
    if book_id not in BOOKS:
        raise KeyError(f"Book ID '{book_id}' not found.")
    if status not in ("Available", "Issued"):
        raise ValueError("Status must be 'Available' or 'Issued'.")
    BOOKS[book_id]["availability"] = status
    return BOOKS[book_id]


def get_book(book_id: str) -> dict:
    """Return book record or raise KeyError."""
    if book_id not in BOOKS:
        raise KeyError(f"Book ID '{book_id}' not found.")
    return BOOKS[book_id]


# ---------------------------------------------------------------------------
# Member management
# ---------------------------------------------------------------------------

def add_member(member_id: str, name: str, age: int, contact: str) -> dict:
    """
    Register a new library member.

    Parameters
    ----------
    member_id : unique identifier (e.g. 'M001')
    name      : full name
    age       : age in years (must be ≥ 5)
    contact   : email or phone number
    """
    if member_id in MEMBERS:
        raise ValueError(f"Member ID '{member_id}' already exists.")
    if age < 5:
        raise ValueError("Member age must be at least 5.")

    member = {
        "member_id":      member_id,
        "name":           name.strip(),
        "age":            age,
        "contact":        contact.strip(),
        "borrowed_books": [],   # list of book_ids currently borrowed
    }
    MEMBERS[member_id] = member
    return member


def get_member(member_id: str) -> dict:
    """Return member record or raise KeyError."""
    if member_id not in MEMBERS:
        raise KeyError(f"Member ID '{member_id}' not found.")
    return MEMBERS[member_id]


# ---------------------------------------------------------------------------
# Borrow & Return
# ---------------------------------------------------------------------------

def issue_book(member_id: str, book_id: str) -> dict:
    """
    Issue a book to a member.

    Business rules
    --------------
    - Book and member must exist.
    - Book must be 'Available'.
    - A member cannot borrow the same book twice simultaneously.

    Returns
    -------
    The borrow-log entry that was recorded.
    """
    member = get_member(member_id)
    book   = get_book(book_id)

    if book["availability"] != "Available":
        raise ValueError(
            f"Book '{book['title']}' is already issued and not available."
        )
    if book_id in member["borrowed_books"]:
        raise ValueError(
            f"Member '{member['name']}' already has book '{book['title']}'."
        )

    # Update state
    BOOKS[book_id]["availability"] = "Issued"
    MEMBERS[member_id]["borrowed_books"].append(book_id)

    entry = {
        "action":    "ISSUE",
        "member_id": member_id,
        "book_id":   book_id,
        "timestamp": _now(),
    }
    BORROW_LOG.append(entry)
    return entry


def return_book(member_id: str, book_id: str) -> dict:
    """
    Return a book previously borrowed by a member.

    Returns
    -------
    The borrow-log entry that was recorded.
    """
    member = get_member(member_id)
    book   = get_book(book_id)

    if book_id not in member["borrowed_books"]:
        raise ValueError(
            f"Member '{member['name']}' does not have book '{book['title']}'."
        )

    # Update state
    BOOKS[book_id]["availability"] = "Available"
    MEMBERS[member_id]["borrowed_books"].remove(book_id)

    entry = {
        "action":    "RETURN",
        "member_id": member_id,
        "book_id":   book_id,
        "timestamp": _now(),
    }
    BORROW_LOG.append(entry)
    return entry


# ---------------------------------------------------------------------------
# Reports & Queries
# ---------------------------------------------------------------------------

def show_available_books_by_genre(genre: str) -> list:
    """
    Return a list of available books in the given genre (case-insensitive).
    """
    genre_lower = genre.strip().lower()
    return [
        b for b in BOOKS.values()
        if b["genre"].lower() == genre_lower and b["availability"] == "Available"
    ]


def list_members_with_borrowed_books() -> list:
    """
    Return members who currently have at least one borrowed book.
    Each entry includes member details plus titles of borrowed books.
    """
    result = []
    for m in MEMBERS.values():
        if m["borrowed_books"]:
            borrowed_titles = [
                BOOKS[bid]["title"]
                for bid in m["borrowed_books"]
                if bid in BOOKS
            ]
            result.append({
                "member_id":      m["member_id"],
                "name":           m["name"],
                "contact":        m["contact"],
                "borrowed_books": borrowed_titles,
            })
    return result


def search_books(query: str) -> list:
    """
    Search for books by title or author (case-insensitive substring match).

    Parameters
    ----------
    query : search string

    Returns
    -------
    List of matching book records (regardless of availability).
    """
    q = query.strip().lower()
    return [
        b for b in BOOKS.values()
        if q in b["title"].lower() or q in b["author"].lower()
    ]


def most_popular_genre() -> dict:
    """
    Determine the most popular genre based on all ISSUE transactions in the
    borrow log (not just currently issued books).

    Returns
    -------
    dict with keys: genre, count, all_genre_counts
    """
    issue_entries = [e for e in BORROW_LOG if e["action"] == "ISSUE"]
    if not issue_entries:
        return {"genre": None, "count": 0, "all_genre_counts": {}}

    genres = [
        BOOKS[e["book_id"]]["genre"]
        for e in issue_entries
        if e["book_id"] in BOOKS
    ]
    counter = Counter(genres)
    top_genre, top_count = counter.most_common(1)[0]
    return {
        "genre":            top_genre,
        "count":            top_count,
        "all_genre_counts": dict(counter),
    }


def library_summary() -> dict:
    """
    Return a high-level overview of the library:
      - total books, available vs issued
      - genre breakdown of the full catalogue
      - total members, members currently borrowing
      - total transactions (issues + returns)
      - most popular genre
    """
    total_books     = len(BOOKS)
    available       = sum(1 for b in BOOKS.values() if b["availability"] == "Available")
    issued          = total_books - available

    genre_breakdown = {}
    for b in BOOKS.values():
        genre_breakdown[b["genre"]] = genre_breakdown.get(b["genre"], 0) + 1

    total_members       = len(MEMBERS)
    members_borrowing   = sum(1 for m in MEMBERS.values() if m["borrowed_books"])

    total_transactions  = len(BORROW_LOG)
    popular             = most_popular_genre()

    return {
        "total_books":          total_books,
        "available_books":      available,
        "issued_books":         issued,
        "genre_breakdown":      genre_breakdown,
        "total_members":        total_members,
        "members_borrowing":    members_borrowing,
        "total_transactions":   total_transactions,
        "most_popular_genre":   popular["genre"],
        "popular_genre_count":  popular["count"],
    }


# ---------------------------------------------------------------------------
# Display helpers (formatted console output)
# ---------------------------------------------------------------------------

def _hr(char: str = "-", width: int = 60) -> str:
    return char * width


def display_books(books: list, title: str = "Books") -> None:
    """Pretty-print a list of book records."""
    print(f"\n{'='*60}")
    print(f"  {title}  ({len(books)} record(s))")
    print(_hr())
    if not books:
        print("  No records found.")
    for b in books:
        avail_tag = "[AVAILABLE]" if b["availability"] == "Available" else "[ISSUED]   "
        print(
            f"  {avail_tag} {b['book_id']} | {b['title']}"
            f" by {b['author']} | Genre: {b['genre']}"
        )
    print(_hr())


def display_members(members: list, title: str = "Members") -> None:
    """Pretty-print a list of member records."""
    print(f"\n{'='*60}")
    print(f"  {title}  ({len(members)} record(s))")
    print(_hr())
    if not members:
        print("  No records found.")
    for m in members:
        books_str = ", ".join(m.get("borrowed_books", [])) or "None"
        print(
            f"  {m['member_id']} | {m['name']} | Age: {m.get('age', 'N/A')}"
            f" | Contact: {m['contact']} | Borrowed: {books_str}"
        )
    print(_hr())


def display_summary(summary: dict) -> None:
    """Pretty-print the library summary."""
    print(f"\n{'='*60}")
    print("  LIBRARY SUMMARY")
    print(_hr())
    print(f"  Books          : {summary['total_books']} total")
    print(f"    Available    : {summary['available_books']}")
    print(f"    Issued       : {summary['issued_books']}")
    print(f"  Genre breakdown:")
    for genre, cnt in summary["genre_breakdown"].items():
        print(f"    {genre:<20} : {cnt}")
    print(f"  Members        : {summary['total_members']} total")
    print(f"    Borrowing    : {summary['members_borrowing']}")
    print(f"  Transactions   : {summary['total_transactions']}")
    print(f"  Popular genre  : {summary['most_popular_genre']} "
          f"({summary['popular_genre_count']} issue(s))")
    print(_hr())


def display_borrow_log(log: list = None) -> None:
    """Pretty-print the borrow log (or a subset)."""
    if log is None:
        log = BORROW_LOG
    print(f"\n{'='*60}")
    print(f"  BORROW LOG  ({len(log)} entry(ies))")
    print(_hr())
    if not log:
        print("  No transactions recorded.")
    for entry in log:
        book_title = BOOKS.get(entry["book_id"], {}).get("title", entry["book_id"])
        member_name = MEMBERS.get(entry["member_id"], {}).get("name", entry["member_id"])
        print(
            f"  [{entry['timestamp']}] {entry['action']:<6}"
            f" | {member_name:<20} → {book_title}"
        )
    print(_hr())


# ---------------------------------------------------------------------------
# Data reset (useful for testing)
# ---------------------------------------------------------------------------

def reset_library() -> None:
    """Clear all in-memory data stores. Useful for testing."""
    BOOKS.clear()
    MEMBERS.clear()
    BORROW_LOG.clear()


# ---------------------------------------------------------------------------
# Seed data loader (demo / notebook activation)
# ---------------------------------------------------------------------------

def load_seed_data() -> None:
    """
    Populate the library with a realistic seed dataset so the notebook
    can demonstrate all features without manual entry.
    """
    reset_library()

    # -- Books ---------------------------------------------------------------
    seed_books = [
        ("B001", "The Great Gatsby",          "F. Scott Fitzgerald", "Fiction"),
        ("B002", "To Kill a Mockingbird",     "Harper Lee",          "Fiction"),
        ("B003", "1984",                       "George Orwell",       "Dystopian"),
        ("B004", "A Brief History of Time",   "Stephen Hawking",     "Science"),
        ("B005", "Sapiens",                    "Yuval Noah Harari",   "History"),
        ("B006", "The Selfish Gene",           "Richard Dawkins",     "Science"),
        ("B007", "Dune",                       "Frank Herbert",       "Science Fiction"),
        ("B008", "Foundation",                 "Isaac Asimov",        "Science Fiction"),
        ("B009", "The Hobbit",                 "J.R.R. Tolkien",      "Fantasy"),
        ("B010", "Harry Potter & the Philosopher's Stone",
                                               "J.K. Rowling",        "Fantasy"),
        ("B011", "The Alchemist",              "Paulo Coelho",        "Fiction"),
        ("B012", "Brave New World",            "Aldous Huxley",       "Dystopian"),
        ("B013", "The Da Vinci Code",          "Dan Brown",           "Mystery"),
        ("B014", "Gone Girl",                  "Gillian Flynn",       "Mystery"),
        ("B015", "Thinking, Fast and Slow",   "Daniel Kahneman",     "Psychology"),
    ]
    for args in seed_books:
        add_book(*args)

    # -- Members -------------------------------------------------------------
    seed_members = [
        ("M001", "Alice Johnson",  28, "alice@example.com"),
        ("M002", "Bob Smith",      35, "bob@example.com"),
        ("M003", "Carol White",    22, "carol@example.com"),
        ("M004", "David Brown",    45, "david@example.com"),
        ("M005", "Eva Martinez",   31, "eva@example.com"),
    ]
    for args in seed_members:
        add_member(*args)

    # -- Transactions --------------------------------------------------------
    # Alice borrows two books
    issue_book("M001", "B001")
    issue_book("M001", "B009")
    # Bob borrows a Science book then returns it (to show full log)
    issue_book("M002", "B004")
    return_book("M002", "B004")
    # Bob borrows another book
    issue_book("M002", "B007")
    # Carol borrows a Dystopian book
    issue_book("M003", "B003")
    # David borrows two books
    issue_book("M004", "B005")
    issue_book("M004", "B013")
    # Eva borrows a Psychology book
    issue_book("M005", "B015")
