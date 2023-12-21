import json
import random
import string
from datetime import datetime, timedelta

class User:
    def __init__(self, name):
        self.name = name
        self.token = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
        self.borrowed_books = {}

class LibraryAdmin(User):
    def __init__(self, name):
        super().__init__(name)
        self.permissions = ["remove_book", "find_book", "borrow_book", "return_book", "add_book"]

    def has_add_book_permission(self):
        return "add_book" in self.permissions

class Book:
    def __init__(self, title, author, copies):
        self.title = title
        self.author = author
        self.copies = copies
        self.due_dates = []  # List to store due dates for each copy

    def check_out(self, num_copies=1):
        if self.copies >= num_copies:
            self.copies -= num_copies
            due_dates = []
            for _ in range(num_copies):
                due_date = datetime.now() + timedelta(days=14)
                due_dates.append(due_date)
            return True, due_dates
        else:
            return False, None

    def return_book(self):
        self.copies += 1

    def add_due_date(self, due_date):
        self.due_dates.append(due_date)
        self.copies -= 1  # Decrement copies when adding a due date

class Library:
    def __init__(self):
        self.books = {}
        self.users = {}
        self.admin_password = '123abc'
        self.admin_token = None
        self.load_data()

    def load_data(self):
        self.load_books_data()
        try:
            with open("library_data.json", "r") as file:
                data = json.load(file)
                self.admin_token = data.get("admin_token", None)
                users_data = data.get("users", {})
                for token, user_data in users_data.items():
                    user = self.create_user_from_data(user_data)
                    user.token = token
                    self.users[token] = user
        except FileNotFoundError:
            pass

    def load_books_data(self):
        try:
            with open("books_data.json", "r") as file:
                data = json.load(file)
                self.books = data.get("books", {})
        except FileNotFoundError:
            pass

    def create_user_from_data(self, user_data):
        if "permissions" in user_data and "admin" in user_data["permissions"]:
            user = LibraryAdmin(user_data["name"])
            user.permissions = user_data.get("permissions", [])
        else:
            user = User(user_data["name"])
            user.permissions = []
        borrowed_books = {title: datetime.strptime(due_date, '%Y-%m-%d') for title, due_date in
                          user_data.get("borrowed_books", {}).items()}
        user.borrowed_books = borrowed_books
        return user

    def create_user(self, name, user_type):
        if user_type == "admin":
            if not self.admin_token:
                admin = LibraryAdmin(name)
                admin.permissions = ["remove_book", "find_book", "borrow_book", "return_book", "add_book"]
                self.admin_token = admin.token
                self.users[admin.token] = admin
                return self.admin_token
            else:
                return None
        else:
            while True:
                user = User(name)
                user_token = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
                if user_token not in self.users:
                    user.token = user_token
                    self.users[user.token] = user
                    self.save_data()
                    return user.token

    def add_book(self, category, language, title, author, copies, user_token):
        user = self.find_user(user_token)

        if user and (isinstance(user, LibraryAdmin) or (self.admin_token and user_token == self.admin_token)):
            admin_password = input("Enter the admin password: ").lower()
            if admin_password == self.admin_password:
                category = category.lower()

                self.books.setdefault(category, {}).setdefault(language, {})

                if title not in self.books[category][language]:
                    book = {"author": author, "copies": copies}
                    self.books[category][language][title] = book
                    self.save_books_data()
                    return "Book added successfully."
                else:
                    return "Book with the same title already exists."
            else:
                return "Invalid admin password. Access denied."
        return "Unauthorized to add books."

    def remove_book(self, title, user_token):
        user = self.find_user(user_token)
        if user and ("remove_book" in user.permissions or (self.admin_token and user_token == self.admin_token)):
            for category, languages in self.books.items():
                for language, books_info in languages.items():
                    if title in books_info:
                        del books_info[title]
                        self.save_books_data()
                        return "Book removed successfully."

            return "Book not found or unauthorized to remove books."

    def list_books(self):
        if not self.books:
            print("No books available in the library.")
            return

        for category, languages in self.books.items():
            for language, books_info in languages.items():
                print(f"\nLanguage: {language}, Category: {category}")
                for title, book_info in books_info.items():
                    print(f"Title: {title}, Author: {book_info['author']}, Copies: {book_info['copies']}")

    def find_book(self):
        print("Available Categories:")
        for category in self.books.keys():
            print(f"- {category.capitalize()}")

        user_category = input("Choose a category: ").lower()
        if user_category in self.books:
            print(f"Available Languages in {user_category.capitalize()}:")
            for language in self.books[user_category].keys():
                print(f"- {language.capitalize()}")

            user_language = input("Choose a language: ").lower()
            if user_language in self.books[user_category]:
                print(f"Available Books in {user_language.capitalize()} under {user_category.capitalize()}:")
                for title, book_info in self.books[user_category][user_language].items():
                    print(f"- {title}")

                user_title = input("Choose a book: ").lower()
                if user_title in self.books[user_category][user_language]:
                    return Book(
                        user_title,
                        self.books[user_category][user_language][user_title]['author'],
                        self.books[user_category][user_language][user_title]['copies']
                    )

        return None

    
    def borrow_book(self, user_token):
        user = self.find_user(user_token)
        book = self.find_book()

        if user and book:
            num_copies_requested = int(input("Enter the number of copies you want to borrow: "))

            success, due_dates = book.check_out(num_copies_requested)

            if success:
                # Update the number of copies in books_data.json
                self.update_copies_in_books_data(book, num_copies_requested)

                for due_date in due_dates:
                    user.borrowed_books[book.title] = due_date

                self.save_data()
                return f"{num_copies_requested} copies of '{book.title}' borrowed successfully. Due dates: {[date.strftime('%Y-%m-%d') for date in due_dates]}"
            else:
                return f"Requested number of copies ({num_copies_requested}) not available for '{book.title}'. Only {book.copies} copies available."

        return "Unauthorized to borrow or book not found."

    def update_copies_in_books_data(self, book, num_copies_borrowed):
        for category, languages in self.books.items():
            for language, books_info in languages.items():
                if book.title in books_info:
                    books_info[book.title]['copies'] -= num_copies_borrowed
                    self.save_books_data()
                    break



    def return_book(self, user_token):
        user = self.find_user(user_token)
        book = self.find_book()
        if user and book:
            book.return_book()
            if book.title in user.borrowed_books:
                del user.borrowed_books[book.title]
                self.save_data()
                return "Book returned successfully."
            else:
                return "Book not borrowed by this user."
        return "Unauthorized to return or book not found."

    # def find_user(self, token):
    #     return self.users.get(token)
    def find_user(self, token):
        user = self.users.get(token)
        if user is None:
            print("User not found. Please check your token.")
        return user


    def save_data(self):
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.strftime('%Y-%m-%d')
            return obj

        with open("library_data.json", "w") as file:
            data = {
                "admin_token": self.admin_token,
                "users": {
                    token: {
                        "name": user.name,
                        "permissions": user.permissions if isinstance(user, LibraryAdmin) else [],
                        "borrowed_books": {
                            title: due_date.strftime('%Y-%m-%d') for title, due_date in user.borrowed_books.items()
                        }
                    } for token, user in self.users.items() if isinstance(user, User)
                }
            }
            json.dump(data, file, default=serialize, indent=2)

    def save_books_data(self):
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.strftime('%Y-%m-%d')
            return obj

        with open("books_data.json", "w") as file:
            data = {
                "books": self.books
            }
            json.dump(data, file, default=serialize, indent=2)

