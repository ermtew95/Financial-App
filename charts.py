import flet as ft
import flet_charts as fch


def sek(amount: float) -> str:
    return f"{amount:,.0f} SEK".replace(",", " ")


def empty_chart_message(text: str) -> ft.Container:
    return ft.Container(
        height=260,
        alignment=ft.Alignment.CENTER,
        content=ft.Text(text, color="#64748B", size=14),
    )


def build_monthly_line_chart(series: list[dict]) -> ft.Control:
    if not any(
        item["income"] or item["expense"] or item["saving"] or item["planned"]
        for item in series
    ):
        return empty_chart_message("No yearly data yet.")

    income_points = []
    expense_points = []
    saving_points = []
    planned_points = []

    max_y = 0
    for idx, item in enumerate(series, start=1):
        income_points.append(fch.LineChartDataPoint(idx, item["income"]))
        expense_points.append(fch.LineChartDataPoint(idx, item["expense"]))
        saving_points.append(fch.LineChartDataPoint(idx, item["saving"]))
        planned_points.append(fch.LineChartDataPoint(idx, item["planned"]))
        max_y = max(max_y, item["income"], item["expense"], item["saving"], item["planned"])

    max_y = max(10, max_y * 1.15)

    return fch.LineChart(
        min_x=1,
        max_x=12,
        min_y=0,
        max_y=max_y,
        interactive=True,
        bgcolor="#0F172A",
        tooltip=fch.LineChartTooltip(
            bgcolor="#11182B",
            fit_inside_horizontally=True,
            fit_inside_vertically=True,
        ),
        left_axis=fch.ChartAxis(
            label_size=44,
            title=ft.Text("SEK", size=12, color="#94A3B8"),
            title_size=24,
        ),
        bottom_axis=fch.ChartAxis(
            label_size=28,
            labels=[
                fch.ChartAxisLabel(
                    value=i,
                    label=ft.Text(
                        ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"][i - 1],
                        color="#94A3B8",
                        size=11,
                    ),
                )
                for i in range(1, 13)
            ],
        ),
        horizontal_grid_lines=fch.ChartGridLines(
            interval=max_y / 5 if max_y else 1,
            color=ft.Colors.with_opacity(0.15, "#94A3B8"),
            width=1,
        ),
        vertical_grid_lines=fch.ChartGridLines(
            interval=1,
            color=ft.Colors.with_opacity(0.08, "#94A3B8"),
            width=1,
        ),
        data_series=[
            fch.LineChartData(
                color="#22D3EE",
                stroke_width=4,
                curved=True,
                rounded_stroke_cap=True,
                points=income_points,
            ),
            fch.LineChartData(
                color="#EF4444",
                stroke_width=4,
                curved=True,
                rounded_stroke_cap=True,
                points=expense_points,
            ),
            fch.LineChartData(
                color="#A855F7",
                stroke_width=4,
                curved=True,
                rounded_stroke_cap=True,
                points=saving_points,
            ),
            fch.LineChartData(
                color="#F59E0B",
                stroke_width=4,
                curved=True,
                rounded_stroke_cap=True,
                points=planned_points,
            ),
        ],
        expand=True,
    )


