import calendar
import sqlite3

DB_PATH = "finance.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_date TEXT NOT NULL,
            tx_type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT DEFAULT '',
            series_id TEXT DEFAULT '',
            source_type TEXT DEFAULT '',
            gross_amount REAL DEFAULT 0,
            tax_rate REAL DEFAULT 0,
            tax_amount REAL DEFAULT 0,
            net_amount REAL DEFAULT 0
        )
        """
    )

    columns = [row[1] for row in cur.execute("PRAGMA table_info(transactions)").fetchall()]
    if "series_id" not in columns:
        cur.execute("ALTER TABLE transactions ADD COLUMN series_id TEXT DEFAULT ''")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS planned_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            due_date TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT DEFAULT '',
            series_id TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'planned',
            recurrence TEXT NOT NULL DEFAULT 'none'
        )
        """
    )

    planned_columns = [row[1] for row in cur.execute("PRAGMA table_info(planned_expenses)").fetchall()]
    if "series_id" not in planned_columns:
        cur.execute("ALTER TABLE planned_expenses ADD COLUMN series_id TEXT DEFAULT ''")

    conn.commit()
    conn.close()


# ----------------------------
# Transactions
# ----------------------------
def add_transaction(
    tx_date: str,
    tx_type: str,
    category: str,
    amount: float,
    note: str = "",
    series_id: str = "",
    source_type: str = "",
    gross_amount: float = 0,
    tax_rate: float = 0,
    tax_amount: float = 0,
    net_amount: float = 0,
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO transactions
        (tx_date, tx_type, category, amount, note, series_id, source_type, gross_amount, tax_rate, tax_amount, net_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tx_date,
            tx_type,
            category,
            amount,
            note,
            series_id,
            source_type,
            gross_amount,
            tax_rate,
            tax_amount,
            net_amount,
        ),
    )

    conn.commit()
    conn.close()


def delete_transaction(transaction_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()


def delete_transaction_series(
    tx_date: str,
    tx_type: str,
    category: str,
    amount: float,
    note: str = "",
    source_type: str = "",
    gross_amount: float = 0,
    tax_rate: float = 0,
    tax_amount: float = 0,
    net_amount: float = 0,
):
    conn = get_connection()
    cur = conn.cursor()
    day_part = tx_date[8:10]
    cur.execute(
        """
        DELETE FROM transactions
        WHERE tx_type = ?
          AND category = ?
          AND amount = ?
          AND note = ?
          AND source_type = ?
          AND gross_amount = ?
          AND tax_rate = ?
          AND tax_amount = ?
          AND net_amount = ?
          AND substr(tx_date, 9, 2) = ?
        """,
        (
            tx_type,
            category,
            amount,
            note,
            source_type,
            gross_amount,
            tax_rate,
            tax_amount,
            net_amount,
            day_part,
        ),
    )
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


def delete_transaction_series_by_id(series_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE series_id = ? AND series_id != ''", (series_id,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


def delete_transactions_for_month(month_str: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM transactions WHERE substr(tx_date, 1, 7) = ?",
        (month_str,),
    )
    conn.commit()
    conn.close()


def get_transactions_for_month(month_str: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, tx_date, tx_type, category, amount, note, series_id,
               source_type, gross_amount, tax_rate, tax_amount, net_amount
        FROM transactions
        WHERE substr(tx_date, 1, 7) = ?
        ORDER BY tx_date DESC, id DESC
        """,
        (month_str,),
    )

    rows = cur.fetchall()
    conn.close()
    return rows


def get_month_summary(month_str: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE substr(tx_date, 1, 7) = ? AND tx_type = 'income'
        """,
        (month_str,),
    )
    income = cur.fetchone()[0] or 0

    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE substr(tx_date, 1, 7) = ? AND tx_type = 'expense'
        """,
        (month_str,),
    )
    expenses = cur.fetchone()[0] or 0

    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE substr(tx_date, 1, 7) = ? AND tx_type = 'saving'
        """,
        (month_str,),
    )
    savings = cur.fetchone()[0] or 0

    month_end = f"{month_str}-31"
    cur.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN tx_type = 'expense' THEN amount ELSE 0 END), 0)
        FROM transactions
        WHERE tx_date <= ?
        """,
        (month_end,),
    )
    reserve_income, reserve_expenses = cur.fetchone()

    conn.close()

    return {
        "income": income,
        "expenses": expenses,
        "savings": savings,
        "leftover": income - expenses - savings,
        "savings_balance": (reserve_income or 0) - (reserve_expenses or 0),
    }


# ----------------------------
# Planned expenses / obligations
# ----------------------------
def add_planned_expense(
    due_date: str,
    title: str,
    category: str,
    amount: float,
    note: str = "",
    series_id: str = "",
    status: str = "planned",
    recurrence: str = "none",
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO planned_expenses
        (due_date, title, category, amount, note, series_id, status, recurrence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (due_date, title, category, amount, note, series_id, status, recurrence),
    )

    conn.commit()
    conn.close()


def delete_planned_expense(expense_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM planned_expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


def update_planned_expense_status(expense_id: int, status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE planned_expenses SET status = ? WHERE id = ?", (status, expense_id))
    conn.commit()
    conn.close()


def delete_planned_expense_series_by_id(series_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM planned_expenses WHERE series_id = ? AND series_id != ''", (series_id,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


def get_planned_expenses_for_month(month_str: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, due_date, title, category, amount, note, series_id, status, recurrence
        FROM planned_expenses
        WHERE substr(due_date, 1, 7) = ?
        ORDER BY due_date ASC, id DESC
        """,
        (month_str,),
    )

    rows = cur.fetchall()
    conn.close()
    return rows


