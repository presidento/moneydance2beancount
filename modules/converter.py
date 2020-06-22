from dataclasses import dataclass
import datetime
import collections

DEFAULT_CURRENCY = 'HUF'

class Account:
    def __init__(self, md_account):
        if md_account.account_type == 'EXPENSE':
            prefix = "Expenses"
        elif md_account.account_type == 'INCOME':
            prefix = "Income"
        elif md_account.account_type == 'BANK' or md_account.account_type == 'ASSET':
            prefix = "Assets"
        elif md_account.account_type == 'LIABILITY':
            prefix = "Liabilities"
        else:
            raise NotImplementedError(f"Moneydance account type {md_account.account_type}")
        self.name = prefix  + ":" + self.fix_name(md_account.name)
        self.start_date = None
        self.end_date = None
        self.start_balance = md_account.start_balance
        self.currency = md_account.currency
        self.type = prefix
    
    def register_date(self, date):
        if not self.start_date or self.start_date > date:
            self.start_date = date
        if not self.end_date or self.end_date < date:
            self.end_date = date
    
    @staticmethod
    def fix_name(name):
        name = name.replace("&", "")
        name = name.replace(" ", "-")
        name = name.replace("--", "-")
        name = ':'.join(part[0].upper() + part[1:] for part in name.split(":"))
        return name


@dataclass
class Transaction:
    date: datetime.date
    status: str
    payee: str
    narration: str
    comment: str

    def __init__(self, md_transaction):
        self.date=md_transaction.date
        self.status=self.convert_status(md_transaction.status)
        self.payee=""
        self.narration=md_transaction.description.replace("\"", "'")
        self.comment=md_transaction.memo
        self.splits = []

    @staticmethod
    def convert_status(md_status):
        # FIXME: calculate status
        return "*"


@dataclass
class Split:
    account: Account
    amount: float
    comment: str
    in_default_currency: float

    def __init__(self, account, md_transaction):
        self.account = account
        self.amount = md_transaction.amount
        self.comment = md_transaction.memo
        if self.currency != DEFAULT_CURRENCY:
            self.in_default_currency = md_transaction.splits[0].amount
        else:
            self.in_default_currency = None

    
    @property
    def currency(self):
        return self.account.currency


def they_are_opposite(md_transaction, md_split):
    return (
        md_transaction.account == md_split.account
        and md_transaction.amount == -md_split.amount
        and md_transaction.memo == md_split.memo
    )


class Md2BeanConverter:
    def __init__(self):
        self.accounts = {}
        self.transactions = []

    def bean_account(self, md_account):
        if md_account.name not in self.accounts:
            self.accounts[md_account.name] = Account(md_account)
        return self.accounts[md_account.name]

    def convert(self, moneydance_transactions):
        self.accounts = {}
        self.transactions = []
        all_md_transactions = collections.defaultdict(
            collections.deque
        )  # date -> list(transactions)
        for transaction in moneydance_transactions:
            all_md_transactions[transaction.date].append(transaction)

        for date, transaction_list in all_md_transactions.items():
            self.transactions += self.parse_transaction_list(date, transaction_list)
        
        self.update_account_start_end_dates()

    def parse_transaction_list(self, date, transaction_list):
        bean_transactions = []
        while transaction_list:
            md_transaction = transaction_list.popleft()
            splits = []
            for split in md_transaction.splits:
                for candidate in transaction_list:
                    if (
                        they_are_opposite(candidate, split)
                        and len(candidate.splits) == 1
                        and they_are_opposite(md_transaction, candidate.splits[0])
                    ):
                        transaction_list.remove(candidate)
                        splits.append(candidate)
                        break
            if splits:
                bean_transaction = Transaction(md_transaction)
                for split in splits:
                    bean_transaction.splits.append(self.create_split(split))
                bean_transaction.splits.append(self.create_split(md_transaction))
                bean_transactions.append(bean_transaction)
            else:
                # This is one of the "other part" of the transaction
                # Put back to the end of the list, and parse later
                transaction_list.append(md_transaction)
        return bean_transactions

    def create_split(self, md_transaction):
        account = self.bean_account(md_transaction.account)
        split = Split(account=account, md_transaction=md_transaction)
        return split

    def update_account_start_end_dates(self):
        for transaction in self.transactions:
            for split in transaction.splits:
                split.account.register_date(transaction.date)