def main():
    library = Library()
    library.load_data()

    while True:
        print("\nLibrary Management System")
        print("1. Admin")
        print("2. Member")
        print("3. Exit")
        choice = input("Enter your choice: ").lower()

        if choice == "1":
            admin_password = input("Enter the admin password: ").lower()
            if admin_password == library.admin_password:
                print("\nHey....Admin")
                while True:
                    print("\nAdmin Menu")
                    print("1. Add a Book")
                    print("2. Remove a Book")
                    print("3. List Books")
                    print("4. Exit")
                    admin_choice = input("Enter your choice: ").lower()
                    if admin_choice == "1":
                        category = input("Enter the category of the book: ").lower()
                        language = input("Enter the language of the book: ").lower()
                        title = input("Enter the title of the book: ").lower()
                        author = input("Enter the author: ").lower()
                        copies = int(input("Enter the number of copies: "))
                        result = library.add_book(category, language, title, author, copies, library.admin_token)
                        print(result)
                    elif admin_choice == "2":
                        title = input("Enter the title of the book you want to remove: ").lower()
                        result = library.remove_book(title, library.admin_token)
                        print(result)
                    elif admin_choice == "3":
                        library.list_books()
                    elif admin_choice == "4":
                        break
                    else:
                        print("Invalid choice. Please try again.")
            else:
                print("Invalid admin password. Access denied.")
        elif choice == "2":
            while True:
                print("\nMember Menu")
                print("1. New Member")
                print("2. Existing Member")
                print("3. Exit")
                member_choice = input("Enter your choice: ")
                if member_choice == "1":
                    name = input("Enter your name: ").capitalize()
                    user_token = library.create_user(name, "user")
                    while user_token is None:
                        print("Invalid token. Please try again.")
                        user_token = library.create_user(name, "user")
                    print(f"User created with token: {user_token}")
                    while True:
                        print("\nMember Menu")
                        print("1. List Books")
                        print("2. Find a Book")
                        print("3. Borrow a Book")
                        print("4. Return a Book")
                        print("5. Exit")
                        member_choice = input("Enter your choice: ")
                        if member_choice == "1":
                            library.list_books()
                        elif member_choice == "2":
                            book = library.find_book()
                            if book:
                                print(
                                    f"Book found - Title: {book.title}, Author: {book.author}, Copies Available: {book.copies}")
                            else:
                                print("Book not found in the library.")
                        elif member_choice == "3":
                            result = library.borrow_book(user_token)
                            print(result)
                        elif member_choice == "4":
                            result = library.return_book(user_token)
                            print(result)
                        elif member_choice == "5":
                            break
                        else:
                            print("Invalid choice. Please try again.")
                elif member_choice == "2":
                    user_token = input("Enter your token: ")
                    user = library.find_user(user_token)
                    if user:
                        print(f"Welcome back, {user.name}!")
                        while True:
                            print("\nMember Menu")
                            print("1. List Books")
                            print("2. Find a Book")
                            print("3. Borrow a Book")
                            print("4. Return a Book")
                            print("5. View Borrowed Books")
                            print("6. Exit")
                            member_choice = input("Enter your choice: ")
                            if member_choice == "1":
                                library.list_books()
                            elif member_choice == "2":
                                book = library.find_book()
                                if book:
                                    print(
                                        f"Book found - Title: {book.title}, Author: {book.author}, Copies Available: {book.copies}")
                                else:
                                    print("Book not found in the library.")
                            elif member_choice == "3":
                                result = library.borrow_book(user_token)
                                print(result)
                            elif member_choice == "4":
                                result = library.return_book(user_token)
                                print(result)
                            elif member_choice == "5":
                                if user.borrowed_books:
                                    print("Borrowed Books:")
                                    for title, due_date in user.borrowed_books.items():
                                        print(f"Title: {title}, Due Date: {due_date.strftime('%Y-%m-%d')}")
                                else:
                                    print("No books currently borrowed.")
                            elif member_choice == "6":
                                break
                            else:
                                print("Invalid choice. Please try again.")
                elif member_choice == "3":
                    break
                else:
                    print("Invalid choice. Please try again.")
        elif choice == "3":
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
