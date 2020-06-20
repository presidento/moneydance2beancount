#!/usr/bin/env python3
from modules.parser import MoneydanceParser
from modules.converter import Md2BeanConverter
import scripthelper
from dataclasses import dataclass
import datetime
import collections

DEFAULT_CURRENCY = "HUF"

logger = scripthelper.bootstrap()


logger.info("Parsing Moneydance input")
parser = MoneydanceParser("Personal Finances.txt")
parser.parse()
bean_converter = Md2BeanConverter()
bean_converter.convert(parser.all_transactions())

logger.info("Writing Beancount file")

main_bean = open("main.bean", "w", encoding="utf-8")

main_bean.write('option "title" "Moneydance export"\n')
main_bean.write(f'option "operating_currency" "{DEFAULT_CURRENCY}"\n')

for account in sorted(bean_converter.accounts.values(), key=lambda a: a.name):
    txt = f"{account.start_date} open {account.name}"
    if account.type == "Assets":
        txt += f"     {account.currency}"
        if account.currency != DEFAULT_CURRENCY:
            txt += ' "NONE"'
    main_bean.write(txt + "\n")

main_bean.write("\n\n")

current_year = 0
current_out_file = None
for transaction in sorted(bean_converter.transactions, key=lambda p: p.date):
    if transaction.date.year != current_year:
        current_year = transaction.date.year
        if current_out_file:
            current_out_file.close()
        current_out_file = open(f'{current_year}.bean', 'w', encoding='utf-8')
        main_bean.write(f'include "{current_year}.bean"\n')
    txt = f'{transaction.date} {transaction.status} "{transaction.payee}" "{transaction.narration}"'
    if transaction.comment:
        txt += f" ; {transaction.comment}"
    current_out_file.write(txt + "\n")
    for split in transaction.splits:
        txt = f"  {split.account.name:50} {split.amount:10.2f} {split.account.currency}"
        if split.in_default_currency:
            txt += (
                " {{"
                + f"{abs(split.in_default_currency):.2f} {DEFAULT_CURRENCY}"
                + "}}"
            )
        if split.comment and split.comment != transaction.comment:
            txt += f" ; " + split.comment
        current_out_file.write(txt + "\n")
    current_out_file.write("\n")


current_out_file.close()