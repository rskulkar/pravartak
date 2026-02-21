"""
Unit Tests – City Library Management System
============================================
Run with:  python -m pytest test_library_system.py -v

Each test class isolates state via setUp() / reset_library().
"""

import unittest
import library_system as lib


# ---------------------------------------------------------------------------
# Helper: fresh state before each test
# ---------------------------------------------------------------------------

def _setup():
    """Reset stores and add a minimal dataset."""
    lib.reset_library()

    lib.add_book("B001", "The Great Gatsby",        "F. Scott Fitzgerald", "Fiction")
    lib.add_book("B002", "1984",                    "George Orwell",       "Dystopian")
    lib.add_book("B003", "A Brief History of Time", "Stephen Hawking",     "Science")
    lib.add_book("B004", "Dune",                    "Frank Herbert",       "Science Fiction")
    lib.add_book("B005", "The Hobbit",              "J.R.R. Tolkien",      "Fantasy")

    lib.add_member("M001", "Alice Johnson", 28, "alice@example.com")
    lib.add_member("M002", "Bob Smith",     35, "bob@example.com")


# ===========================================================================
# 1. Book Management
# ===========================================================================

class TestAddBook(unittest.TestCase):

    def setUp(self):
        _setup()

    def test_add_book_success(self):
        """A new book is added and stored correctly."""
        book = lib.add_book("B099", "New Book", "New Author", "Fiction")
        self.assertEqual(book["book_id"], "B099")
        self.assertEqual(book["availability"], "Available")
        self.assertIn("B099", lib.BOOKS)

    def test_add_book_duplicate_id_raises(self):
        """Duplicate book_id must raise ValueError."""
        with self.assertRaises(ValueError):
            lib.add_book("B001", "Duplicate", "Author", "Genre")

    def test_add_book_strips_whitespace(self):
        """Title and author whitespace should be stripped."""
        book = lib.add_book("B098", "  Spaces  ", "  Auth  ", "Fiction")
        self.assertEqual(book["title"], "Spaces")
        self.assertEqual(book["author"], "Auth")

    def test_get_book_success(self):
        """get_book returns correct record."""
        book = lib.get_book("B001")
        self.assertEqual(book["title"], "The Great Gatsby")

    def test_get_book_not_found(self):
        """get_book raises KeyError for unknown ID."""
        with self.assertRaises(KeyError):
            lib.get_book("Z999")

    def test_update_availability_valid(self):
        """update_book_availability changes status correctly."""
        lib.update_book_availability("B001", "Issued")
        self.assertEqual(lib.BOOKS["B001"]["availability"], "Issued")
        lib.update_book_availability("B001", "Available")
        self.assertEqual(lib.BOOKS["B001"]["availability"], "Available")

    def test_update_availability_invalid_status(self):
        """Invalid status raises ValueError."""
        with self.assertRaises(ValueError):
            lib.update_book_availability("B001", "Lost")

    def test_update_availability_unknown_book(self):
        """Unknown book raises KeyError."""
        with self.assertRaises(KeyError):
            lib.update_book_availability("Z999", "Available")


# ===========================================================================
# 2. Member Management
# ===========================================================================

class TestAddMember(unittest.TestCase):

    def setUp(self):
        _setup()

    def test_add_member_success(self):
        """A new member is added and stored correctly."""
        member = lib.add_member("M099", "Test User", 25, "test@example.com")
        self.assertEqual(member["member_id"], "M099")
        self.assertEqual(member["borrowed_books"], [])
        self.assertIn("M099", lib.MEMBERS)

    def test_add_member_duplicate_id_raises(self):
        """Duplicate member_id must raise ValueError."""
        with self.assertRaises(ValueError):
            lib.add_member("M001", "Duplicate", 30, "dup@example.com")

    def test_add_member_age_too_low(self):
        """Age below 5 must raise ValueError."""
        with self.assertRaises(ValueError):
            lib.add_member("M099", "Tiny Tim", 3, "tiny@example.com")

    def test_add_member_minimum_age(self):
        """Age == 5 should be accepted."""
        member = lib.add_member("M100", "Young Reader", 5, "young@example.com")
        self.assertEqual(member["age"], 5)

    def test_get_member_success(self):
        """get_member returns correct record."""
        member = lib.get_member("M001")
        self.assertEqual(member["name"], "Alice Johnson")

    def test_get_member_not_found(self):
        """get_member raises KeyError for unknown ID."""
        with self.assertRaises(KeyError):
            lib.get_member("Z999")


