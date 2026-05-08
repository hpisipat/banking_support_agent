# data/mock_accounts.py

MOCK_CUSTOMERS = {

    "CUST-10234": {
        "customer_id"          : "CUST-10234",
        "name"                 : "Ravi Kumar",
        "dob"                  : "15-Mar-1988",
        "mobile"               : "9876543210",
        "email"                : "ravikumar@gmail.com",
        "kyc_status"           : "Verified",
        "kyc_expiry"           : "31-Mar-2026",
        "account"              : {
            "account_number"   : "001234567890",
            "account_type"     : "Savings Account",
            "status"           : "Active",
            "opening_date"     : "10-Jun-2015",
            "branch"           : "Ameerpet Branch",
            "ifsc"             : "BANK0001234",
            "nominee"          : "Sunitha Kumar (Wife)"
        },
        "linked_products"      : {
            "loans"   : [
                {
                    "loan_id"    : "LN-2022-001",
                    "type"       : "Personal Loan",
                    "amount"     : 200000,
                    "emi"        : 4500,
                    "status"     : "Active",
                    "start_date" : "10-Jun-2022",
                    "end_date"   : "10-Jun-2025"
                }
            ],
            "cards"   : [
                {
                    "card_id" : "DC-10234-001",
                    "type"    : "Debit Card",
                    "network" : "Visa",
                    "limit"   : 0,
                    "status"  : "Active",
                    "expiry"  : "12-2027"
                },
                {
                    "card_id" : "CC-10234-001",
                    "type"    : "Credit Card",
                    "network" : "Mastercard",
                    "limit"   : 150000,
                    "status"  : "Active",
                    "expiry"  : "06-2026"
                }
            ],
            "deposits": [
                {
                    "deposit_id" : "FD-10234-001",
                    "type"       : "Fixed Deposit",
                    "amount"     : 50000,
                    "rate"       : 7.5,
                    "start_date" : "10-Jun-2023",
                    "maturity"   : "10-Jun-2025",
                    "status"     : "Active"
                }
            ]
        },
        "segment"              : "Regular",
        "relationship_manager" : "Ms. Priya Sharma"
    },

    "CUST-10235": {
        "customer_id"          : "CUST-10235",
        "name"                 : "Ananya Reddy",
        "dob"                  : "22-Jul-1995",
        "mobile"               : "9848012345",
        "email"                : "ananya.reddy@gmail.com",
        "kyc_status"           : "Expired",        # edge case
        "kyc_expiry"           : "31-Dec-2023",
        "account"              : {
            "account_number"   : "001234567891",
            "account_type"     : "Savings Account",
            "status"           : "Dormant",        # edge case
            "opening_date"     : "05-Jan-2019",
            "branch"           : "Kukatpally Branch",
            "ifsc"             : "BANK0001235",
            "nominee"          : "Ramesh Reddy (Father)"
        },
        "linked_products"      : {
            "loans"   : [],
            "cards"   : [
                {
                    "card_id" : "DC-10235-001",
                    "type"    : "Debit Card",
                    "network" : "Rupay",
                    "limit"   : 0,
                    "status"  : "Active",
                    "expiry"  : "09-2026"
                }
            ],
            "deposits": []
        },
        "segment"              : "Regular",
        "relationship_manager" : "Mr. Anil Reddy"
    },

    "CUST-10236": {
        "customer_id"          : "CUST-10236",
        "name"                 : "Prasad G",
        "dob"                  : "08-Nov-1980",
        "mobile"               : "9700123456",
        "email"                : "prasad.g@outlook.com",
        "kyc_status"           : "Verified",
        "kyc_expiry"           : "30-Jun-2027",
        "account"              : {
            "account_number"   : "001234567892",
            "account_type"     : "Current Account",
            "status"           : "Frozen",         # edge case
            "opening_date"     : "18-Mar-2010",
            "branch"           : "Begumpet Branch",
            "ifsc"             : "BANK0001236",
            "nominee"          : "Geeta G (Spouse)"
        },
        "linked_products"      : {
            "loans"   : [
                {
                    "loan_id"    : "LN-2020-004",
                    "type"       : "Home Loan",
                    "amount"     : 4500000,
                    "emi"        : 42000,
                    "status"     : "Active",
                    "start_date" : "18-Mar-2020",
                    "end_date"   : "18-Mar-2035"
                },
                {
                    "loan_id"    : "LN-2019-002",
                    "type"       : "Car Loan",
                    "amount"     : 800000,
                    "emi"        : 0,
                    "status"     : "Closed",
                    "start_date" : "01-Jan-2019",
                    "end_date"   : "01-Jan-2023"
                }
            ],
            "cards"   : [
                {
                    "card_id" : "DC-10236-001",
                    "type"    : "Debit Card",
                    "network" : "Visa",
                    "limit"   : 0,
                    "status"  : "Blocked",
                    "expiry"  : "03-2025"
                },
                {
                    "card_id" : "CC-10236-001",
                    "type"    : "Credit Card",
                    "network" : "Visa",
                    "limit"   : 500000,
                    "status"  : "Active",
                    "expiry"  : "11-2027"
                }
            ],
            "deposits": [
                {
                    "deposit_id" : "FD-10236-001",
                    "type"       : "Fixed Deposit",
                    "amount"     : 200000,
                    "rate"       : 7.8,
                    "start_date" : "18-Mar-2023",
                    "maturity"   : "18-Mar-2026",
                    "status"     : "Active"
                },
                {
                    "deposit_id" : "RD-10236-001",
                    "type"       : "Recurring Deposit",
                    "amount"     : 5000,
                    "rate"       : 6.5,
                    "start_date" : "01-Apr-2023",
                    "maturity"   : "01-Apr-2025",
                    "status"     : "Active"
                }
            ]
        },
        "segment"              : "Premium",
        "relationship_manager" : "Ms. Sunita Rao"
    },

    "CUST-10237": {
        "customer_id"          : "CUST-10237",
        "name"                 : "Sneha Patil",
        "dob"                  : "30-Sep-1999",
        "mobile"               : "9123456789",
        "email"                : "sneha.patil@gmail.com",
        "kyc_status"           : "Verified",
        "kyc_expiry"           : "30-Sep-2025",
        "account"              : {
            "account_number"   : "001234567893",
            "account_type"     : "Savings Account",
            "status"           : "Active",
            "opening_date"     : "15-Aug-2021",
            "branch"           : "Madhapur Branch",
            "ifsc"             : "BANK0001237",
            "nominee"          : "Vijay Patil (Father)"
        },
        "linked_products"      : {
            "loans"   : [
                {
                    "loan_id"    : "LN-2023-009",
                    "type"       : "Education Loan",
                    "amount"     : 600000,
                    "emi"        : 8000,
                    "status"     : "Active",
                    "start_date" : "01-Aug-2023",
                    "end_date"   : "01-Aug-2028"
                }
            ],
            "cards"   : [
                {
                    "card_id" : "DC-10237-001",
                    "type"    : "Debit Card",
                    "network" : "Rupay",
                    "limit"   : 0,
                    "status"  : "Active",
                    "expiry"  : "08-2028"
                }
            ],
            "deposits": []
        },
        "segment"              : "Regular",
        "relationship_manager" : "Mr. Venkat Prasad"
    },

    "CUST-10238": {
        "customer_id"          : "CUST-10238",
        "name"                 : "Lakshmi Narayana",
        "dob"                  : "12-Feb-1965",
        "mobile"               : "9456781234",
        "email"                : "lnarayana@yahoo.com",
        "kyc_status"           : "Verified",
        "kyc_expiry"           : "28-Feb-2027",
        "account"              : {
            "account_number"   : "001234567894",
            "account_type"     : "Savings Account",
            "status"           : "Active",
            "opening_date"     : "02-Apr-2005",
            "branch"           : "Secunderabad Branch",
            "ifsc"             : "BANK0001238",
            "nominee"          : "Padma Narayana (Wife)"
        },
        "linked_products"      : {
            "loans"   : [],
            "cards"   : [
                {
                    "card_id" : "DC-10238-001",
                    "type"    : "Debit Card",
                    "network" : "Visa",
                    "limit"   : 0,
                    "status"  : "Active",
                    "expiry"  : "04-2026"
                },
                {
                    "card_id" : "CC-10238-001",
                    "type"    : "Credit Card",
                    "network" : "Mastercard",
                    "limit"   : 300000,
                    "status"  : "Active",
                    "expiry"  : "04-2026"
                }
            ],
            "deposits": [
                {
                    "deposit_id" : "FD-10238-001",
                    "type"       : "Fixed Deposit",
                    "amount"     : 500000,
                    "rate"       : 8.0,
                    "start_date" : "02-Apr-2023",
                    "maturity"   : "02-Apr-2026",
                    "status"     : "Active"
                },
                {
                    "deposit_id" : "FD-10238-002",
                    "type"       : "Fixed Deposit",
                    "amount"     : 300000,
                    "rate"       : 7.5,
                    "start_date" : "01-Jan-2024",
                    "maturity"   : "01-Jan-2027",
                    "status"     : "Active"
                }
            ]
        },
        "segment"              : "Premium",
        "relationship_manager" : "Ms. Priya Sharma"
    }
}

MOCK_STAFF = {
    "EMP-4521": {"name": "Priya Sharma",  "branch": "Ameerpet",     "role": "Manager"},
    "EMP-3310": {"name": "Anil Reddy",    "branch": "Kukatpally",   "role": "Employee"},
    "EMP-2201": {"name": "Sunita Rao",    "branch": "Begumpet",     "role": "Manager"},
    "EMP-1105": {"name": "Venkat Prasad", "branch": "Madhapur",     "role": "Employee"},
}
