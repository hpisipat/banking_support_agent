# data/mock_tickets.py

MOCK_TICKETS_LIST = [
    {
        "ticket_id"        : "TKT-2024-00142",
        "customer_id"      : "CUST-10234",
        "category"         : "Transaction Issue",
        "sub_category"     : "Failed ATM Transaction",
        "description"      : "ATM transaction of Rs.5,000 failed at Ameerpet ATM. Amount debited.",
        "date_of_incident" : "10-Apr-2024",
        "amount"           : 5000,
        "priority"         : "High",
        "status"           : "In Progress",
        "logged_on"        : "10-Apr-2024",
        "last_updated"     : "11-Apr-2024 10:30 AM",
        "updated_by"       : "Operations Team",
        "remark"           : "Transaction records retrieved. Refund being processed.",
        "email_sent_to"    : "r*******r@gmail.com",
        "resolution_eta"   : "12-Apr-2024"
    },
    {
        "ticket_id"        : "TKT-2024-00139",
        "customer_id"      : "CUST-10236",
        "category"         : "Account Issue",
        "sub_category"     : "Wrong Charges Applied",
        "description"      : "Annual maintenance charge deducted twice in March 2024.",
        "date_of_incident" : "31-Mar-2024",
        "amount"           : 750,
        "priority"         : "Medium",
        "status"           : "Resolved",
        "logged_on"        : "01-Apr-2024",
        "last_updated"     : "05-Apr-2024 02:00 PM",
        "updated_by"       : "Accounts Team",
        "remark"           : "Duplicate charge confirmed. Rs.750 refunded to account.",
        "email_sent_to"    : "f*****m@outlook.com",
        "resolution_eta"   : "05-Apr-2024"
    },
    {
        "ticket_id"        : "TKT-2024-00155",
        "customer_id"      : "CUST-10235",
        "category"         : "Digital Banking Issue",
        "sub_category"     : "Net Banking Login Not Working",
        "description"      : "Unable to login to net banking for the past 3 days.",
        "date_of_incident" : "08-Apr-2024",
        "amount"           : 0,
        "priority"         : "Medium",
        "status"           : "Logged",
        "logged_on"        : "08-Apr-2024",
        "last_updated"     : "08-Apr-2024 09:00 AM",
        "updated_by"       : "System",
        "remark"           : "Ticket logged. Assigned to digital banking team.",
        "email_sent_to"    : "a*****y@gmail.com",
        "resolution_eta"   : "10-Apr-2024"
    },
    {
        "ticket_id"        : "TKT-2024-00160",
        "customer_id"      : "CUST-10237",
        "category"         : "Card Issue",
        "sub_category"     : "Debit Card Not Working",
        "description"      : "Debit card declined at POS terminal at Big Bazaar, Madhapur.",
        "date_of_incident" : "11-Apr-2024",
        "amount"           : 2300,
        "priority"         : "Medium",
        "status"           : "Awaiting Info",
        "logged_on"        : "11-Apr-2024",
        "last_updated"     : "11-Apr-2024 04:00 PM",
        "updated_by"       : "Card Services Team",
        "remark"           : "Please confirm if card is within validity and PIN was entered correctly.",
        "email_sent_to"    : "s*****l@gmail.com",
        "resolution_eta"   : "13-Apr-2024"
    }
]

# Dict for fast lookup by ticket ID
MOCK_TICKETS = {
    ticket["ticket_id"]: ticket for ticket in MOCK_TICKETS_LIST
}
