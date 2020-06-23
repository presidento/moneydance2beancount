#!/usr/bin/env python3
from modules.parser import MoneydanceParser
from modules.converter import Md2BeanConverter
import scripthelper
from dataclasses import dataclass
import datetime
import collections
import textwrap

DEFAULT_CURRENCY = "HUF"

logger = scripthelper.bootstrap()


logger.info("Parsing Moneydance input")
parser = MoneydanceParser("Personal Finances.txt")
parser.parse()
bean_converter = Md2BeanConverter()
bean_converter.convert(parser.all_transactions())

logger.info("Writing Beancount file")

main_bean = open("main.bean", "w", encoding="utf-8")

main_bean.write(textwrap.dedent(f"""
    option "title" "Moneydance export"
    option "operating_currency" "{DEFAULT_CURRENCY}"
    option "render_commas" "TRUE"

    plugin "beancount.plugins.implicit_prices"
    ;plugin "beancount.plugins.leafonly"
    ;plugin "beancount.plugins.mark_unverified"

    2005-01-01 custom "fava-option" "locale" "hu_HU"
    2005-01-01 custom "fava-option" "show-accounts-with-zero-balance" "false"
""").strip() + "\n\n")

with open("common.bean", "w", encoding="utf-8") as common_bean:
    for account in sorted(bean_converter.accounts.values(), key=lambda a: a.name):
        txt = f"{account.start_date} open {account.name}"
        if account.type == "Assets":
            txt += f"     {account.currency}"
        common_bean.write(txt + "\n")

        if account.type == 'Assets' or account.type == 'Liabilities':
            if account.end_date < datetime.date.today() - datetime.timedelta(days=365):
                common_bean.write(f"{account.end_date} close {account.name}\n")

main_bean.write('include "common.bean"\n')

main_bean.write('include "fixup.bean"\n')

current_year = 0
current_out_file = None
for transaction in sorted(bean_converter.transactions, key=lambda p: p.date):
    if transaction.date.year != current_year:
        current_year = transaction.date.year
        if current_out_file:
            current_out_file.close()
        current_out_file = open(f'{current_year}.bean', 'w', encoding='utf-8')
        main_bean.write(f'include "{current_year}.bean"\n')

    if not any(posting.amount for posting in transaction.postings):
        continue
    current_out_file.write(transaction.bean_str() + "\n")
    current_out_file.write("\n")


current_out_file.close()