def build_daily_line_chart(series: list[dict]) -> ft.Control:
    if not series:
        return empty_chart_message("No daily data for this month.")

    income_points = []
    expense_points = []
    leftover_points = []
    max_x = 1
    max_y = 0

    for item in series:
        d = item["day"]
        income_points.append(fch.LineChartDataPoint(d, item["income"]))
        expense_points.append(fch.LineChartDataPoint(d, item["expense"]))
        leftover_points.append(fch.LineChartDataPoint(d, item["leftover"]))
        max_x = max(max_x, d)
        max_y = max(max_y, item["income"], item["expense"], item["leftover"])

    max_y = max(10, max_y * 1.15)

    return fch.LineChart(
        min_x=1,
        max_x=max_x,
        min_y=0,
        max_y=max_y,
        interactive=True,
        bgcolor="#0F172A",
        tooltip=fch.LineChartTooltip(
            bgcolor="#11182B",
            fit_inside_horizontally=True,
            fit_inside_vertically=True,
        ),
        left_axis=fch.ChartAxis(
            label_size=44,
            title=ft.Text("SEK", size=12, color="#94A3B8"),
            title_size=24,
        ),
        bottom_axis=fch.ChartAxis(
            label_size=28,
        ),
        horizontal_grid_lines=fch.ChartGridLines(
            interval=max_y / 5 if max_y else 1,
            color=ft.Colors.with_opacity(0.15, "#94A3B8"),
            width=1,
        ),
        vertical_grid_lines=fch.ChartGridLines(
            interval=max(1, int(max_x / 6)),
            color=ft.Colors.with_opacity(0.08, "#94A3B8"),
            width=1,
        ),
        data_series=[
            fch.LineChartData(
                color="#22D3EE",
                stroke_width=4,
                curved=True,
                rounded_stroke_cap=True,
                points=income_points,
            ),
            fch.LineChartData(
                color="#EF4444",
                stroke_width=4,
                curved=True,
                rounded_stroke_cap=True,
                points=expense_points,
            ),
            fch.LineChartData(
                color="#22C55E",
                stroke_width=4,
                curved=True,
                rounded_stroke_cap=True,
                points=leftover_points,
            ),
        ],
        expand=True,
    )