# ===========================================================================
# 3. Issue & Return
# ===========================================================================

class TestIssueReturn(unittest.TestCase):

    def setUp(self):
        _setup()

    def test_issue_book_success(self):
        """Issuing an available book updates book & member state and logs."""
        entry = lib.issue_book("M001", "B001")
        self.assertEqual(entry["action"], "ISSUE")
        self.assertEqual(lib.BOOKS["B001"]["availability"], "Issued")
        self.assertIn("B001", lib.MEMBERS["M001"]["borrowed_books"])
        self.assertEqual(len(lib.BORROW_LOG), 1)

    def test_issue_already_issued_book_raises(self):
        """Issuing an already-issued book must raise ValueError."""
        lib.issue_book("M001", "B001")
        with self.assertRaises(ValueError):
            lib.issue_book("M002", "B001")   # B001 is now Issued

    def test_issue_same_book_twice_by_same_member_raises(self):
        """A member cannot borrow the same book twice."""
        lib.issue_book("M001", "B001")
        with self.assertRaises(ValueError):
            lib.issue_book("M001", "B001")

    def test_issue_unknown_member_raises(self):
        """Issuing to unknown member raises KeyError."""
        with self.assertRaises(KeyError):
            lib.issue_book("Z999", "B001")

    def test_issue_unknown_book_raises(self):
        """Issuing unknown book raises KeyError."""
        with self.assertRaises(KeyError):
            lib.issue_book("M001", "Z999")

    def test_return_book_success(self):
        """Returning a borrowed book restores availability and logs correctly."""
        lib.issue_book("M001", "B001")
        entry = lib.return_book("M001", "B001")
        self.assertEqual(entry["action"], "RETURN")
        self.assertEqual(lib.BOOKS["B001"]["availability"], "Available")
        self.assertNotIn("B001", lib.MEMBERS["M001"]["borrowed_books"])
        self.assertEqual(len(lib.BORROW_LOG), 2)   # ISSUE + RETURN

    def test_return_book_not_borrowed_raises(self):
        """Returning a book the member did not borrow raises ValueError."""
        with self.assertRaises(ValueError):
            lib.return_book("M001", "B001")

    def test_return_unknown_member_raises(self):
        """Returning for unknown member raises KeyError."""
        with self.assertRaises(KeyError):
            lib.return_book("Z999", "B001")

    def test_return_unknown_book_raises(self):
        """Returning unknown book raises KeyError."""
        with self.assertRaises(KeyError):
            lib.return_book("M001", "Z999")

    def test_reissue_after_return(self):
        """A returned book can be re-issued to another member."""
        lib.issue_book("M001", "B001")
        lib.return_book("M001", "B001")
        entry = lib.issue_book("M002", "B001")
        self.assertEqual(entry["action"], "ISSUE")
        self.assertEqual(lib.BOOKS["B001"]["availability"], "Issued")


# ===========================================================================
# 4. Reports & Queries
# ===========================================================================

