import os
import json
import uuid
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
BOOKS_FILE = os.path.join(DATA_DIR, "swatch_books.json")


def _ensure_storage_exists():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(BOOKS_FILE):
        with open(BOOKS_FILE, "w", encoding="utf-8") as f:
            json.dump({"books": {}}, f, indent=2)


def load_all_books() -> dict:
    _ensure_storage_exists()
    try:
        with open(BOOKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("books", {})
    except Exception:
        return {}


def save_all_books(books: dict):
    _ensure_storage_exists()
    with open(BOOKS_FILE, "w", encoding="utf-8") as f:
        json.dump({"books": books}, f, indent=2)


def create_book(name: str, items_per_page: int = 24, notes: str = "") -> dict:
    books = load_all_books()
    book_id = f"book_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()
    
    new_book = {
        "id": book_id,
        "name": name.strip(),
        "items_per_page": int(items_per_page),
        "notes": notes.strip(),
        "created_at": now,
        "updated_at": now,
        "printed_item_ids": []
    }
    books[book_id] = new_book
    save_all_books(books)
    return new_book


def update_book_metadata(book_id: str, name: str, items_per_page: int, notes: str):
    books = load_all_books()
    if book_id in books:
        books[book_id]["name"] = name.strip()
        books[book_id]["items_per_page"] = int(items_per_page)
        books[book_id]["notes"] = notes.strip()
        books[book_id]["updated_at"] = datetime.now().isoformat()
        save_all_books(books)


def delete_book(book_id: str):
    books = load_all_books()
    if book_id in books:
        del books[book_id]
        save_all_books(books)


def reset_book_printed_items(book_id: str):
    """Clears history so the entire book can be reprinted from scratch."""
    books = load_all_books()
    if book_id in books:
        books[book_id]["printed_item_ids"] = []
        books[book_id]["updated_at"] = datetime.now().isoformat()
        save_all_books(books)


def commit_items_to_book(book_id: str, new_item_ids: list):
    """Appends new item IDs to the book's permanent printed registry."""
    books = load_all_books()
    if book_id in books:
        current_ids = set(books[book_id].get("printed_item_ids", []))
        for item_id in new_item_ids:
            current_ids.add(str(item_id))
        books[book_id]["printed_item_ids"] = list(current_ids)
        books[book_id]["updated_at"] = datetime.now().isoformat()
        save_all_books(books)


def calculate_book_pagination_state(book: dict, all_items_df):
    """
    Computes exact page positions, tail page items, and unprinted polishes.
    """
    capacity = max(1, int(book.get("items_per_page", 24)))
    printed_ids = set(book.get("printed_item_ids", []))
    
    # Filter inventory into already committed vs unprinted
    committed_df = all_items_df[all_items_df["item_id"].isin(printed_ids)].copy()
    unprinted_df = all_items_df[~all_items_df["item_id"].isin(printed_ids)].copy()
    
    total_committed = len(committed_df)
    
    if total_committed == 0:
        return {
            "total_committed": 0,
            "total_pages": 0,
            "slots_on_last_page": 0,
            "free_slots_on_last_page": capacity,
            "last_page_df": all_items_df.iloc[0:0],
            "unprinted_df": unprinted_df,
            "start_page_num": 1,
            "is_last_page_partial": False
        }
        
    remainder = total_committed % capacity
    if remainder == 0:
        total_pages = total_committed // capacity
        free_slots = 0
        last_page_items = committed_df.iloc[-capacity:]
        start_page_num = total_pages + 1
        is_partial = False
    else:
        total_pages = (total_committed // capacity) + 1
        free_slots = capacity - remainder
        last_page_items = committed_df.iloc[-remainder:]
        start_page_num = total_pages
        is_partial = True

    return {
        "total_committed": total_committed,
        "total_pages": total_pages,
        "slots_on_last_page": remainder if remainder != 0 else capacity,
        "free_slots_on_last_page": free_slots,
        "last_page_df": last_page_items,
        "unprinted_df": unprinted_df,
        "start_page_num": start_page_num,
        "is_last_page_partial": is_partial
    }