# expense-tracker
A simple desktop application to record and manage daily expenses. Built with **Python, Tkinter, and SQLite**,

"""
expense_tracker.py

Expense Tracker GUI using Tkinter + SQLite + Matplotlib.

Features:
- Add / Update / Delete expense records (date, category, amount, note)
- View records in a table (Treeview)
- Filter by date range and/or category
- Monthly summary (total per month) and category summary
- Plot summary chart (Matplotlib) in a popup
- Export filtered records to CSV

Usage:
    python expense_tracker.py

Dependencies:
- Python 3.8+
- tkinter (built-in)
- sqlite3 (built-in)
- matplotlib (pip install matplotlib)
- pandas (optional for CSV export; but built-in csv module is used here)
"""

import sqlite3
import datetime
import csv
import os
from tkinter import *
from tkinter import ttk, messagebox, filedialog
from tkinter.simpledialog import askstring

# Optional import for plotting
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False

DB_FILE = "expenses.db"


# ---------------------------
# Database utilities
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT
        )
    """)
    conn.commit()
    conn.close()


def insert_expense(date, category, amount, note):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (date, category, amount, note) VALUES (?, ?, ?, ?)",
        (date, category, amount, note),
    )
    conn.commit()
    conn.close()


def update_expense(record_id, date, category, amount, note):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE expenses SET date = ?, category = ?, amount = ?, note = ? WHERE id = ?",
        (date, category, amount, note, record_id),
    )
    conn.commit()
    conn.close()


def delete_expense(record_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def fetch_expenses(start_date=None, end_date=None, category=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    query = "SELECT id, date, category, amount, note FROM expenses WHERE 1=1"
    params = []
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if category and category.strip():
        query += " AND category = ?"
        params.append(category.strip())
    query += " ORDER BY date DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def fetch_category_summary(start_date=None, end_date=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    query = "SELECT category, SUM(amount) FROM expenses WHERE 1=1"
    params = []
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " GROUP BY category ORDER BY SUM(amount) DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def fetch_monthly_summary():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Group by year-month
    query = """
        SELECT SUBSTR(date,1,7) AS month, SUM(amount) 
        FROM expenses
        GROUP BY month
        ORDER BY month DESC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows


