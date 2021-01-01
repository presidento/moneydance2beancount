#!/usr/bin/env python3
from modules.parser import MoneydanceParser
from modules.converter import Md2BeanConverter
import scripthelper
from dataclasses import dataclass
import datetime
import collections
import textwrap
import pathlib

DEFAULT_CURRENCY = "HUF"
VERY_FIRST_DATE = "2005-01-01"

scripthelper.add_argument(
    "-i",
    "--input-file",
    help="Moneydance txt export filename. Default: Personal finances.txt",
    default="Personal Finances.txt",
)
scripthelper.add_argument("-o", "--output-dir", default="output")
logger, args = scripthelper.bootstrap_args()

out_dir = pathlib.Path(args.output_dir)
out_dir.mkdir(exist_ok=True)

logger.info("Parsing Moneydance input")
parser = MoneydanceParser(args.input_file)
parser.parse()
bean_converter = Md2BeanConverter()
bean_converter.convert(parser.all_transactions())

logger.info("Writing Beancount file")

main_bean = (out_dir / "main.bean").open("w", encoding="utf-8")

main_bean.write(
    textwrap.dedent(
        f"""
    option "title" "Moneydance export"
    option "operating_currency" "{DEFAULT_CURRENCY}"
    option "render_commas" "TRUE"
    option "account_previous_balances" "Opening-Balances"

    plugin "beancount.plugins.implicit_prices"
    ;plugin "beancount.plugins.leafonly"
    ;plugin "beancount.plugins.mark_unverified"

    {VERY_FIRST_DATE} custom "fava-option" "locale" "hu_HU"
    {VERY_FIRST_DATE} custom "fava-option" "show-accounts-with-zero-balance" "false"
"""
    ).strip()
    + "\n\n"
)

with (out_dir / "common.bean").open("w", encoding="utf-8") as common_bean:
    had_opening_balance = False
    last_account_type = None
    common_bean.write(
        f"; Accounts generated from Moneydance export on {datetime.date.today()}\n"
    )
    for account in sorted(bean_converter.accounts.values(), key=lambda a: a.name):
        if account.type != last_account_type:
            common_bean.write("\n")
            last_account_type = account.type
        txt = f"{account.start_date} open  {account.name}"
        if account.type == "Assets":
            txt = f"{txt:55} {account.currency}"
        common_bean.write(txt + "\n")
        if account.start_balance:
            had_opening_balance = True
            common_bean.write(
                textwrap.dedent(
                    f"""
                    {account.start_date} * "Opening balance"
                      {account.name} {account.start_balance} {account.currency}
                      Equity:Opening-Balances
                    """
                ).strip()
                + "\n"
            )

        if account.type == "Assets" or account.type == "Liabilities":
            if account.end_date < datetime.date.today() - datetime.timedelta(days=365):
                common_bean.write(f"{account.end_date} close {account.name}\n")
    if had_opening_balance:
        common_bean.write(f"{VERY_FIRST_DATE} open  Equity:Opening-Balances\n")

main_bean.write('include "common.bean"\n')

main_bean.write('include "fixup.bean"\n')

current_year = 0
current_out_file = None
for transaction in sorted(
    bean_converter.transactions, key=lambda t: f"{t.date} {t.narration} {t.comment}"
):
    if transaction.date.year != current_year:
        current_year = transaction.date.year
        if current_out_file:
            current_out_file.close()
        current_out_file = (out_dir / f"{current_year}.bean").open(
            "w", encoding="utf-8"
        )
        main_bean.write(f'include "{current_year}.bean"\n')

    if not any(posting.amount for posting in transaction.postings):
        continue
    current_out_file.write(transaction.bean_str() + "\n")
    current_out_file.write("\n")


current_out_file.close()