def get_planned_expenses_for_year(year_str: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, due_date, title, category, amount, note, series_id, status, recurrence
        FROM planned_expenses
        WHERE substr(due_date, 1, 4) = ?
        ORDER BY due_date ASC, id DESC
        """,
        (year_str,),
    )

    rows = cur.fetchall()
    conn.close()
    return rows


def get_planned_total_for_year(year_str: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM planned_expenses
        WHERE substr(due_date, 1, 4) = ? AND status = 'planned'
        """,
        (year_str,),
    )

    total = cur.fetchone()[0] or 0
    conn.close()
    return total


def get_flow_breakdown_for_month(month_str: str):
    conn = get_connection()
    cur = conn.cursor()

    month_start = f"{month_str}-01"

    cur.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN tx_type = 'expense' THEN amount ELSE 0 END), 0)
        FROM transactions
        WHERE tx_date < ?
        """,
        (month_start,),
    )
    opening_income, opening_expense = cur.fetchone()

    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM planned_expenses
        WHERE due_date < ? AND status = 'planned'
        """,
        (month_start,),
    )
    opening_planned = cur.fetchone()[0] or 0
    opening_balance = (opening_income or 0) - (opening_expense or 0) - opening_planned

    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE substr(tx_date, 1, 7) = ? AND tx_type = 'income'
        """,
        (month_str,),
    )
    income_total = cur.fetchone()[0] or 0

    cur.execute(
        """
        SELECT category, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE substr(tx_date, 1, 7) = ? AND tx_type = 'expense'
        GROUP BY category
        ORDER BY SUM(amount) DESC, category ASC
        """,
        (month_str,),
    )
    expense_rows = cur.fetchall()

    cur.execute(
        """
        SELECT title, COALESCE(SUM(amount), 0)
        FROM planned_expenses
        WHERE substr(due_date, 1, 7) = ? AND status = 'planned'
        GROUP BY title
        ORDER BY SUM(amount) DESC, title ASC
        """,
        (month_str,),
    )
    planned_rows = cur.fetchall()

    conn.close()

    allocation_rows = list(expense_rows) + [(f"Planned: {title}", amount) for title, amount in planned_rows]
    total_available = opening_balance + income_total
    allocated_total = sum(amount for _, amount in allocation_rows)
    remaining_balance = total_available - allocated_total

    return {
        "total_available": total_available,
        "opening_balance": opening_balance,
        "income_total": income_total,
        "allocation_rows": allocation_rows,
        "remaining_balance": remaining_balance,
    }


def get_flow_breakdown_for_year(year_str: str):
    conn = get_connection()
    cur = conn.cursor()

    year_start = f"{year_str}-01-01"

    cur.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN tx_type = 'expense' THEN amount ELSE 0 END), 0)
        FROM transactions
        WHERE tx_date < ?
        """,
        (year_start,),
    )
    opening_income, opening_expense = cur.fetchone()

    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM planned_expenses
        WHERE due_date < ? AND status = 'planned'
        """,
        (year_start,),
    )
    opening_planned = cur.fetchone()[0] or 0
    opening_balance = (opening_income or 0) - (opening_expense or 0) - opening_planned

    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE substr(tx_date, 1, 4) = ? AND tx_type = 'income'
        """,
        (year_str,),
    )
    income_total = cur.fetchone()[0] or 0

    cur.execute(
        """
        SELECT category, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE substr(tx_date, 1, 4) = ? AND tx_type = 'expense'
        GROUP BY category
        ORDER BY SUM(amount) DESC, category ASC
        """,
        (year_str,),
    )
    expense_rows = cur.fetchall()

    cur.execute(
        """
        SELECT title, COALESCE(SUM(amount), 0)
        FROM planned_expenses
        WHERE substr(due_date, 1, 4) = ? AND status = 'planned'
        GROUP BY title
        ORDER BY SUM(amount) DESC, title ASC
        """,
        (year_str,),
    )
    planned_rows = cur.fetchall()

    conn.close()

    allocation_rows = list(expense_rows) + [(f"Planned: {title}", amount) for title, amount in planned_rows]
    total_available = opening_balance + income_total
    allocated_total = sum(amount for _, amount in allocation_rows)
    remaining_balance = total_available - allocated_total

    return {
        "total_available": total_available,
        "opening_balance": opening_balance,
        "income_total": income_total,
        "allocation_rows": allocation_rows,
        "remaining_balance": remaining_balance,
    }


