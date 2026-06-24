from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_WORKBOOK = Path(r"D:\Onedrive\Desktop\Portafoglio\locale\portafoglio.xlsx")
OUTPUT_FILE = Path(__file__).resolve().parents[1] / "portfolio_snapshot.json"
SNAPSHOT_JS_FILE = Path(__file__).resolve().parents[1] / "snapshot.js"

ALLOWED_BLOCKS = ["A1", "A2", "A3", "A4", "B1", "B2", "C"]
MONTH_ORDER = [
    "Gennaio",
    "Febbraio",
    "Marzo",
    "Aprile",
    "Maggio",
    "Giugno",
    "Luglio",
    "Agosto",
    "Settembre",
    "Ottobre",
    "Novembre",
    "Dicembre",
]
MONTH_NUM = {name.lower(): idx for idx, name in enumerate(MONTH_ORDER, start=1)}
MONTH_SHORT = {name[:3].lower(): idx for idx, name in enumerate(MONTH_ORDER, start=1)}
BLOCK_CONFIG = {
    "A1": {"target": 0.18, "min": 0.14, "max": 0.22, "role": "Stabilita / Difesa"},
    "A2": {"target": 0.14, "min": 0.11, "max": 0.18, "role": "Reddito aggressivo / Ciclici"},
    "A3": {"target": 0.19, "min": 0.16, "max": 0.23, "role": "Alto rendimento / Maggior rischio"},
    "A4": {"target": 0.20, "min": 0.17, "max": 0.23, "role": "ETF Income / Diversificazione"},
    "B1": {"target": 0.21, "min": 0.17, "max": 0.26, "role": "Crescita qualita"},
    "B2": {"target": 0.05, "min": 0.04, "max": 0.07, "role": "Crescita aggressiva"},
    "C": {"target": 0.03, "min": 0.01, "max": 0.05, "role": "Opportunistico / Cripto"},
}
HARD_CAPS = {
    "A2": 0.185,
    "A3": 0.24,
    "A4": 0.235,
    "B1": 0.265,
    "B2": 0.07,
    "C": 0.05,
}


