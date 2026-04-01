import calendar
from datetime import datetime
import traceback
import uuid
import flet as ft

from calculations import (
    AGE_GROUP_UNDER_66,
    INCOME_MODE_GROSS,
    INCOME_MODE_NET,
    PRIMARY_INCOME,
    estimate_swedish_salary,
    get_tax_table_choices,
    refresh_swedish_tax_cache,
)
from database import (
    init_db,
    add_transaction,
    delete_transaction,
    delete_transaction_series_by_id,
    delete_transaction_series,
    delete_transactions_for_month,
    get_transactions_for_month,
    get_month_summary,
    add_planned_expense,
    delete_planned_expense,
    delete_planned_expense_series_by_id,
    update_planned_expense_status,
    get_planned_expenses_for_month,
    get_planned_expenses_for_year,
    get_planned_total_for_year,
    get_flow_breakdown_for_month,
    get_flow_breakdown_for_year,
    get_monthly_series,
    get_daily_series,
    get_expense_category_totals,
    get_expense_category_totals_for_year,
)
from charts import (
    build_daily_activity_list,
    build_daily_bar_overview,
    build_yearly_bar_overview,
    build_yearly_totals_pie_chart,
    build_flow_breakdown_chart,
    build_expense_category_bars,
    build_expense_pie_chart,
)

BG = "#07111F"
PANEL = "#0F172A"
PANEL_ALT = "#101A2C"
BORDER = "#22314A"
TEXT = "#E2E8F0"
MUTED = "#94A3B8"
SUBTLE = "#64748B"
ACCENT = "#22D3EE"
PURPLE = "#7C3AED"

MONTH_OPTIONS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
YEAR_OPTIONS = [str(year) for year in range(2024, 2038)]
TYPE_OPTIONS = ["income", "expense", "saving"]
PLANNED_STATUS_OPTIONS = ["planned", "paid", "skipped"]
PLANNED_RECURRENCE_OPTIONS = ["none", "yearly"]
EMPLOYMENT_TYPE_OPTIONS = ["heltid", "deltid", "behovsanstallning", "timanstallning", "extrajobb", "vikariat"]
YEAR_CHART_OPTIONS = ["Pie chart", "Bar overview"]
MONTH_CHART_OPTIONS = ["Activity list", "Daily bars"]
EXPENSE_CHART_OPTIONS = ["Pie chart", "Category bars"]
YEAR_SCOPE_OPTIONS = ["Selected month", "Full year"]
INCOME_AMOUNT_MODE_OPTIONS = ["Post-tax (net)", "Pre-tax (gross)"]
INCOME_TAX_TREATMENT_OPTIONS = ["Main income", "Side income (30%)"]
INCOME_AGE_GROUP_OPTIONS = ["Under 66", "66 or older"]


def amount_mode_key(label: str) -> str:
    return INCOME_MODE_GROSS if label == "Pre-tax (gross)" else INCOME_MODE_NET


def tax_treatment_key(label: str) -> str:
    return PRIMARY_INCOME if label == "Main income" else "secondary"


def age_group_key(label: str) -> str:
    return AGE_GROUP_UNDER_66 if label == "Under 66" else "66_plus"


def sek(amount: float) -> str:
    return f"{amount:,.0f} SEK".replace(",", " ")


def month_to_number(month_name: str) -> str:
    return f"{MONTH_OPTIONS.index(month_name) + 1:02d}"


def month_key(month_name: str, year: str) -> str:
    return f"{year}-{month_to_number(month_name)}"


def days_in_month(month_name: str, year: str) -> list[str]:
    month_num = MONTH_OPTIONS.index(month_name) + 1
    day_count = calendar.monthrange(int(year), month_num)[1]
    return [str(day) for day in range(1, day_count + 1)]


def next_month(month_name: str, year: str) -> tuple[str, str]:
    month_index = MONTH_OPTIONS.index(month_name)
    year_int = int(year)
    if month_index == 11:
        return MONTH_OPTIONS[0], str(year_int + 1)
    return MONTH_OPTIONS[month_index + 1], str(year_int)


def month_year_before_or_equal(start_month: str, start_year: str, end_month: str, end_year: str) -> bool:
    s = (int(start_year), MONTH_OPTIONS.index(start_month) + 1)
    e = (int(end_year), MONTH_OPTIONS.index(end_month) + 1)
    return s <= e


def control_value(control) -> str:
    return (control.value or "").strip()


def build_card(title: str, value_control: ft.Text, subtitle: str) -> ft.Container:
    return ft.Container(
        expand=True,
        padding=18,
        border_radius=22,
        bgcolor=PANEL_ALT,
        border=ft.Border.all(1, BORDER),
        content=ft.Column(
            [
                ft.Text(title, size=14, color=MUTED),
                value_control,
                ft.Text(subtitle, size=12, color=SUBTLE),
            ],
            spacing=8,
        ),
    )


def choice_button(label: str, active: bool, on_click) -> ft.Button:
    return ft.Button(
        label,
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=ACCENT if active else PANEL_ALT,
            color="#06131F" if active else TEXT,
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            shape=ft.RoundedRectangleBorder(radius=14),
        ),
    )


def section(title: str, content: ft.Control, expand: bool = False, padding: int = 18) -> ft.Container:
    return ft.Container(
        expand=expand,
        padding=padding,
        border_radius=24,
        bgcolor=PANEL,
        border=ft.Border.all(1, BORDER),
        content=ft.Column(
            [
                ft.Text(title, size=18, weight=ft.FontWeight.W_600, color=TEXT),
                ft.Divider(color=BORDER, height=14),
                content,
            ],
            spacing=0,
            expand=expand,
        ),
    )


def nav_button(label: str, icon, on_click, active: bool = False) -> ft.Button:
    return ft.Button(
        label,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=ACCENT if active else PANEL_ALT,
            color="#06131F" if active else TEXT,
            padding=18,
            shape=ft.RoundedRectangleBorder(radius=16),
        ),
    )