class TestReports(unittest.TestCase):

    def setUp(self):
        _setup()
        # Issue a couple of books for report tests
        lib.issue_book("M001", "B001")   # Fiction
        lib.issue_book("M002", "B002")   # Dystopian

    def test_show_available_books_by_genre_returns_only_available(self):
        """Only available books of the requested genre are returned."""
        # B001 (Fiction) is now Issued; only available Fiction books remain
        available_fiction = lib.show_available_books_by_genre("Fiction")
        ids = [b["book_id"] for b in available_fiction]
        self.assertNotIn("B001", ids)
        # All returned books must be Fiction and Available
        for b in available_fiction:
            self.assertEqual(b["genre"], "Fiction")
            self.assertEqual(b["availability"], "Available")

    def test_show_available_books_by_genre_case_insensitive(self):
        """Genre search should be case-insensitive."""
        result_lower = lib.show_available_books_by_genre("science")
        result_upper = lib.show_available_books_by_genre("Science")
        self.assertEqual(
            [b["book_id"] for b in result_lower],
            [b["book_id"] for b in result_upper],
        )

    def test_show_available_books_by_genre_no_match(self):
        """Returns empty list for an unknown genre."""
        result = lib.show_available_books_by_genre("Horror")
        self.assertEqual(result, [])

    def test_list_members_with_borrowed_books(self):
        """Only members who currently have books appear in the list."""
        borrowers = lib.list_members_with_borrowed_books()
        borrower_ids = [m["member_id"] for m in borrowers]
        self.assertIn("M001", borrower_ids)
        self.assertIn("M002", borrower_ids)

    def test_list_members_with_borrowed_books_excludes_non_borrowers(self):
        """Members with no borrowed books are excluded."""
        borrowers = lib.list_members_with_borrowed_books()
        borrower_ids = [m["member_id"] for m in borrowers]
        # M002 returned nothing; in setUp only M001 & M002 borrowed
        # No extra members should appear
        self.assertNotIn("M003", borrower_ids)   # M003 doesn't even exist yet

    def test_search_books_by_title(self):
        """Substring title search works (case-insensitive)."""
        results = lib.search_books("gatsby")
        self.assertTrue(any(b["book_id"] == "B001" for b in results))

    def test_search_books_by_author(self):
        """Substring author search works."""
        results = lib.search_books("orwell")
        self.assertTrue(any(b["book_id"] == "B002" for b in results))

    def test_search_books_no_results(self):
        """Non-matching query returns empty list."""
        results = lib.search_books("xyzabc")
        self.assertEqual(results, [])

    def test_search_books_returns_all_statuses(self):
        """Search returns books regardless of availability."""
        results = lib.search_books("gatsby")   # B001 is Issued
        statuses = {b["availability"] for b in results}
        # B001 is currently Issued but should still appear
        self.assertIn("B001", [b["book_id"] for b in results])

    def test_most_popular_genre(self):
        """Fiction (1 issue) and Dystopian (1 issue) → tied; result is valid."""
        info = lib.most_popular_genre()
        self.assertIn(info["genre"], ("Fiction", "Dystopian"))
        self.assertEqual(info["count"], 1)
        self.assertIn("Fiction", info["all_genre_counts"])
        self.assertIn("Dystopian", info["all_genre_counts"])

    def test_most_popular_genre_no_transactions(self):
        """With no issues, most_popular_genre returns genre=None."""
        lib.reset_library()
        info = lib.most_popular_genre()
        self.assertIsNone(info["genre"])
        self.assertEqual(info["count"], 0)

    def test_most_popular_genre_after_multiple_issues(self):
        """Genre with most issues wins."""
        lib.reset_library()
        lib.add_book("X1", "Book1", "Author", "Science")
        lib.add_book("X2", "Book2", "Author", "Science")
        lib.add_book("X3", "Book3", "Author", "Fantasy")
        lib.add_member("P1", "Person1", 20, "p1@test.com")
        lib.add_member("P2", "Person2", 20, "p2@test.com")
        lib.add_member("P3", "Person3", 20, "p3@test.com")
        lib.issue_book("P1", "X1")   # Science
        lib.issue_book("P2", "X2")   # Science
        lib.issue_book("P3", "X3")   # Fantasy
        info = lib.most_popular_genre()
        self.assertEqual(info["genre"], "Science")
        self.assertEqual(info["count"], 2)

    def test_most_popular_genre_counts_returned_books(self):
        """Returned books still count toward genre popularity."""
        lib.reset_library()
        lib.add_book("X1", "Book1", "Author", "Science")
        lib.add_member("P1", "Person", 20, "p@test.com")
        lib.issue_book("P1", "X1")
        lib.return_book("P1", "X1")
        info = lib.most_popular_genre()
        self.assertEqual(info["genre"], "Science")   # ISSUE log entry remains