# ----------------------------
# Series for charts
# ----------------------------
def get_monthly_series(year_str: str):
    conn = get_connection()
    cur = conn.cursor()

    year_start = f"{year_str}-01-01"

    cur.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN tx_type = 'expense' THEN amount ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN tx_type = 'saving' THEN amount ELSE 0 END), 0)
        FROM transactions
        WHERE tx_date < ?
        """,
        (year_start,),
    )
    opening_income, opening_expense, opening_saving = cur.fetchone()

    cur.execute(
        """
        SELECT substr(tx_date, 1, 7) AS month_key,
               COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount ELSE 0 END), 0) AS income,
               COALESCE(SUM(CASE WHEN tx_type = 'expense' THEN amount ELSE 0 END), 0) AS expense,
               COALESCE(SUM(CASE WHEN tx_type = 'saving' THEN amount ELSE 0 END), 0) AS saving
        FROM transactions
        WHERE substr(tx_date, 1, 4) = ?
        GROUP BY month_key
        ORDER BY month_key
        """,
        (year_str,),
    )
    tx_rows = cur.fetchall()

    cur.execute(
        """
        SELECT substr(due_date, 1, 7) AS month_key,
               COALESCE(SUM(CASE WHEN status = 'planned' THEN amount ELSE 0 END), 0) AS planned
        FROM planned_expenses
        WHERE substr(due_date, 1, 4) = ?
        GROUP BY month_key
        ORDER BY month_key
        """,
        (year_str,),
    )
    planned_rows = cur.fetchall()

    conn.close()

    tx_map = {row[0]: row for row in tx_rows}
    planned_map = {row[0]: row[1] for row in planned_rows}

    running_total_balance = (opening_income or 0) - (opening_expense or 0)
    running_saved_balance = opening_saving or 0

    data = []
    for month in range(1, 13):
        month_key = f"{year_str}-{month:02d}"
        if month_key in tx_map:
            _, income, expense, saving = tx_map[month_key]
        else:
            income, expense, saving = 0, 0, 0

        planned = planned_map.get(month_key, 0)
        monthly_leftover = income - expense - saving
        running_total_balance += income - expense
        running_saved_balance += saving
        available_balance = running_total_balance - running_saved_balance

        data.append(
            {
                "month": month_key,
                "income": income,
                "expense": expense,
                "saving": saving,
                "planned": planned,
                "leftover": monthly_leftover,
                "savings_balance": running_total_balance,
                "saved_balance": running_saved_balance,
                "available_balance": available_balance,
                "total_balance": running_total_balance,
            }
        )

    return data


def get_daily_series(month_str: str):
    conn = get_connection()
    cur = conn.cursor()

    month_start = f"{month_str}-01"

    cur.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN tx_type = 'expense' THEN amount ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN tx_type = 'saving' THEN amount ELSE 0 END), 0)
        FROM transactions
        WHERE tx_date < ?
        """,
        (month_start,),
    )
    opening_income, opening_expense, opening_saving = cur.fetchone()

    cur.execute(
        """
        SELECT substr(tx_date, 9, 2) AS day_no,
               COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount ELSE 0 END), 0) AS income,
               COALESCE(SUM(CASE WHEN tx_type = 'expense' THEN amount ELSE 0 END), 0) AS expense,
               COALESCE(SUM(CASE WHEN tx_type = 'saving' THEN amount ELSE 0 END), 0) AS saving
        FROM transactions
        WHERE substr(tx_date, 1, 7) = ?
        GROUP BY day_no
        ORDER BY day_no
        """,
        (month_str,),
    )

    rows = cur.fetchall()
    conn.close()

    row_map = {int(row[0]): (row[1], row[2], row[3]) for row in rows}

    year = int(month_str[:4])
    month = int(month_str[5:7])
    day_count = calendar.monthrange(year, month)[1]

    running_total_balance = (opening_income or 0) - (opening_expense or 0)
    running_saved_balance = opening_saving or 0
    data = []

    for day in range(1, day_count + 1):
        income, expense, saving = row_map.get(day, (0, 0, 0))
        running_total_balance += income - expense
        running_saved_balance += saving
        data.append(
            {
                "day": day,
                "income": income,
                "expense": expense,
                "saving": saving,
                "leftover": income - expense - saving,
                "saved_balance": running_saved_balance,
                "available_balance": running_total_balance - running_saved_balance,
                "total_balance": running_total_balance,
            }
        )

    return data


def get_expense_category_totals(month_str: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT category, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE substr(tx_date, 1, 7) = ? AND tx_type = 'expense'
        GROUP BY category
        ORDER BY SUM(amount) DESC
        """,
        (month_str,),
    )

    rows = cur.fetchall()
    conn.close()
    return rows


def get_expense_category_totals_for_year(year_str: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT category, COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE substr(tx_date, 1, 4) = ? AND tx_type = 'expense'
        GROUP BY category
        ORDER BY SUM(amount) DESC
        """,
        (year_str,),
    )

    rows = cur.fetchall()
    conn.close()
    return rows