def build_expense_pie_chart(category_rows: list[tuple[str, float]]) -> ft.Control:
    if not category_rows:
        return empty_chart_message("No expense categories yet.")

    palette = ["#7C3AED", "#22D3EE", "#22C55E", "#F59E0B", "#EF4444", "#EC4899", "#3B82F6"]

    sections = []
    total = sum(amount for _, amount in category_rows)

    for i, (category, amount) in enumerate(category_rows):
        pct = 0 if total == 0 else round((amount / total) * 100)
        sections.append(
            fch.PieChartSection(
                value=amount,
                title=f"{pct}%",
                color=palette[i % len(palette)],
                radius=80,
                title_style=ft.TextStyle(
                    size=12,
                    color="#F8FAFC",
                    weight=ft.FontWeight.BOLD,
                ),
            )
        )

    legend = ft.Column(
        [
            ft.Row(
                [
                    ft.Container(
                        width=10,
                        height=10,
                        border_radius=10,
                        bgcolor=palette[i % len(palette)],
                    ),
                    ft.Text(category, color="#CBD5E1", expand=True),
                    ft.Text(f"{amount:,.0f} SEK".replace(",", " "), color="#E2E8F0"),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
            for i, (category, amount) in enumerate(category_rows)
        ],
        spacing=8,
    )

    chart = fch.PieChart(
        sections=sections,
        sections_space=2,
        center_space_radius=40,
        expand=True,
    )

    return ft.Row(
        [
            ft.Container(expand=1, height=260, content=chart),
            ft.Container(width=16),
            ft.Container(expand=1, content=legend),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def build_horizontal_bar_list(
    items: list[tuple[str, float]],
    empty_text: str,
    bar_color: str = "#22D3EE",
) -> ft.Control:
    if not items:
        return empty_chart_message(empty_text)

    max_value = max(value for _, value in items) or 1

    return ft.Column(
        [
            ft.Row(
                [
                    ft.Text(label, color="#CBD5E1", width=84, size=12),
                    ft.Container(
                        expand=True,
                        height=12,
                        border_radius=999,
                        bgcolor="#162033",
                        content=ft.Container(
                            width=max(6, int((value / max_value) * 280)),
                            height=12,
                            border_radius=999,
                            bgcolor=bar_color,
                        ),
                    ),
                    ft.Text(sek(value), color="#E2E8F0", width=90, text_align=ft.TextAlign.RIGHT, size=12),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            for label, value in items
        ],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
    )


def build_yearly_bar_overview(series: list[dict]) -> ft.Control:
    items = [(item["month"][5:], item["total_balance"]) for item in series if item["income"] or item["expense"] or item["saving"] or item["total_balance"]]
    if not items:
        return empty_chart_message("No yearly data yet.")

    max_abs = max(abs(value) for _, value in items) or 1
    rows = []
    for label, value in items:
        width = max(6, int((abs(value) / max_abs) * 280))
        color = "#22C55E" if value >= 0 else "#EF4444"
        rows.append(
            ft.Row(
                [
                    ft.Text(label, color="#CBD5E1", width=50, size=12),
                    ft.Container(width=width, height=12, border_radius=999, bgcolor=color),
                    ft.Text(sek(value), color="#E2E8F0", size=12),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    return ft.Column(rows, spacing=10, scroll=ft.ScrollMode.AUTO)


def build_daily_bar_overview(series: list[dict]) -> ft.Control:
    items = [(str(item["day"]), item["total_balance"]) for item in series if item["income"] or item["expense"] or item["saving"] or item["total_balance"]]
    if not items:
        return empty_chart_message("No daily data for this month.")

    max_abs = max(abs(value) for _, value in items) or 1
    rows = []
    for label, value in items:
        width = max(6, int((abs(value) / max_abs) * 260))
        color = "#22C55E" if value >= 0 else "#EF4444"
        rows.append(
            ft.Row(
                [
                    ft.Text(label, color="#CBD5E1", width=32, size=12),
                    ft.Container(
                        width=width,
                        height=12,
                        border_radius=999,
                        bgcolor=color,
                    ),
                    ft.Text(sek(value), color="#E2E8F0", size=12),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    return ft.Column(rows, spacing=10, scroll=ft.ScrollMode.AUTO)


def build_daily_activity_list(series: list[dict]) -> ft.Control:
    active_days = [item for item in series if item["income"] or item["expense"] or item["saving"]]
    if not active_days:
        return empty_chart_message("No transaction days in this month.")

    rows = []
    for item in active_days:
        parts = []
        if item["income"]:
            parts.append(ft.Text(f"Income {sek(item['income'])}", color="#86EFAC", size=12))
        if item["expense"]:
            parts.append(ft.Text(f"Expense {sek(item['expense'])}", color="#FCA5A5", size=12))
        if item["saving"]:
            parts.append(ft.Text(f"Saving {sek(item['saving'])}", color="#C084FC", size=12))
        parts.append(ft.Text(f"Balance {sek(item['total_balance'])}", color="#22D3EE", size=12))

        rows.append(
            ft.Container(
                padding=14,
                border_radius=16,
                bgcolor="#101A2C",
                border=ft.Border.all(1, "#22314A"),
                content=ft.Row(
                    [
                        ft.Text(f"Day {item['day']}", color="#E2E8F0", width=62, weight=ft.FontWeight.W_700),
                        ft.Row(parts, wrap=True, spacing=14, expand=True),
                    ],
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        )

    return ft.Column(rows, spacing=10, scroll=ft.ScrollMode.AUTO)


def build_yearly_totals_list(series: list[dict]) -> ft.Control:
    active_months = [item for item in series if item["income"] or item["expense"] or item["saving"] or item["planned"]]
    if not active_months:
        return empty_chart_message("No yearly data yet.")

    rows = []
    for item in active_months:
        rows.append(
            ft.Container(
                padding=14,
                border_radius=16,
                bgcolor="#101A2C",
                border=ft.Border.all(1, "#22314A"),
                content=ft.Column(
                    [
                        ft.Text(item["month"][5:], color="#E2E8F0", weight=ft.FontWeight.W_700),
                        ft.Row(
                            [
                                ft.Text(f"Income {sek(item['income'])}", color="#86EFAC", size=12),
                                ft.Text(f"Expense {sek(item['expense'])}", color="#FCA5A5", size=12),
                                ft.Text(f"Saving {sek(item['saving'])}", color="#C084FC", size=12),
                                ft.Text(f"Planned {sek(item['planned'])}", color="#FCD34D", size=12),
                            ],
                            wrap=True,
                            spacing=14,
                        ),
                    ],
                    spacing=8,
                ),
            )
        )

    return ft.Column(rows, spacing=10, scroll=ft.ScrollMode.AUTO)


def build_yearly_totals_pie_chart(series: list[dict]) -> ft.Control:
    if not series:
        return empty_chart_message("No yearly data yet.")

    latest = series[-1]
    rows = []

    if latest["saved_balance"] > 0:
        rows.append(("Saved balance", latest["saved_balance"]))

    available_balance = latest["available_balance"]
    if available_balance > 0:
        rows.append(("Available balance", available_balance))
    elif available_balance < 0:
        rows.append(("Over budget", abs(available_balance)))

    if not rows:
        return empty_chart_message("No yearly data yet.")

    return build_expense_pie_chart(rows)


def build_balance_pie_chart(saved_balance: float, available_balance: float, empty_text: str) -> ft.Control:
    rows = []

    if saved_balance > 0:
        rows.append(("Saved balance", saved_balance))

    if available_balance > 0:
        rows.append(("Available balance", available_balance))
    elif available_balance < 0:
        rows.append(("Over budget", abs(available_balance)))

    if not rows:
        return empty_chart_message(empty_text)

    return build_expense_pie_chart(rows)


def build_flow_breakdown_chart(
    total_available: float,
    opening_balance: float,
    income_total: float,
    allocation_rows: list[tuple[str, float]],
    remaining_balance: float,
    period_label: str,
    show_carry_over: bool = True,
) -> ft.Control:
    if total_available <= 0 and not allocation_rows and remaining_balance <= 0:
        return empty_chart_message(f"No money flow for {period_label.lower()} yet.")

    use_rows = list(allocation_rows)
    if remaining_balance > 0:
        use_rows.append(("Saved after costs", remaining_balance))
    elif remaining_balance < 0:
        use_rows.append(("Over budget", abs(remaining_balance)))

    allocation_chart = build_expense_pie_chart(use_rows) if use_rows else empty_chart_message("No allocations yet.")

    return ft.Column(
        [
            ft.Container(
                height=430,
                padding=14,
                border_radius=16,
                bgcolor="#101A2C",
                border=ft.Border.all(1, "#22314A"),
                content=ft.Column(
                    [
                        ft.Text("Money allocation", color="#CBD5E1", size=13, weight=ft.FontWeight.W_600),
                        ft.Text(
                            "This pie shows where the expected money ends up for the period.",
                            color="#64748B",
                            size=12,
                        ),
                        ft.Row(
                            [
                                ft.Container(
                                    visible=show_carry_over,
                                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                                    border_radius=999,
                                    bgcolor="#13233C",
                                    content=ft.Text(f"Carry-over {sek(opening_balance)}", color="#CBD5E1", size=12),
                                ),
                                ft.Container(
                                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                                    border_radius=999,
                                    bgcolor="#123525",
                                    content=ft.Text(f"Income {sek(income_total)}", color="#DCFCE7", size=12),
                                ),
                            ],
                            wrap=True,
                            spacing=10,
                        ),
                        allocation_chart,
                    ],
                    spacing=10,
                ),
            ),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
    )


def build_totals_pie_chart(rows: list[tuple[str, float]], empty_text: str) -> ft.Control:
    filtered = [(label, value) for label, value in rows if value > 0]
    if not filtered:
        return empty_chart_message(empty_text)
    return build_expense_pie_chart(filtered)


def build_totals_bar_chart(rows: list[tuple[str, float]], empty_text: str) -> ft.Control:
    filtered = [(label, value) for label, value in rows if value > 0]
    return build_horizontal_bar_list(filtered, empty_text, bar_color="#22D3EE")


def build_expense_category_bars(category_rows: list[tuple[str, float]]) -> ft.Control:
    return build_horizontal_bar_list(
        category_rows,
        "No expense categories yet.",
        bar_color="#A855F7",
    )