def main(page: ft.Page):
    init_db()

    page.title = "FutureBudget"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG
    page.padding = 0
    page.window_width = 1460
    page.window_height = 940
    page.window_min_width = 1180
    page.window_min_height = 760

    today = datetime.today()
    default_month = MONTH_OPTIONS[today.month - 1]
    default_year = str(today.year)
    default_day = str(today.day)

    current_view = {"name": "dashboard"}
    content_area = ft.Container(expand=True)
    nav_row = ft.Row(spacing=12, scroll=ft.ScrollMode.AUTO)

    # Summary texts
    income_value = ft.Text("0 SEK", size=28, weight=ft.FontWeight.W_700, color=TEXT)
    expenses_value = ft.Text("0 SEK", size=28, weight=ft.FontWeight.W_700, color="#FCA5A5")
    savings_value = ft.Text("0 SEK", size=28, weight=ft.FontWeight.W_700, color="#C084FC")
    leftover_value = ft.Text("0 SEK", size=28, weight=ft.FontWeight.W_700, color="#86EFAC")
    planned_total_value = ft.Text("0 SEK", size=24, weight=ft.FontWeight.W_700, color="#FCD34D")
    reserve_value = ft.Text("0 SEK", size=20, weight=ft.FontWeight.W_700, color="#FCD34D")
    expected_money_title = ft.Text("Expected saved by period end", color=MUTED, size=13)
    expected_money_value = ft.Text("0 SEK", size=24, weight=ft.FontWeight.W_700, color=TEXT)
    expected_money_detail = ft.Text("", color=SUBTLE, size=12)

    # Containers updated dynamically
    tx_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    planned_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    month_view_text = ft.Text("", color=MUTED, size=14)
    delete_series_checkbox = ft.Checkbox(
        label="Delete recurring series",
        value=False,
        active_color=ACCENT,
        check_color="#06131F",
    )
    delete_planned_series_checkbox = ft.Checkbox(
        label="Delete yearly obligation series",
        value=False,
        active_color=ACCENT,
        check_color="#06131F",
    )
    yearly_chart_type = ft.Dropdown(
        label="Yearly chart",
        value="Pie chart",
        width=170,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(value) for value in YEAR_CHART_OPTIONS],
    )
    monthly_chart_type = ft.Dropdown(
        label="Month chart",
        value="Activity list",
        width=170,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(value) for value in MONTH_CHART_OPTIONS],
    )
    expense_chart_type = ft.Dropdown(
        label="Expense chart",
        value="Pie chart",
        width=170,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(value) for value in EXPENSE_CHART_OPTIONS],
    )
    yearly_scope_type = ft.Dropdown(
        label="Yearly flow scope",
        value="Full year",
        width=150,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(value) for value in YEAR_SCOPE_OPTIONS],
    )

    # Filters
    filter_month = ft.Dropdown(
        label="View month",
        value=default_month,
        width=170,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(month) for month in MONTH_OPTIONS],
    )
    filter_year = ft.Dropdown(
        label="View year",
        value=default_year,
        width=120,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(year) for year in YEAR_OPTIONS],
    )
    entries_apply_button = ft.Button(
        "Apply",
        style=ft.ButtonStyle(
            bgcolor="#13233C",
            color=TEXT,
            padding=16,
            shape=ft.RoundedRectangleBorder(radius=14),
        ),
    )
    dashboard_month = ft.Dropdown(
        label="Dashboard month",
        value=default_month,
        width=170,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(month) for month in MONTH_OPTIONS],
    )
    dashboard_year = ft.Dropdown(
        label="Dashboard year",
        value=default_year,
        width=140,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(year) for year in YEAR_OPTIONS],
    )
    dashboard_apply_button = ft.Button(
        "Apply",
        style=ft.ButtonStyle(
            bgcolor="#13233C",
            color=TEXT,
            padding=16,
            shape=ft.RoundedRectangleBorder(radius=14),
        ),
    )

    # Transaction entry
    entry_type = ft.Dropdown(
        label="Type",
        value="expense",
        width=150,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(option) for option in TYPE_OPTIONS],
    )
    entry_category = ft.TextField(
        label="Category",
        hint_text="Rent, Salary, Groceries...",
        width=220,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
    )
    entry_amount = ft.TextField(
        label="Amount",
        hint_text="0",
        width=160,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    entry_note = ft.TextField(
        label="Note",
        hint_text="Optional note",
        expand=True,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
    )
    entry_month = ft.Dropdown(
        label="Month",
        value=default_month,
        width=170,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(month) for month in MONTH_OPTIONS],
    )
    entry_year = ft.Dropdown(
        label="Year",
        value=default_year,
        width=120,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(year) for year in YEAR_OPTIONS],
    )
    entry_day = ft.Dropdown(
        label="Day",
        value=default_day,
        width=110,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(day) for day in days_in_month(default_month, default_year)],
    )

    recurring_switch = ft.Switch(label="Repeat monthly", value=False, active_color=ACCENT)
    recurring_until_month = ft.Dropdown(
        label="Repeat until month",
        value=default_month,
        width=180,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        disabled=True,
        options=[ft.dropdown.Option(month) for month in MONTH_OPTIONS],
    )
    recurring_until_year = ft.Dropdown(
        label="Repeat until year",
        value=default_year,
        width=140,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        disabled=True,
        options=[ft.dropdown.Option(year) for year in YEAR_OPTIONS],
    )
    recurring_preview = ft.Column(spacing=8)

    # Income details
    income_source_type = ft.Dropdown(
        label="Income source",
        value="job",
        width=170,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[
            ft.dropdown.Option("job"),
            ft.dropdown.Option("freelance"),
            ft.dropdown.Option("benefit"),
            ft.dropdown.Option("gift"),
            ft.dropdown.Option("other"),
        ],
    )
    income_amount_mode = ft.Dropdown(
        label="Amount type",
        value="Post-tax (net)",
        width=170,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(value) for value in INCOME_AMOUNT_MODE_OPTIONS],
    )
    employment_type = ft.Dropdown(
        label="Employment type",
        value="heltid",
        width=190,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(option) for option in EMPLOYMENT_TYPE_OPTIONS],
    )
    income_tax_treatment = ft.Dropdown(
        label="Tax treatment",
        value="Main income",
        width=190,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(value) for value in INCOME_TAX_TREATMENT_OPTIONS],
    )
    income_tax_table = ft.Dropdown(
        label="Skattetabell",
        value="32",
        width=140,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(table) for table in get_tax_table_choices()],
    )
    income_age_group = ft.Dropdown(
        label="Age group",
        value="Under 66",
        width=170,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(value) for value in INCOME_AGE_GROUP_OPTIONS],
    )
    refresh_tax_button = ft.Button(
        "Refresh tax data",
        icon=ft.Icons.SYNC,
        style=ft.ButtonStyle(
            bgcolor="#13233C",
            color=TEXT,
            padding=16,
            shape=ft.RoundedRectangleBorder(radius=14),
        ),
    )
    tax_preview = ft.Text("Net after tax: 0 SEK", color=MUTED, size=12)
    income_extra_box = ft.Container(
        visible=True,
        padding=16,
        border_radius=18,
        bgcolor=PANEL_ALT,
        border=ft.Border.all(1, BORDER),
        content=ft.Column(
            [
                ft.Row([income_source_type, income_amount_mode, employment_type], wrap=True, spacing=12),
                ft.Row([income_tax_treatment, income_tax_table, income_age_group], wrap=True, spacing=12),
                ft.Row([refresh_tax_button], spacing=12),
                ft.Text(
                    "For salary, choose pre-tax or post-tax input, then select tax table and income type to preview the estimate.",
                    color=SUBTLE,
                    size=12,
                ),
                tax_preview,
            ],
            spacing=10,
        ),
    )

    # Planned obligations
    planned_title = ft.TextField(
        label="Planned payment title",
        hint_text="Car tax, dental, service...",
        width=240,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
    )
    planned_category = ft.TextField(
        label="Planned category",
        hint_text="Tax, maintenance, health...",
        width=220,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
    )
    planned_amount = ft.TextField(
        label="Planned amount",
        hint_text="0",
        width=150,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    planned_note = ft.TextField(
        label="Planned note",
        hint_text="Optional note",
        expand=True,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
    )
    planned_month = ft.Dropdown(
        label="Due month",
        value=default_month,
        width=170,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(month) for month in MONTH_OPTIONS],
    )
    planned_year = ft.Dropdown(
        label="Due year",
        value=default_year,
        width=120,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(year) for year in YEAR_OPTIONS],
    )
    planned_day = ft.Dropdown(
        label="Due day",
        value=default_day,
        width=110,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(day) for day in days_in_month(default_month, default_year)],
    )
    planned_status = ft.Dropdown(
        label="Status",
        value="planned",
        width=140,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(x) for x in PLANNED_STATUS_OPTIONS],
    )
    planned_recurrence = ft.Dropdown(
        label="Recurrence",
        value="none",
        width=140,
        bgcolor=PANEL_ALT,
        border_color=BORDER,
        color=TEXT,
        options=[ft.dropdown.Option(x) for x in PLANNED_RECURRENCE_OPTIONS],
    )

    def selected_month_key() -> str:
        return month_key(filter_month.value, filter_year.value)

    def selected_dashboard_month_key() -> str:
        return month_key(dashboard_month.value, dashboard_year.value)

    def set_selected_period(month_name: str, year_value: str):
        filter_month.value = month_name
        filter_year.value = year_value

    def set_dashboard_period(month_name: str, year_value: str):
        dashboard_month.value = month_name
        dashboard_year.value = year_value

    def show_message(message: str):
        page.snack_bar = ft.SnackBar(ft.Text(message))
        page.snack_bar.open = True
        page.update()

    def update_day_dropdown(_=None):
        valid_days = days_in_month(entry_month.value, entry_year.value)
        entry_day.options = [ft.dropdown.Option(day) for day in valid_days]
        if entry_day.value not in valid_days:
            entry_day.value = valid_days[0]
        update_recurring_preview()
        page.update()

    def update_planned_day_dropdown(_=None):
        valid_days = days_in_month(planned_month.value, planned_year.value)
        planned_day.options = [ft.dropdown.Option(day) for day in valid_days]
        if planned_day.value not in valid_days:
            planned_day.value = valid_days[0]
        page.update()

    def toggle_recurring(_=None):
        recurring_until_month.disabled = not recurring_switch.value
        recurring_until_year.disabled = not recurring_switch.value
        update_recurring_preview()
        page.update()

    def update_recurring_preview(_=None):
        recurring_preview.controls.clear()

        if not recurring_switch.value:
            recurring_preview.controls.append(
                ft.Text("Recurring is off. Only one entry will be added.", color=SUBTLE, size=12)
            )
            return

        start_month = entry_month.value
        start_year = entry_year.value
        end_month = recurring_until_month.value
        end_year = recurring_until_year.value

        if not month_year_before_or_equal(start_month, start_year, end_month, end_year):
            recurring_preview.controls.append(
                ft.Text("Repeat-until date must be the same month or later.", color="#FCA5A5", size=12)
            )
            return

        preview_items = []
        cur_month = start_month
        cur_year = start_year

        while True:
            preview_items.append(f"{cur_month} {cur_year}")
            if cur_month == end_month and cur_year == end_year:
                break
            cur_month, cur_year = next_month(cur_month, cur_year)
            if len(preview_items) > 120:
                break

        recurring_preview.controls.append(
            ft.Text(f"This will create {len(preview_items)} monthly entries:", color=MUTED, size=12)
        )
        recurring_preview.controls.append(
            ft.Container(
                padding=12,
                border_radius=16,
                bgcolor=PANEL_ALT,
                border=ft.Border.all(1, BORDER),
                content=ft.Text(
                    "  •  ".join(preview_items[:8]) + ("  •  ..." if len(preview_items) > 8 else ""),
                    color=TEXT,
                    size=12,
                ),
            )
        )

    def update_tax_preview(_=None):
        if entry_type.value != "income":
            tax_preview.value = "Net after tax: 0 SEK"
            page.update()
            return

        if income_source_type.value != "job":
            tax_preview.value = "For non-job income, Amount is treated as received income."
            page.update()
            return

        try:
            amount = float(control_value(entry_amount).replace(",", "."))
        except ValueError:
            tax_preview.value = "Enter a valid salary amount."
            page.update()
            return

        selected_amount_mode = amount_mode_key(income_amount_mode.value)
        selected_tax_treatment = tax_treatment_key(income_tax_treatment.value)
        selected_age_group = age_group_key(income_age_group.value)

        if amount <= 0:
            if selected_amount_mode == INCOME_MODE_GROSS:
                tax_preview.value = "Enter a gross salary amount to estimate tax."
            else:
                tax_preview.value = "Enter a net salary amount to estimate gross income."
            page.update()
            return

        try:
            estimate = estimate_swedish_salary(
                amount=amount,
                amount_mode=selected_amount_mode,
                table_number=int(income_tax_table.value),
                age_group=selected_age_group,
                tax_treatment=selected_tax_treatment,
            )
            tax_preview.value = (
                f"Gross: {sek(estimate['gross_amount'])} | "
                f"Tax: {sek(estimate['tax_amount'])} | "
                f"Net: {sek(estimate['net_amount'])} | "
                f"Source: {estimate['source']}"
            )
        except Exception as exc:
            tax_preview.value = f"Tax lookup unavailable: {exc}"
        page.update()

    def update_amount_field_mode():
        if entry_type.value != "income":
            entry_amount.label = "Amount"
            entry_amount.hint_text = "0"
            entry_amount.disabled = False
            return

        if income_source_type.value == "job":
            entry_amount.label = "Gross salary" if amount_mode_key(income_amount_mode.value) == INCOME_MODE_GROSS else "Net salary"
            entry_amount.hint_text = (
                "Before tax deduction" if amount_mode_key(income_amount_mode.value) == INCOME_MODE_GROSS else "Amount after tax"
            )
            entry_amount.disabled = False
            return

        entry_amount.label = "Received amount"
        entry_amount.hint_text = "Net amount received"
        entry_amount.disabled = False

    def update_income_fields(_=None):
        is_income = entry_type.value == "income"
        update_amount_field_mode()
        if is_income and income_source_type.value == "job":
            update_tax_preview()
        elif is_income:
            tax_preview.value = "Tax estimate is only used for salary/job income."
        else:
            tax_preview.value = "Switch type to income to use the salary tax estimate."
        page.update()

    def handle_income_source_change(_=None):
        update_amount_field_mode()
        update_tax_preview()

    def refresh_tax_data(_=None):
        try:
            path = refresh_swedish_tax_cache()
            show_message(f"Refreshed Skatteverket tax data from {path}.")
        except Exception as exc:
            show_message(f"Could not refresh tax data: {exc}")
        update_tax_preview()

    entry_month.on_change = update_day_dropdown
    entry_year.on_change = update_day_dropdown
    planned_month.on_change = update_planned_day_dropdown
    planned_year.on_change = update_planned_day_dropdown
    recurring_switch.on_change = toggle_recurring
    recurring_until_month.on_change = update_recurring_preview
    recurring_until_year.on_change = update_recurring_preview
    entry_type.on_change = update_income_fields
    income_source_type.on_change = handle_income_source_change
    income_amount_mode.on_change = handle_income_source_change
    income_tax_treatment.on_change = update_tax_preview
    income_tax_table.on_change = update_tax_preview
    income_age_group.on_change = update_tax_preview
    employment_type.on_change = update_tax_preview
    entry_amount.on_change = update_tax_preview
    refresh_tax_button.on_click = refresh_tax_data

    def reset_transaction_form():
        entry_type.value = "expense"
        entry_category.value = ""
        entry_amount.value = ""
        entry_note.value = ""
        entry_month.value = filter_month.value
        entry_year.value = filter_year.value
        entry_day.value = "1"
        recurring_switch.value = False
        recurring_until_month.value = entry_month.value
        recurring_until_year.value = entry_year.value
        recurring_until_month.disabled = True
        recurring_until_year.disabled = True
        income_source_type.value = "job"
        income_amount_mode.value = "Post-tax (net)"
        income_tax_treatment.value = "Main income"
        income_tax_table.value = "32"
        income_age_group.value = "Under 66"
        employment_type.value = "heltid"
        update_day_dropdown()
        update_recurring_preview()
        update_income_fields()

    def reset_planned_form():
        planned_title.value = ""
        planned_category.value = ""
        planned_amount.value = ""
        planned_note.value = ""
        planned_month.value = filter_month.value
        planned_year.value = filter_year.value
        planned_day.value = "1"
        planned_status.value = "planned"
        planned_recurrence.value = "none"
        update_planned_day_dropdown()

    def refresh_summary():
        summary = get_month_summary(selected_dashboard_month_key())
        income_value.value = sek(summary["income"])
        expenses_value.value = sek(summary["expenses"])
        savings_value.value = sek(summary["savings_balance"])
        leftover_value.value = sek(summary["leftover"])
        leftover_value.color = "#86EFAC" if summary["leftover"] >= 0 else "#FCA5A5"

        planned_total = get_planned_total_for_year(dashboard_year.value)
        planned_total_value.value = sek(planned_total)
        reserve_value.value = sek(planned_total / 12 if planned_total else 0)
        if yearly_scope_type.value == "Selected month":
            flow = get_flow_breakdown_for_month(selected_dashboard_month_key())
            expected_money_title.value = f"Expected saved after {dashboard_month.value} {dashboard_year.value}"
        else:
            flow = get_flow_breakdown_for_year(dashboard_year.value)
            expected_money_title.value = f"Expected saved by end of {dashboard_year.value}"
        retained = flow["remaining_balance"]
        expected_money_value.value = sek(retained)
        pct = 0 if flow["total_available"] <= 0 else round((retained / flow["total_available"]) * 100)
        expected_money_detail.value = (
            f"Total available {sek(flow['total_available'])} • Retention {pct}%"
            if flow["total_available"] > 0
            else "No available money in this period yet."
        )

        month_view_text.value = f"Showing entries for {filter_month.value} {filter_year.value}"

    def refresh_transactions():
        rows = get_transactions_for_month(selected_month_key())
        tx_list.controls.clear()

        if not rows:
            tx_list.controls.append(
                ft.Container(
                    padding=18,
                    border_radius=18,
                    bgcolor=PANEL_ALT,
                    border=ft.Border.all(1, BORDER),
                    content=ft.Text("No entries for this month yet.", color=SUBTLE),
                )
            )
            return

        for tx_id, tx_date, tx_type, category, amount, note, series_id, source_type, gross_amount, tax_rate, tax_amount, net_amount in rows:
            if tx_type == "income":
                amount_color = "#86EFAC"
                sign = "+"
                chip_color = "#123525"
            elif tx_type == "saving":
                amount_color = "#C084FC"
                sign = "-"
                chip_color = "#2A1841"
            else:
                amount_color = "#FCA5A5"
                sign = "-"
                chip_color = "#3A181C"

            secondary = tx_date
            if note:
                secondary += f"   {note}"
            if tx_type == "income" and source_type:
                secondary += f"   [{source_type}]"

            tx_list.controls.append(
                ft.Container(
                    padding=16,
                    border_radius=18,
                    bgcolor=PANEL_ALT,
                    border=ft.Border.all(1, BORDER),
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Text(category, color=TEXT, weight=ft.FontWeight.W_700, size=15),
                                            ft.Container(
                                                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                                border_radius=999,
                                                bgcolor=chip_color,
                                                content=ft.Text(tx_type, color=MUTED, size=11),
                                            ),
                                        ],
                                        spacing=10,
                                    ),
                                    ft.Text(secondary, color=SUBTLE, size=12),
                                ],
                                spacing=4,
                                expand=True,
                            ),
                            ft.Text(f"{sign} {sek(amount)}", color=amount_color, weight=ft.FontWeight.W_700),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color="#F87171",
                                on_click=lambda e,
                                tx_id=tx_id,
                                tx_date=tx_date,
                                tx_type=tx_type,
                                category=category,
                                amount=amount,
                                note=note,
                                series_id=series_id,
                                source_type=source_type,
                                gross_amount=gross_amount,
                                tax_rate=tax_rate,
                                tax_amount=tax_amount,
                                net_amount=net_amount: handle_delete_transaction(
                                    tx_id,
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
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )

    def refresh_planned_list():
        rows = get_planned_expenses_for_month(selected_month_key())
        planned_list.controls.clear()

        if not rows:
            planned_list.controls.append(
                ft.Container(
                    padding=18,
                    border_radius=18,
                    bgcolor=PANEL_ALT,
                    border=ft.Border.all(1, BORDER),
                    content=ft.Text("No planned obligations for this month yet.", color=SUBTLE),
                )
            )
            return

        for expense_id, due_date, title, category, amount, note, series_id, status, recurrence in rows:
            status_color = {
                "planned": "#FCD34D",
                "paid": "#86EFAC",
                "skipped": "#FCA5A5",
            }.get(status, "#CBD5E1")

            action_controls: list[ft.Control] = []
            if status != "paid":
                action_controls.append(
                    ft.Button(
                        "Mark paid",
                        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                        on_click=lambda e, expense_id=expense_id, due_date=due_date, title=title, category=category, amount=amount, note=note: handle_mark_planned_paid(
                            expense_id,
                            due_date,
                            title,
                            category,
                            amount,
                            note,
                        ),
                        style=ft.ButtonStyle(
                            bgcolor="#123525",
                            color="#DCFCE7",
                            padding=ft.padding.symmetric(horizontal=14, vertical=12),
                            shape=ft.RoundedRectangleBorder(radius=14),
                        ),
                    )
                )
            else:
                action_controls.append(
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        border_radius=14,
                        bgcolor="#123525",
                        content=ft.Text("Already paid", color="#DCFCE7", size=12),
                    )
                )

            action_controls.append(
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color="#F87171",
                    on_click=lambda e, expense_id=expense_id, series_id=series_id: handle_delete_planned(expense_id, series_id),
                )
            )

            planned_list.controls.append(
                ft.Container(
                    padding=16,
                    border_radius=18,
                    bgcolor=PANEL_ALT,
                    border=ft.Border.all(1, BORDER),
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Text(title, color=TEXT, weight=ft.FontWeight.W_700, size=15),
                                            ft.Container(
                                                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                                border_radius=999,
                                                bgcolor="#1A2337",
                                                content=ft.Text(status, color=status_color, size=11),
                                            ),
                                        ],
                                        spacing=10,
                                    ),
                                    ft.Text(
                                        f"{due_date}   {category}   {recurrence}" + (f"   {note}" if note else ""),
                                        color=SUBTLE,
                                        size=12,
                                    ),
                                ],
                                spacing=4,
                                expand=True,
                            ),
                            ft.Text(sek(amount), color="#FCD34D", weight=ft.FontWeight.W_700),
                            ft.Row(
                                action_controls,
                                spacing=8,
                                wrap=True,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )

    def build_dashboard_yearly_chart() -> ft.Control:
        if yearly_scope_type.value == "Selected month":
            flow = get_flow_breakdown_for_month(selected_dashboard_month_key())
            return (
                build_flow_breakdown_chart(
                    total_available=flow["total_available"],
                    opening_balance=flow["opening_balance"],
                    income_total=flow["income_total"],
                    allocation_rows=flow["allocation_rows"],
                    remaining_balance=flow["remaining_balance"],
                    period_label=f"{dashboard_month.value} {dashboard_year.value}",
                    show_carry_over=True,
                )
                if yearly_chart_type.value == "Pie chart"
                else build_daily_bar_overview(get_daily_series(selected_dashboard_month_key()))
            )

        monthly_series = get_monthly_series(dashboard_year.value)
        yearly_flow = get_flow_breakdown_for_year(dashboard_year.value)
        return (
            build_flow_breakdown_chart(
                total_available=yearly_flow["total_available"],
                opening_balance=yearly_flow["opening_balance"],
                income_total=yearly_flow["income_total"],
                allocation_rows=yearly_flow["allocation_rows"],
                remaining_balance=yearly_flow["remaining_balance"],
                period_label=dashboard_year.value,
                show_carry_over=False,
            )
            if yearly_chart_type.value == "Pie chart"
            else build_yearly_bar_overview(monthly_series)
        )

    def build_dashboard_month_chart() -> ft.Control:
        daily_series = get_daily_series(selected_dashboard_month_key())
        return (
            build_daily_activity_list(daily_series)
            if monthly_chart_type.value == "Activity list"
            else build_daily_bar_overview(daily_series)
        )

    def build_dashboard_expense_chart() -> ft.Control:
        flow = get_flow_breakdown_for_month(selected_dashboard_month_key())
        expense_totals = get_expense_category_totals(selected_dashboard_month_key())
        allocation_rows = list(flow["allocation_rows"])
        if flow["remaining_balance"] > 0:
            allocation_rows.append(("Saved after costs", flow["remaining_balance"]))
        elif flow["remaining_balance"] < 0:
            allocation_rows.append(("Over budget", abs(flow["remaining_balance"])))
        return (
            build_expense_pie_chart(allocation_rows)
            if expense_chart_type.value == "Pie chart"
            else build_expense_category_bars(expense_totals)
        )

    def set_chart_type(group: str, value: str):
        if group == "yearly":
            yearly_chart_type.value = value
        elif group == "yearly_scope":
            yearly_scope_type.value = value
        elif group == "monthly":
            monthly_chart_type.value = value
        else:
            expense_chart_type.value = value

        current_view["name"] = "dashboard"
        content_area.content = dashboard_view()
        page.update()

    def refresh_all(_=None):
        refresh_summary()
        refresh_transactions()
        refresh_planned_list()
        render_view(current_view["name"])
        page.update()

    def handle_delete_transaction(
        tx_id: int,
        tx_date: str,
        tx_type: str,
        category: str,
        amount: float,
        note: str,
        series_id: str,
        source_type: str,
        gross_amount: float,
        tax_rate: float,
        tax_amount: float,
        net_amount: float,
    ):
        if delete_series_checkbox.value:
            if series_id:
                deleted = delete_transaction_series_by_id(series_id)
            else:
                deleted = delete_transaction_series(
                    tx_date=tx_date,
                    tx_type=tx_type,
                    category=category,
                    amount=amount,
                    note=note,
                    source_type=source_type,
                    gross_amount=gross_amount,
                    tax_rate=tax_rate,
                    tax_amount=tax_amount,
                    net_amount=net_amount,
                )
            refresh_all()
            show_message(f"Deleted {deleted} entries in the recurring series.")
            return

        delete_transaction(tx_id)
        refresh_all()
        show_message("Entry deleted.")

    def handle_delete_planned(expense_id: int, series_id: str):
        if delete_planned_series_checkbox.value and series_id:
            deleted = delete_planned_expense_series_by_id(series_id)
            refresh_all()
            show_message(f"Deleted {deleted} planned obligations in the yearly series.")
            return

        delete_planned_expense(expense_id)
        refresh_all()
        show_message("Planned expense deleted.")

    def handle_mark_planned_paid(
        expense_id: int,
        due_date: str,
        title: str,
        category: str,
        amount: float,
        note: str,
    ):
        note_text = f"Paid planned obligation: {title}"
        if note:
            note_text += f" | {note}"

        add_transaction(
            tx_date=due_date,
            tx_type="expense",
            category=category,
            amount=amount,
            note=note_text,
        )
        update_planned_expense_status(expense_id, "paid")
        refresh_all()
        show_message("Planned obligation marked as paid and added to expenses.")

    def handle_delete_month(_=None):
        rows = get_transactions_for_month(selected_month_key())
        if not rows:
            show_message("There are no entries in this month to delete.")
            return

        if delete_series_checkbox.value:
            deleted_total = 0
            deleted_series_ids: set[str] = set()

            for tx_id, tx_date, tx_type, category, amount, note, series_id, source_type, gross_amount, tax_rate, tax_amount, net_amount in rows:
                if series_id:
                    if series_id in deleted_series_ids:
                        continue
                    deleted_series_ids.add(series_id)
                    deleted_total += delete_transaction_series_by_id(series_id)
                else:
                    deleted_total += delete_transaction_series(
                        tx_date=tx_date,
                        tx_type=tx_type,
                        category=category,
                        amount=amount,
                        note=note,
                        source_type=source_type,
                        gross_amount=gross_amount,
                        tax_rate=tax_rate,
                        tax_amount=tax_amount,
                        net_amount=net_amount,
                    )

            refresh_all()
            show_message(f"Deleted {deleted_total} entries tied to {filter_month.value} {filter_year.value}.")
            return

        delete_transactions_for_month(selected_month_key())
        refresh_all()
        show_message(f"Deleted all entries for {filter_month.value} {filter_year.value}.")

    def handle_add_transaction(_):
        try:
            category = control_value(entry_category)
            amount_raw = control_value(entry_amount).replace(",", ".")
            note = control_value(entry_note)

            if not category:
                show_message("Category is required.")
                return

            if not amount_raw and entry_type.value != "income":
                show_message("Amount is required.")
                return

            try:
                amount = float(amount_raw) if amount_raw else 0
            except ValueError:
                show_message("Amount must be a valid number.")
                return

            if entry_type.value != "income" and amount <= 0:
                show_message("Amount must be greater than 0.")
                return

            source_type = ""
            gross_amount = 0
            tax_rate = 0
            tax_amount = 0
            net_amount = 0
            series_id = str(uuid.uuid4()) if recurring_switch.value else ""

            if entry_type.value == "income":
                source_type = income_source_type.value

                if source_type == "job":
                    if amount <= 0:
                        show_message("Salary amount must be greater than 0.")
                        return

                    selected_amount_mode = amount_mode_key(income_amount_mode.value)
                    selected_tax_treatment = tax_treatment_key(income_tax_treatment.value)
                    selected_age_group = age_group_key(income_age_group.value)

                    estimate = estimate_swedish_salary(
                        amount=amount,
                        amount_mode=selected_amount_mode,
                        table_number=int(income_tax_table.value),
                        age_group=selected_age_group,
                        tax_treatment=selected_tax_treatment,
                    )
                    gross_amount = estimate["gross_amount"]
                    tax_amount = estimate["tax_amount"]
                    net_amount = estimate["net_amount"]
                    tax_rate = estimate["tax_rate_percent"]
                    amount = net_amount
                    source_type = f"job/{employment_type.value}"
                else:
                    if amount <= 0:
                        show_message("Amount must be greater than 0.")
                        return
                    net_amount = amount

            start_month = entry_month.value
            start_year = entry_year.value
            start_day = int(entry_day.value)

            def insert_one(tx_date_value: str):
                add_transaction(
                    tx_date=tx_date_value,
                    tx_type=entry_type.value,
                    category=category,
                    amount=amount,
                    note=note,
                    series_id=series_id,
                    source_type=source_type,
                    gross_amount=gross_amount,
                    tax_rate=tax_rate,
                    tax_amount=tax_amount,
                    net_amount=net_amount,
                )

            set_selected_period(start_month, start_year)

            if recurring_switch.value:
                end_month = recurring_until_month.value
                end_year = recurring_until_year.value

                if not month_year_before_or_equal(start_month, start_year, end_month, end_year):
                    show_message("Repeat-until date must be the same month or later.")
                    return

                cur_month = start_month
                cur_year = start_year
                created = 0

                while True:
                    valid_days = days_in_month(cur_month, cur_year)
                    use_day = min(start_day, len(valid_days))
                    tx_date_value = f"{cur_year}-{month_to_number(cur_month)}-{use_day:02d}"
                    insert_one(tx_date_value)
                    created += 1

                    if cur_month == end_month and cur_year == end_year:
                        break

                    cur_month, cur_year = next_month(cur_month, cur_year)

                    if created > 120:
                        break

                show_message(f"Added {created} recurring entries.")
            else:
                tx_date_value = f"{start_year}-{month_to_number(start_month)}-{start_day:02d}"
                insert_one(tx_date_value)
                show_message("Entry added.")

            refresh_all()
            reset_transaction_form()
        except Exception as exc:
            print("ERROR in handle_add_transaction:")
            traceback.print_exc()
            show_message(f"Add entry failed: {exc}")

    def handle_add_planned(_):
        title = planned_title.value.strip()
        category = planned_category.value.strip()
        amount_raw = planned_amount.value.strip().replace(",", ".")
        note = planned_note.value.strip()

        if not title:
            show_message("Planned payment title is required.")
            return
        if not category:
            show_message("Planned category is required.")
            return
        if not amount_raw:
            show_message("Planned amount is required.")
            return

        try:
            amount = float(amount_raw)
        except ValueError:
            show_message("Planned amount must be a valid number.")
            return

        if amount <= 0:
            show_message("Planned amount must be greater than 0.")
            return

        due_date = f"{planned_year.value}-{month_to_number(planned_month.value)}-{int(planned_day.value):02d}"

        planned_series_id = str(uuid.uuid4()) if planned_recurrence.value == "yearly" else ""

        def insert_planned(one_due_date: str):
            add_planned_expense(
                due_date=one_due_date,
                title=title,
                category=category,
                amount=amount,
                note=note,
                series_id=planned_series_id,
                status=planned_status.value,
                recurrence=planned_recurrence.value,
            )

        if planned_recurrence.value == "yearly":
            start_year = int(planned_year.value)
            end_year = int(YEAR_OPTIONS[-1])
            created = 0
            for year in range(start_year, end_year + 1):
                one_due_date = f"{year}-{month_to_number(planned_month.value)}-{int(planned_day.value):02d}"
                insert_planned(one_due_date)
                created += 1
            refresh_all()
            reset_planned_form()
            show_message(f"Added {created} yearly planned obligations.")
            return

        insert_planned(due_date)

        refresh_all()
        reset_planned_form()
        show_message("Planned obligation added.")

    def handle_entries_period_change(_=None):
        refresh_transactions()
        refresh_planned_list()
        month_view_text.value = f"Showing entries for {filter_month.value} {filter_year.value}"
        if current_view["name"] == "entries":
            content_area.content = entries_view()
        page.update()

    def handle_dashboard_period_change(_=None):
        refresh_summary()
        if current_view["name"] == "dashboard":
            content_area.content = dashboard_view()
        page.update()

    filter_month.on_change = handle_entries_period_change
    filter_year.on_change = handle_entries_period_change
    entries_apply_button.on_click = handle_entries_period_change
    dashboard_month.on_change = handle_dashboard_period_change
    dashboard_year.on_change = handle_dashboard_period_change
    dashboard_apply_button.on_click = handle_dashboard_period_change

    add_transaction_button = ft.Button(
        "Add entry",
        icon=ft.Icons.ADD,
        on_click=handle_add_transaction,
        style=ft.ButtonStyle(
            bgcolor="#13233C",
            color=TEXT,
            padding=20,
            shape=ft.RoundedRectangleBorder(radius=16),
        ),
    )

    delete_month_button = ft.Button(
        "Delete whole month",
        icon=ft.Icons.DELETE_SWEEP_ROUNDED,
        on_click=handle_delete_month,
        style=ft.ButtonStyle(
            bgcolor="#2A1519",
            color="#FCA5A5",
            padding=20,
            shape=ft.RoundedRectangleBorder(radius=16),
        ),
    )

    add_planned_button = ft.Button(
        "Add planned obligation",
        icon=ft.Icons.ADD,
        on_click=handle_add_planned,
        style=ft.ButtonStyle(
            bgcolor="#13233C",
            color=TEXT,
            padding=20,
            shape=ft.RoundedRectangleBorder(radius=16),
        ),
    )

    summary_cards = ft.Row(
        [
            build_card("Income", income_value, "Total monthly income"),
            build_card("Expenses", expenses_value, "Total monthly expenses"),
            build_card("Savings", savings_value, "Rolling reserve balance"),
            build_card("Left over", leftover_value, "Current month leftover after savings"),
        ],
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
    )

    def dashboard_view():
        yearly_chart_height = 430 if yearly_chart_type.value == "Pie chart" else 300
        return ft.Container(
            expand=True,
            padding=12,
            content=ft.Column(
                [
                    summary_cards,
                    ft.Container(height=18),
                    ft.Row(
                        [
                            ft.Row([dashboard_month, dashboard_year, dashboard_apply_button], spacing=12, wrap=True),
                            ft.Text(
                                f"Dashboard totals and month charts for {dashboard_month.value} {dashboard_year.value}",
                                color=MUTED,
                                size=13,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        wrap=True,
                    ),
                    ft.Container(height=18),
                    ft.Row(
                        [
                            ft.Container(
                                expand=True,
                                content=section(
                                    "Yearly Flow",
                                    ft.Column(
                                        [
                                            ft.Text("Running balance over time", color=SUBTLE, size=12),
                                            ft.Text(
                                                "Pie view shows expected money for the period, then breaks it down into carry-over, income, expense and planned slices, plus what remains saved.",
                                                color=MUTED,
                                                size=12,
                                            ),
                                            ft.Container(height=8),
                                            ft.Row(
                                                [
                                                    ft.Container(
                                                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                                                        border_radius=16,
                                                        bgcolor=PANEL_ALT,
                                                        border=ft.Border.all(1, BORDER),
                                                        content=ft.Column(
                                                            [
                                                                ft.Text("Show this chart for", color=MUTED, size=11),
                                                                ft.Row(
                                                                    [
                                                                        choice_button(
                                                                            "Selected month",
                                                                            yearly_scope_type.value == "Selected month",
                                                                            lambda e: set_chart_type("yearly_scope", "Selected month"),
                                                                        ),
                                                                        choice_button(
                                                                            "Full year",
                                                                            yearly_scope_type.value == "Full year",
                                                                            lambda e: set_chart_type("yearly_scope", "Full year"),
                                                                        ),
                                                                    ],
                                                                    wrap=True,
                                                                    spacing=10,
                                                                ),
                                                            ],
                                                            spacing=8,
                                                        ),
                                                    ),
                                                    choice_button(
                                                        "Pie chart",
                                                        yearly_chart_type.value == "Pie chart",
                                                        lambda e: set_chart_type("yearly", "Pie chart"),
                                                    ),
                                                    choice_button(
                                                        "Bar overview",
                                                        yearly_chart_type.value == "Bar overview",
                                                        lambda e: set_chart_type("yearly", "Bar overview"),
                                                    ),
                                                ],
                                                wrap=True,
                                                spacing=10,
                                            ),
                                            ft.Container(height=8),
                                            ft.Container(height=yearly_chart_height, content=build_dashboard_yearly_chart()),
                                        ],
                                        spacing=0,
                                    ),
                                ),
                            ),
                            ft.Container(width=18),
                            ft.Container(
                                width=320,
                                content=section(
                                    "Yearly Planned Reserve",
                                    ft.Column(
                                        [
                                            expected_money_title,
                                            expected_money_value,
                                            expected_money_detail,
                                            ft.Container(height=10),
                                            ft.Text("Planned obligations total", color=MUTED, size=13),
                                            planned_total_value,
                                            ft.Container(height=10),
                                            ft.Text("Monthly reserve target", color=MUTED, size=13),
                                            reserve_value,
                                        ],
                                        spacing=4,
                                    ),
                                ),
                            ),
                        ]
                    ),
                    ft.Container(height=18),
                    ft.Row(
                        [
                            ft.Container(
                                expand=True,
                                content=section(
                                    "Current Month Trend",
                                    ft.Column(
                                        [
                                            ft.Text("Transaction days inside selected month", color=SUBTLE, size=12),
                                            ft.Text(
                                                f"Showing day-by-day activity for {dashboard_month.value} {dashboard_year.value}",
                                                color=MUTED,
                                                size=12,
                                            ),
                                            ft.Container(height=8),
                                            ft.Row(
                                                [
                                                    choice_button(
                                                        "Activity list",
                                                        monthly_chart_type.value == "Activity list",
                                                        lambda e: set_chart_type("monthly", "Activity list"),
                                                    ),
                                                    choice_button(
                                                        "Daily bars",
                                                        monthly_chart_type.value == "Daily bars",
                                                        lambda e: set_chart_type("monthly", "Daily bars"),
                                                    ),
                                                ],
                                                wrap=True,
                                                spacing=10,
                                            ),
                                            ft.Container(height=8),
                                            ft.Container(height=300, content=build_dashboard_month_chart()),
                                        ],
                                        spacing=0,
                                    ),
                                ),
                            ),
                            ft.Container(width=18),
                            ft.Container(
                                expand=True,
                                content=section(
                                    "Monthly Allocation",
                                    ft.Column(
                                        [
                                            ft.Text("Current month allocation view", color=SUBTLE, size=12),
                                            ft.Text(
                                                f"Pie view shows where the month's expected money ends up. Bar view shows expense categories only for {dashboard_month.value} {dashboard_year.value}.",
                                                color=MUTED,
                                                size=12,
                                            ),
                                            ft.Container(height=8),
                                            ft.Row(
                                                [
                                                    choice_button(
                                                        "Pie chart",
                                                        expense_chart_type.value == "Pie chart",
                                                        lambda e: set_chart_type("expense", "Pie chart"),
                                                    ),
                                                    choice_button(
                                                        "Category bars",
                                                        expense_chart_type.value == "Category bars",
                                                        lambda e: set_chart_type("expense", "Category bars"),
                                                    ),
                                                ],
                                                wrap=True,
                                                spacing=10,
                                            ),
                                            ft.Container(height=8),
                                            ft.Container(height=300, content=build_dashboard_expense_chart()),
                                        ],
                                        spacing=0,
                                    ),
                                ),
                            ),
                        ]
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )

    def add_view():
        return ft.Container(
            expand=True,
            padding=12,
            content=ft.Column(
                [
                    section(
                        "Add Income / Expense / Saving",
                        ft.Column(
                            [
                                ft.Row([entry_type, entry_category, entry_amount], wrap=True, spacing=12),
                                income_extra_box,
                                ft.Row([entry_month, entry_year, entry_day], wrap=True, spacing=12),
                                ft.Row([entry_note], spacing=12),
                                ft.Container(height=8),
                                ft.Container(
                                    padding=16,
                                    border_radius=18,
                                    bgcolor=PANEL_ALT,
                                    border=ft.Border.all(1, BORDER),
                                    content=ft.Column(
                                        [
                                            recurring_switch,
                                            ft.Row([recurring_until_month, recurring_until_year], wrap=True, spacing=12),
                                            recurring_preview,
                                        ],
                                        spacing=10,
                                    ),
                                ),
                                ft.Container(height=12),
                                ft.Row([add_transaction_button]),
                            ],
                            spacing=12,
                            scroll=ft.ScrollMode.AUTO,
                        ),
                    ),
                    ft.Container(height=18),
                    section(
                        "Add Planned Obligation",
                        ft.Column(
                            [
                                ft.Row([planned_title, planned_category, planned_amount], wrap=True, spacing=12),
                                ft.Row([planned_month, planned_year, planned_day, planned_status, planned_recurrence], wrap=True, spacing=12),
                                ft.Row([planned_note], spacing=12),
                                ft.Container(height=12),
                                ft.Row([add_planned_button]),
                            ],
                            spacing=12,
                            scroll=ft.ScrollMode.AUTO,
                        ),
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )

    def entries_view():
        return ft.Container(
            expand=True,
            padding=12,
            content=ft.Column(
                [
                    section(
                        "Entries for Selected Month",
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Row([filter_month, filter_year, entries_apply_button], spacing=12, wrap=True),
                                        month_view_text,
                                        delete_series_checkbox,
                                        delete_month_button,
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    wrap=True,
                                ),
                                ft.Container(height=12),
                                ft.Text("Transactions", color=MUTED, size=13),
                                ft.Container(
                                    height=280,
                                    padding=ft.padding.only(top=4),
                                    content=tx_list,
                                ),
                                ft.Container(height=18),
                                ft.Text("Planned obligations due this month", color=MUTED, size=13),
                                delete_planned_series_checkbox,
                                ft.Container(
                                    height=280,
                                    padding=ft.padding.only(top=4),
                                    content=planned_list,
                                ),
                            ],
                            expand=True,
                        ),
                        expand=True,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        )

    def render_nav():
        nav_row.controls.clear()
        nav_row.controls.extend(
            [
                nav_button(
                    "Dashboard",
                    ft.Icons.DASHBOARD_ROUNDED,
                    lambda e: set_view("dashboard"),
                    active=current_view["name"] == "dashboard",
                ),
                nav_button(
                    "Add Entry",
                    ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED,
                    lambda e: set_view("add"),
                    active=current_view["name"] == "add",
                ),
                nav_button(
                    "Entries",
                    ft.Icons.RECEIPT_LONG_ROUNDED,
                    lambda e: set_view("entries"),
                    active=current_view["name"] == "entries",
                ),
            ]
        )

    def render_view(view_name: str):
        current_view["name"] = view_name
        render_nav()

        if view_name == "dashboard":
            content_area.content = dashboard_view()
        elif view_name == "add":
            content_area.content = add_view()
        else:
            content_area.content = entries_view()

    def set_view(view_name: str):
        render_view(view_name)
        page.update()

    header = ft.Row(
        [
            ft.Column(
                [
                    ft.Text("FutureBudget", size=30, weight=ft.FontWeight.W_700, color=TEXT),
                    ft.Text(
                        "Monthly income, expenses, savings, planned obligations, and theme-matched charts in one place.",
                        color=SUBTLE,
                    ),
                ],
                spacing=4,
            ),
        ]
    )

    page.add(
        ft.Container(
            expand=True,
            padding=18,
            content=ft.Container(
                expand=True,
                border_radius=30,
                bgcolor="#09111F",
                border=ft.Border.all(1, "#1C2940"),
                padding=22,
                content=ft.Column(
                    [
                        header,
                        ft.Container(height=18),
                        nav_row,
                        ft.Container(height=18),
                        content_area,
                    ],
                    expand=True,
                ),
            ),
        )
    )

    reset_transaction_form()
    reset_planned_form()
    refresh_all()
    render_view("dashboard")


if __name__ == "__main__":
    ft.run(main)