def clean_number(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, float) and math.isnan(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return 0.0

    text = (
        text.replace("\u20ac", "")
        .replace("%", "")
        .replace("\xa0", "")
        .strip()
    )
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return 0.0


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    normalized = {str(col).strip().lower(): col for col in df.columns}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in normalized:
            return normalized[key]

    for col in df.columns:
        col_text = str(col).strip().lower()
        for candidate in candidates:
            if candidate.strip().lower() in col_text:
                return col
    return None


def load_portfolio(workbook_path: Path) -> pd.DataFrame:
    raw = pd.read_excel(workbook_path, sheet_name="Portafoglio", engine="openpyxl")
    raw.columns = [str(col).strip() for col in raw.columns]

    mapping = {
        "Blocco": find_column(raw, ["Blocco"]),
        "Ticker": find_column(raw, ["Ticker", "Azione"]),
        "Valore": find_column(raw, ["Valore", "Valore Attuale"]),
        "Investimento": find_column(raw, ["Investimento Attuale", "Investito", "Costo"]),
        "Yield": find_column(raw, ["Yield", "Rendimento%", "Rendimento %", "Dividendo %"]),
    }

    df = pd.DataFrame()
    for public_col, source_col in mapping.items():
        if source_col is not None:
            df[public_col] = raw[source_col]

    if "Blocco" not in df:
        raise ValueError("Colonna Blocco non trovata nel foglio Portafoglio.")

    df["Blocco"] = df["Blocco"].astype(str).str.strip()
    df = df[df["Blocco"].isin(ALLOWED_BLOCKS)].copy()

    for col in ["Valore", "Investimento", "Yield"]:
        if col in df:
            df[col] = df[col].map(clean_number)
        else:
            df[col] = 0.0

    df = df[df["Valore"].fillna(0) > 0].copy()
    df["Differenza"] = df["Valore"] - df["Investimento"]
    df["DividendiAnnuiStimati"] = df["Valore"] * (df["Yield"] / 100)
    return df


def month_name_it(month_num: int) -> str:
    return MONTH_ORDER[int(month_num) - 1]


def parse_dividend_month_column(column: Any, current_year: int, previous_year: int, duplicate_months: set[str]) -> dict[str, int] | None:
    if isinstance(column, pd.Timestamp):
        return {"year": int(column.year), "month": int(column.month)}

    text = str(column).strip()
    if not text or text.lower() == "nan":
        return None

    suffix_match = re.search(r"_(\d+)$", text)
    occurrence = int(suffix_match.group(1)) if suffix_match else 0
    clean = re.sub(r"_(\d+)$", "", text).strip()

    year_match = re.search(r"(20\d{2})", clean)
    year = int(year_match.group(1)) if year_match else None

    parsed = pd.to_datetime(clean, errors="coerce", dayfirst=True)
    if pd.notna(parsed):
        year = int(parsed.year) if year is None and int(parsed.year) > 1900 else year
        return {"year": year or current_year, "month": int(parsed.month)}

    normalized = re.sub(r"[^A-Za-zÀ-ÿ]", " ", clean).strip().lower()
    month = None
    for name, number in MONTH_NUM.items():
        if name in normalized:
            month = number
            break
    if month is None:
        month = MONTH_SHORT.get(normalized[:3])
    if month is None:
        return None

    if year is None:
        base_name = MONTH_ORDER[month - 1]
        if base_name in duplicate_months:
            year = previous_year if occurrence == 0 else current_year
        else:
            year = previous_year

    return {"year": year, "month": month}


def block_state(block: str, weight: float) -> tuple[str, str]:
    config = BLOCK_CONFIG[block]
    hard_cap = HARD_CAPS.get(block)

    if hard_cap is not None and weight > hard_cap:
        return "alert", "Oltre hard cap"
    if weight < config["min"]:
        return "low", "Sotto banda"
    if weight > config["max"]:
        return "alert", "Sopra banda"
    if weight < config["target"]:
        return "watch", "Sotto target"
    return "watch", "Sopra target in banda"


def build_blocks(df: pd.DataFrame, dividend_by_block: dict[str, float] | None = None) -> list[dict[str, Any]]:
    dividend_by_block = dividend_by_block or {}
    total_value = max(float(df["Valore"].sum()), 1e-9)
    grouped = df.groupby("Blocco", as_index=False).agg(
        value=("Valore", "sum"),
        income=("DividendiAnnuiStimati", "sum"),
    )
    lookup = {row["Blocco"]: row for _, row in grouped.iterrows()}

    blocks = []
    for block in ALLOWED_BLOCKS:
        row = lookup.get(block)
        value = float(row["value"]) if row is not None else 0.0
        income = float(dividend_by_block.get(block) or (row["income"] if row is not None else 0.0))
        weight = value / total_value
        tone, state = block_state(block, weight)
        config = BLOCK_CONFIG[block]
        blocks.append(
            {
                "block": block,
                "role": config["role"],
                "weight": round(weight, 4),
                "target": config["target"],
                "min": config["min"],
                "max": config["max"],
                "delta": round(weight - config["target"], 4),
                "yield": round((income / value * 100) if value else 0.0, 2),
                "state": state,
                "tone": tone,
            }
        )
    return blocks


def build_dividends(workbook_path: Path, fallback_annual: float) -> dict[str, Any]:
    today = pd.Timestamp.today().normalize()
    current_year = int(today.year)
    previous_year = current_year - 1
    try:
        raw = pd.read_excel(workbook_path, sheet_name="Dividendi 2025", header=None, engine="openpyxl")
    except Exception:
        return {
            "annual": round(fallback_annual, 2),
            "monthly_estimate": round(fallback_annual / 12, 2),
            "monthly": [],
            "by_block": {},
            "year": current_year,
            "actual_ytd": 0.0,
            "forecast_future": 0.0,
        }

    header_idx = None
    for idx, row in raw.iterrows():
        labels = [str(v).strip() for v in row.tolist()]
        month_positions = [pos for pos, label in enumerate(labels) if label in MONTH_ORDER]
        if len(month_positions) >= 6:
            block_probe_col = max(0, month_positions[0] - 1)
            below = raw.iloc[idx + 1 : idx + 20, block_probe_col].astype(str).str.strip()
            if below.eq("Totale").any():
                header_idx = idx
                break

    if header_idx is None:
        return {
            "annual": round(fallback_annual, 2),
            "monthly_estimate": round(fallback_annual / 12, 2),
            "monthly": [],
            "by_block": {},
            "year": current_year,
            "actual_ytd": 0.0,
            "forecast_future": 0.0,
        }

    header_values = [str(v).strip() for v in raw.iloc[header_idx].tolist()]
    month_indexes: list[tuple[int, str, int, int]] = []
    month_counts: dict[str, int] = {}
    duplicate_months = {
        month for month in MONTH_ORDER
        if sum(label == month for label in header_values) > 1
    }
    for idx, label in enumerate(header_values):
        if label not in MONTH_ORDER:
            continue
        occurrence = month_counts.get(label, 0)
        month_counts[label] = occurrence + 1
        synthetic_label = f"{label}_{occurrence}" if occurrence else label
        parsed = parse_dividend_month_column(synthetic_label, current_year, previous_year, duplicate_months)
        if parsed is not None:
            month_indexes.append((idx, label, parsed["year"], parsed["month"]))

    if len(month_indexes) < 6:
        return {
            "annual": round(fallback_annual, 2),
            "monthly_estimate": round(fallback_annual / 12, 2),
            "monthly": [],
            "by_block": {},
            "year": current_year,
            "actual_ytd": 0.0,
            "forecast_future": 0.0,
        }

    first_month_col = month_indexes[0][0]
    block_col_idx = max(0, first_month_col - 1)
    summary_rows = raw.iloc[header_idx + 1 : header_idx + 20].copy()
    total_rows = summary_rows[summary_rows.iloc[:, block_col_idx].astype(str).str.strip().eq("Totale")]
    if total_rows.empty:
        return {
            "annual": round(fallback_annual, 2),
            "monthly_estimate": round(fallback_annual / 12, 2),
            "monthly": [],
            "by_block": {},
            "year": current_year,
            "actual_ytd": 0.0,
            "forecast_future": 0.0,
        }

    row = total_rows.iloc[0]
    actual_by_month = {month_num: 0.0 for month_num in range(1, 13)}
    actual_by_block = {block: 0.0 for block in ALLOWED_BLOCKS}
    previous_by_month = {month_num: 0.0 for month_num in range(1, 13)}

    for idx, _month_name, year, month_num in month_indexes:
        amount = clean_number(row.iloc[idx])
        if year == current_year and month_num <= int(today.month):
            actual_by_month[month_num] += amount
        elif year == previous_year:
            previous_by_month[month_num] += amount

    for _, block_row in summary_rows.iterrows():
        block = str(block_row.iloc[block_col_idx]).strip()
        if block in ALLOWED_BLOCKS:
            actual_by_block[block] = round(
                sum(
                    clean_number(block_row.iloc[idx])
                    for idx, _month_name, year, month_num in month_indexes
                    if year == current_year and month_num <= int(today.month)
                ),
                2,
            )

    future_by_month, future_by_block = build_dividend_forecast_from_calendar(workbook_path, today)
    monthly = []
    for month_num in range(1, 13):
        actual = actual_by_month.get(month_num, 0.0)
        future = future_by_month.get(month_num, 0.0)
        amount = actual + future
        if month_num < int(today.month):
            kind = "Reale"
        elif month_num == int(today.month) and actual > 0 and future > 0:
            kind = "Reale + stimato"
        elif month_num <= int(today.month) and actual > 0:
            kind = "Reale"
        else:
            kind = "Stimato"
        monthly.append(
            {
                "month": month_name_it(month_num)[:3],
                "amount": round(amount, 2),
                "actual": round(actual, 2),
                "forecast": round(future, 2),
                "type": kind,
            }
        )

    by_block = {
        block: round(actual_by_block.get(block, 0.0) + future_by_block.get(block, 0.0), 2)
        for block in ALLOWED_BLOCKS
        if actual_by_block.get(block, 0.0) or future_by_block.get(block, 0.0)
    }

    actual_ytd = sum(actual_by_month.values())
    forecast_future = sum(future_by_month.values())
    annual = actual_ytd + forecast_future
    monthly_estimate = monthly[int(today.month) - 1]["amount"] if monthly else annual / 12
    previous_ytd = sum(value for month, value in previous_by_month.items() if month <= int(today.month))

    return {
        "annual": round(annual, 2),
        "monthly_estimate": round(monthly_estimate, 2),
        "monthly": monthly,
        "by_block": by_block,
        "year": current_year,
        "actual_ytd": round(actual_ytd, 2),
        "forecast_future": round(forecast_future, 2),
        "previous_ytd": round(previous_ytd, 2),
        "growth_ytd": round(((actual_ytd - previous_ytd) / previous_ytd), 4) if previous_ytd > 0 else None,
    }


def build_dividend_forecast_from_calendar(workbook_path: Path, today: pd.Timestamp) -> tuple[dict[int, float], dict[str, float]]:
    try:
        calendar = pd.read_excel(workbook_path, sheet_name="Calendario Dividendi", engine="openpyxl")
        portfolio = load_portfolio(workbook_path)
    except Exception:
        return {}, {}

    ticker_to_block = {}
    if {"Ticker", "Blocco"}.issubset(portfolio.columns):
        ticker_to_block = {
            str(row["Ticker"]).strip(): str(row["Blocco"]).strip()
            for _, row in portfolio.iterrows()
            if str(row.get("Ticker", "")).strip()
        }

    date_cols = [col for col in calendar.columns if str(col).lower().startswith("data_")]
    current_year = int(today.year)
    by_month: dict[int, float] = {}
    by_block: dict[str, float] = {}

    for _, row in calendar.iterrows():
        amount = clean_number(row.get("ultimo_dividendo", 0.0))
        if amount <= 0:
            continue
        ticker = str(row.get("ticker", "")).strip()
        block = ticker_to_block.get(ticker)
        for col in date_cols:
            dt = pd.to_datetime(row.get(col), errors="coerce")
            if pd.isna(dt):
                continue
            dt = dt.normalize()
            if int(dt.year) != current_year or dt <= today:
                continue
            month_num = int(dt.month)
            by_month[month_num] = by_month.get(month_num, 0.0) + amount
            if block in ALLOWED_BLOCKS:
                by_block[block] = by_block.get(block, 0.0) + amount

    return by_month, by_block


def build_performance(workbook_path: Path) -> dict[str, Any]:
    try:
        raw = pd.read_excel(workbook_path, sheet_name="Andamento", engine="openpyxl")
    except Exception:
        return {"series": [], "total_return": 0.0, "max_drawdown": 0.0}

    raw.columns = [str(col).strip() for col in raw.columns]
    date_col = find_column(raw, ["DATA", "Data"])
    value_col = find_column(raw, ["GIORNALIERO", "Azioni", "TOTALE"])
    pct_col = find_column(raw, ["PERCENTUALE"])
    if date_col is None or value_col is None:
        return {"series": [], "total_return": 0.0, "max_drawdown": 0.0}

    df = raw[[date_col, value_col] + ([pct_col] if pct_col else [])].copy()
    df = df.rename(columns={date_col: "date", value_col: "value"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = df["value"].map(clean_number)
    df = df.dropna(subset=["date"])
    df = df[df["value"] > 0].sort_values("date")

    if df.empty:
        return {"series": [], "total_return": 0.0, "max_drawdown": 0.0}

    first = float(df["value"].iloc[0])
    df["index"] = df["value"] / first * 100
    df["peak"] = df["index"].cummax()
    df["drawdown"] = df["index"] / df["peak"] - 1

    step = max(1, len(df) // 120)
    sampled = df.iloc[::step].tail(120)
    series = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "index": round(float(row["index"]), 2),
            "drawdown": round(float(row["drawdown"]), 4),
        }
        for _, row in sampled.iterrows()
    ]

    total_return = float(df["index"].iloc[-1] / 100 - 1)
    max_drawdown = float(df["drawdown"].min())
    return {
        "series": series,
        "total_return": round(total_return, 4),
        "max_drawdown": round(max_drawdown, 4),
    }


def portfolio_score(blocks: list[dict[str, Any]], df: pd.DataFrame) -> int:
    total = max(float(df["Valore"].sum()), 1e-9)
    weights = df["Valore"] / total
    hhi = float((weights**2).sum())
    top5 = float(weights.sort_values(ascending=False).head(5).sum())
    ids = float(sum(abs(block["delta"]) for block in blocks))

    score = 100
    score -= min(30, int(hhi * 200))
    score -= min(25, int(top5 * 40))
    score -= min(25, int(ids * 200))
    return max(0, min(100, score))


def build_snapshot(workbook_path: Path) -> dict[str, Any]:
    df = load_portfolio(workbook_path)
    total_value = float(df["Valore"].sum())
    total_cost = float(df["Investimento"].sum())
    total_pnl = total_value - total_cost
    fallback_annual = float(df["DividendiAnnuiStimati"].sum())

    dividends = build_dividends(workbook_path, fallback_annual)
    blocks = build_blocks(df, dividends.get("by_block", {}))
    performance = build_performance(workbook_path)
    score = portfolio_score(blocks, df)

    alerts = [
        {
            "block": block["block"],
            "state": block["state"],
            "delta": block["delta"],
            "tone": block["tone"],
        }
        for block in blocks
        if block["tone"] in {"alert", "low"}
    ][:5]

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_mtime": datetime.fromtimestamp(workbook_path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
            "privacy": "Aggregated mobile snapshot. No raw workbook, transactions, screenshots, or full title list.",
        },
        "summary": {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round((total_pnl / total_cost) if total_cost else 0.0, 4),
            "positions_count": int(len(df)),
            "portfolio_score": score,
            "yield_on_value": round((dividends["annual"] / total_value) if total_value else 0.0, 4),
        },
        "blocks": blocks,
        "dividends": dividends,
        "performance": performance,
        "alerts": alerts,
    }


def main() -> None:
    workbook_path = Path(os.environ.get("PORTFOLIO_XLSX", DEFAULT_WORKBOOK))
    if not workbook_path.exists():
        raise FileNotFoundError(f"Workbook not found: {workbook_path}")

    snapshot = build_snapshot(workbook_path)
    snapshot_json = json.dumps(snapshot, indent=2, ensure_ascii=False)
    OUTPUT_FILE.write_text(snapshot_json, encoding="utf-8")
    SNAPSHOT_JS_FILE.write_text(
        "window.PORTFOLIO_SNAPSHOT = "
        + snapshot_json
        + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_FILE}")
    print(f"Wrote {SNAPSHOT_JS_FILE}")
    print(snapshot["meta"]["privacy"])


if __name__ == "__main__":
    main()
