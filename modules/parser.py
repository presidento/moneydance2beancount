from dataclasses import dataclass
import datetime
import csv
import scripthelper

logger = scripthelper.get_logger(__name__)


@dataclass
class MdAccount:
    name: str
    uuid: str = ""
    account_type: str = ""
    currency: str = ""
    start_balance: float = 0

    def __init__(self, name):
        self.name = name
        self.transactions = []


@dataclass
class MdTransaction:
    date: datetime.date
    tax_date: datetime.date
    date_entered: datetime.date
    check_number: str
    description: str
    status: str
    account: MdAccount
    memo: str
    amount: float

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.splits = []


@dataclass
class MdSplit:
    status: str
    account: MdAccount
    memo: str
    amount: float


class MoneydanceParser:
    def __init__(self, filename):
        self.filename = filename
        self._accounts = {}
        self._current_type = None
        self._current_account = None
        self._current_transaction = None

    def get_account(self, name):
        if name not in self._accounts:
            self._accounts[name] = MdAccount(name=name)
        return self._accounts[name]

    def parse(self):
        self._accounts = {}
        self._current_type = None
        self._current_account = None
        self._current_transaction = None

        with open(self.filename, encoding="cp1250", newline="") as input_file:
            reader = csv.reader(input_file, delimiter="\t", quotechar="'")
            for row in reader:
                self.parse_row(row)

    def parse_row(self, row):
        if not row or not row[0]:
            return
        if row[0][0] == "#":
            self._current_type = row[0][1:]
        elif self._current_type == "Currency":
            # For me it does not contain any valuable information...
            pass
        elif self._current_type == "Account":
            self.parse_account(row)
        elif self._current_type == "Date":
            if row[0] != "-":
                self.parse_transaction(row)
            else:
                self.parse_split(row)
        else:
            logger.warning(f"Unhandled type: {self._current_type}")

    def parse_account(self, row):
        account = self.get_account(row[0])
        account.name = row[0]
        account.uuid = row[1]
        account.account_type = row[2]
        account.currency = row[3]
        account.start_balance = float(row[4])
        logger.verbose(f"New {account}")
        self._current_account = account

    def parse_transaction(self, row):
        transaction = MdTransaction(
            date=datetime.datetime.strptime(row[0], "%Y.%m.%d").date(),
            tax_date=datetime.datetime.strptime(row[1], "%Y.%m.%d").date(),
            date_entered=datetime.datetime.strptime(row[2][:19], "%Y.%m.%d %H:%M:%S"),
            check_number=row[3],
            description=row[4],
            status=row[5],
            account=self.get_account(row[6]),
            memo=row[7],
            amount=float(row[8]),
        )
        self._current_account.transactions.append(transaction)
        self._current_transaction = transaction
        logger.debug(f"New {transaction}")

    def parse_split(self, row):
        assert row[1] == "-"
        assert row[2] == "-"
        assert row[3] == "-"
        assert row[4] == "-"
        self._current_transaction.splits.append(
            MdSplit(
                status=row[5],
                account=self.get_account(row[6]),
                memo=row[7],
                amount=float(row[8]),
            )
        )
    
    def all_transactions(self):
        for account in self._accounts.values():
            logger.debug(f"Account transactions: {account.name:40} {len(account.transactions)}")
            yield from account.transactions
