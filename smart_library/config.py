# Settings. Change DB password to YOUR MySQL root password.
class Config:
    SECRET_KEY = "change-this-secret"
    DB = dict(host="localhost", user="root", password="your_password", database="smart_library")
    LOAN_DAYS = 14      # days a book can be kept
    FINE_PER_DAY = 2    # Rs fine per overdue day