# ===========================================================================
# 5. Library Summary
# ===========================================================================

class TestLibrarySummary(unittest.TestCase):

    def setUp(self):
        _setup()

    def test_summary_totals(self):
        """Summary reflects correct totals."""
        summary = lib.library_summary()
        self.assertEqual(summary["total_books"],   5)
        self.assertEqual(summary["available_books"], 5)
        self.assertEqual(summary["issued_books"],    0)
        self.assertEqual(summary["total_members"],   2)
        self.assertEqual(summary["members_borrowing"], 0)
        self.assertEqual(summary["total_transactions"], 0)

    def test_summary_after_transactions(self):
        """Summary updates after issues and returns."""
        lib.issue_book("M001", "B001")
        lib.issue_book("M002", "B002")
        lib.return_book("M002", "B002")

        summary = lib.library_summary()
        self.assertEqual(summary["issued_books"],     1)   # only B001 still issued
        self.assertEqual(summary["available_books"],  4)
        self.assertEqual(summary["members_borrowing"], 1)  # only M001
        self.assertEqual(summary["total_transactions"], 3) # ISSUE, ISSUE, RETURN

    def test_summary_genre_breakdown(self):
        """Genre breakdown contains every added genre."""
        summary = lib.library_summary()
        self.assertIn("Fiction",         summary["genre_breakdown"])
        self.assertIn("Dystopian",       summary["genre_breakdown"])
        self.assertIn("Science",         summary["genre_breakdown"])
        self.assertIn("Science Fiction", summary["genre_breakdown"])
        self.assertIn("Fantasy",         summary["genre_breakdown"])


# ===========================================================================
# 6. Reset
# ===========================================================================

class TestReset(unittest.TestCase):

    def test_reset_clears_all_stores(self):
        """reset_library empties all three stores."""
        _setup()
        lib.issue_book("M001", "B001")
        lib.reset_library()
        self.assertEqual(len(lib.BOOKS),      0)
        self.assertEqual(len(lib.MEMBERS),    0)
        self.assertEqual(len(lib.BORROW_LOG), 0)


# ===========================================================================
# 7. Seed data loader
# ===========================================================================

class TestSeedData(unittest.TestCase):

    def setUp(self):
        lib.load_seed_data()

    def test_seed_books_loaded(self):
        """Seed data should contain at least 15 books."""
        self.assertGreaterEqual(len(lib.BOOKS), 15)

    def test_seed_members_loaded(self):
        """Seed data should contain at least 5 members."""
        self.assertGreaterEqual(len(lib.MEMBERS), 5)

    def test_seed_borrow_log_not_empty(self):
        """Seed transactions should populate the borrow log."""
        self.assertGreater(len(lib.BORROW_LOG), 0)

    def test_seed_all_log_books_exist(self):
        """Every book_id referenced in BORROW_LOG must be in BOOKS."""
        for entry in lib.BORROW_LOG:
            self.assertIn(entry["book_id"], lib.BOOKS)

    def test_seed_all_log_members_exist(self):
        """Every member_id referenced in BORROW_LOG must be in MEMBERS."""
        for entry in lib.BORROW_LOG:
            self.assertIn(entry["member_id"], lib.MEMBERS)

    def test_seed_issued_books_have_issued_status(self):
        """Books currently in a member's borrowed list must be Issued."""
        for m in lib.MEMBERS.values():
            for bid in m["borrowed_books"]:
                self.assertEqual(
                    lib.BOOKS[bid]["availability"], "Issued",
                    msg=f"Book {bid} in member {m['member_id']} should be Issued."
                )


# ===========================================================================
# Entry-point
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