# ---------------------------
# GUI / App logic
# ---------------------------
class ExpenseTrackerApp:
    def __init__(self, root):
        self.root = root
        root.title("Expense Tracker")
        root.geometry("900x600")
        # Top frame for inputs
        self.top_frame = Frame(root, pady=8)
        self.top_frame.pack(fill=X)

        # Date
        Label(self.top_frame, text="Date (YYYY-MM-DD)").grid(row=0, column=0, padx=5, sticky=W)
        self.date_var = StringVar()
        self.date_entry = Entry(self.top_frame, textvariable=self.date_var, width=14)
        self.date_entry.grid(row=1, column=0, padx=5)
        self.date_var.set(datetime.date.today().isoformat())

        # Category
        Label(self.top_frame, text="Category").grid(row=0, column=1, padx=5, sticky=W)
        self.category_var = StringVar()
        self.category_entry = Entry(self.top_frame, textvariable=self.category_var, width=18)
        self.category_entry.grid(row=1, column=1, padx=5)

        # Amount
        Label(self.top_frame, text="Amount").grid(row=0, column=2, padx=5, sticky=W)
        self.amount_var = StringVar()
        self.amount_entry = Entry(self.top_frame, textvariable=self.amount_var, width=12)
        self.amount_entry.grid(row=1, column=2, padx=5)

        # Note
        Label(self.top_frame, text="Note").grid(row=0, column=3, padx=5, sticky=W)
        self.note_var = StringVar()
        self.note_entry = Entry(self.top_frame, textvariable=self.note_var, width=30)
        self.note_entry.grid(row=1, column=3, padx=5)

        # Buttons
        Button(self.top_frame, text="Add", command=self.add_record, width=10).grid(row=1, column=4, padx=6)
        Button(self.top_frame, text="Update", command=self.update_record, width=10).grid(row=1, column=5, padx=6)
        Button(self.top_frame, text="Delete", command=self.delete_record, width=10).grid(row=1, column=6, padx=6)

        # Filter frame
        self.filter_frame = Frame(root, pady=6)
        self.filter_frame.pack(fill=X)
        Label(self.filter_frame, text="Filter - Start Date:").grid(row=0, column=0, padx=4, sticky=W)
        self.filter_start = StringVar()
        Entry(self.filter_frame, textvariable=self.filter_start, width=12).grid(row=0, column=1, padx=4)
        Label(self.filter_frame, text="End Date:").grid(row=0, column=2, padx=4)
        self.filter_end = StringVar()
        Entry(self.filter_frame, textvariable=self.filter_end, width=12).grid(row=0, column=3, padx=4)
        Label(self.filter_frame, text="Category:").grid(row=0, column=4, padx=4)
        self.filter_category = StringVar()
        Entry(self.filter_frame, textvariable=self.filter_category, width=16).grid(row=0, column=5, padx=4)
        Button(self.filter_frame, text="Apply Filter", command=self.apply_filter).grid(row=0, column=6, padx=6)
        Button(self.filter_frame, text="Clear Filter", command=self.clear_filter).grid(row=0, column=7, padx=6)

        # Table frame
        self.table_frame = Frame(root)
        self.table_frame.pack(fill=BOTH, expand=True, pady=8)

        columns = ("id", "date", "category", "amount", "note")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col.capitalize())
            # Make columns reasonably wide
            if col == "note":
                self.tree.column(col, width=300)
            elif col == "amount":
                self.tree.column(col, width=80, anchor=E)
            else:
                self.tree.column(col, width=100)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Vertical scrollbar
        vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=RIGHT, fill=Y)

        # Bottom controls (summary / chart / export)
        self.bottom_frame = Frame(root, pady=6)
        self.bottom_frame.pack(fill=X)
        Button(self.bottom_frame, text="Monthly Summary", command=self.show_monthly_summary).grid(row=0, column=0, padx=6)
        Button(self.bottom_frame, text="Category Summary", command=self.show_category_summary).grid(row=0, column=1, padx=6)
        Button(self.bottom_frame, text="Plot Summary (Matplotlib)", command=self.plot_monthly_summary).grid(row=0, column=2, padx=6)
        Button(self.bottom_frame, text="Export CSV (Filtered)", command=self.export_csv).grid(row=0, column=3, padx=6)
        Button(self.bottom_frame, text="Add Category Quick", command=self.quick_add_category).grid(row=0, column=4, padx=6)

        # Load initial data
        self.load_all_records()

    # -----------------------
    # CRUD Handlers
    # -----------------------
    def add_record(self):
        date = self.date_var.get().strip()
        category = self.category_var.get().strip()
        amount = self.amount_var.get().strip()
        note = self.note_var.get().strip()

        # Basic validation
        if not date or not category or not amount:
            messagebox.showerror("Required", "Date, Category and Amount are required.")
            return
        try:
            # Check date format
            datetime.datetime.strptime(date, "%Y-%m-%d")
            amt = float(amount)
        except ValueError:
            messagebox.showerror("Invalid", "Date must be YYYY-MM-DD and amount must be a number.")
            return

        insert_expense(date, category, amt, note)
        messagebox.showinfo("Added", "Expense added successfully.")
        self.clear_inputs()
        self.load_all_records()

    def update_record(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select", "Select a record to update.")
            return
        record_id = self.tree.item(selected[0])["values"][0]
        date = self.date_var.get().strip()
        category = self.category_var.get().strip()
        amount = self.amount_var.get().strip()
        note = self.note_var.get().strip()
        if not date or not category or not amount:
            messagebox.showerror("Required", "Date, Category and Amount are required.")
            return
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
            amt = float(amount)
        except ValueError:
            messagebox.showerror("Invalid", "Date must be YYYY-MM-DD and amount must be a number.")
            return
        update_expense(record_id, date, category, amt, note)
        messagebox.showinfo("Updated", "Record updated.")
        self.load_all_records()

    def delete_record(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select", "Select a record to delete.")
            return
        if not messagebox.askyesno("Confirm", "Delete selected record?"):
            return
        record_id = self.tree.item(selected[0])["values"][0]
        delete_expense(record_id)
        messagebox.showinfo("Deleted", "Record deleted.")
        self.load_all_records()

    # -----------------------
    # Utility / UI
    # -----------------------
    def clear_inputs(self):
        self.date_var.set(datetime.date.today().isoformat())
        self.category_var.set("")
        self.amount_var.set("")
        self.note_var.set("")

    def load_all_records(self):
        # No filters by default
        self.populate_table(fetch_expenses())

    def populate_table(self, rows):
        # Clear
        for r in self.tree.get_children():
            self.tree.delete(r)
        for row in rows:
            self.tree.insert("", END, values=row)

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        row = self.tree.item(sel[0])["values"]
        # id, date, category, amount, note
        self.date_var.set(row[1])
        self.category_var.set(row[2])
        self.amount_var.set(str(row[3]))
        self.note_var.set(row[4] or "")

    # -----------------------
    # Filters & Export
    # -----------------------
    def apply_filter(self):
        start = self.filter_start.get().strip() or None
        end = self.filter_end.get().strip() or None
        cat = self.filter_category.get().strip() or None

        # Validate dates (if provided)
        for d in (start, end):
            if d:
                try:
                    datetime.datetime.strptime(d, "%Y-%m-%d")
                except ValueError:
                    messagebox.showerror("Invalid Date", "Use YYYY-MM-DD format for dates.")
                    return

        rows = fetch_expenses(start, end, cat)
        self.populate_table(rows)

    def clear_filter(self):
        self.filter_start.set("")
        self.filter_end.set("")
        self.filter_category.set("")
        self.load_all_records()

    def export_csv(self):
        # Export currently displayed rows
        rows = [self.tree.item(r)["values"] for r in self.tree.get_children()]
        if not rows:
            messagebox.showinfo("No data", "No records to export.")
            return
        save_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                 filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not save_path:
            return
        with open(save_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "date", "category", "amount", "note"])
            writer.writerows(rows)
        messagebox.showinfo("Exported", f"Exported {len(rows)} records to {save_path}")

    # -----------------------
    # Summaries / Charts
    # -----------------------
    def show_monthly_summary(self):
        rows = fetch_monthly_summary()
        if not rows:
            messagebox.showinfo("No Data", "No records to summarize.")
            return
        text = "Month\tTotal\n" + "\n".join(f"{r[0]}\t{float(r[1]):.2f}" for r in rows)
        self._popup_text("Monthly Summary (YYYY-MM)", text)

    def show_category_summary(self):
        start = self.filter_start.get().strip() or None
        end = self.filter_end.get().strip() or None
        rows = fetch_category_summary(start, end)
        if not rows:
            messagebox.showinfo("No Data", "No records to summarize.")
            return
        text = "Category\tTotal\n" + "\n".join(f"{r[0]}\t{float(r[1]):.2f}" for r in rows)
        self._popup_text("Category Summary", text)

    def plot_monthly_summary(self):
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showerror("Missing", "Matplotlib is not available. Install it with:\n\npip install matplotlib")
            return
        rows = fetch_monthly_summary()
        if not rows:
            messagebox.showinfo("No Data", "No records to plot.")
            return
        months = [r[0] for r in reversed(rows)]
        totals = [float(r[1]) for r in reversed(rows)]
        # Create a simple bar chart in a new Tk window
        win = Toplevel(self.root)
        win.wm_title("Monthly Expense Chart")
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(months, totals)
        ax.set_ylabel("Total Amount")
        ax.set_xlabel("Month (YYYY-MM)")
        ax.set_title("Monthly Expenses")
        plt.xticks(rotation=45, ha="right")
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=BOTH, expand=True)

    def quick_add_category(self):
        """Prompt for category and a single amount for quick add (today's date)."""
        cat = askstring("Quick Add", "Category name:")
        if not cat:
            return
        amt = askstring("Quick Add", "Amount:")
        if not amt:
            return
        try:
            amt_val = float(amt)
        except ValueError:
            messagebox.showerror("Invalid", "Amount must be numeric.")
            return
        insert_expense(datetime.date.today().isoformat(), cat.strip(), amt_val, "Quick add")
        messagebox.showinfo("Added", "Quick expense added.")
        self.load_all_records()

    def _popup_text(self, title, text):
        win = Toplevel(self.root)
        win.wm_title(title)
        txt = Text(win, wrap="none", width=80, height=20)
        txt.insert("1.0", text)
        txt.configure(state=DISABLED)
        txt.pack(fill=BOTH, expand=True)


# ---------------------------
# Main
# ---------------------------
def main():
    init_db()
    root = Tk()
    app = ExpenseTrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
