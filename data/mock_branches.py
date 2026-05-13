# data/mock_branches.py

MOCK_BRANCHES = [
    {
        "branch_id" : "HYD-001",
        "name"      : "Ameerpet Branch",
        "address"   : "Plot 45, SR Nagar Main Road, Ameerpet, Hyderabad - 500016",
        "area"      : "Ameerpet",
        "zone"      : "Hyderabad West",
        "phone"     : "040-23456789",
        "timings"   : "Mon-Fri: 9:30 AM - 3:30 PM | Sat: 9:30 AM - 1:00 PM",
        "closed_on" : "Sunday & Public Holidays",
        "services"  : ["Account Opening", "Loans", "Locker", "Forex", "NRI Services"],
        "latitude"  : 17.4375,
        "longitude" : 78.4483,
        "manager"   : "Ms. Priya Sharma"
    },
    {
        "branch_id" : "HYD-002",
        "name"      : "Kukatpally Branch",
        "address"   : "KPHB Phase 1 Main Road, Kukatpally, Hyderabad - 500072",
        "area"      : "Kukatpally",
        "zone"      : "Hyderabad West",
        "phone"     : "040-23456790",
        "timings"   : "Mon-Fri: 9:30 AM - 3:30 PM | Sat: 9:30 AM - 1:00 PM",
        "closed_on" : "Sunday & Public Holidays",
        "services"  : ["Account Opening", "Loans", "NRI Services"],
        "latitude"  : 17.4849,
        "longitude" : 78.3996,
        "manager"   : "Mr. Anil Reddy"
    },
    {
        "branch_id" : "HYD-003",
        "name"      : "Begumpet Branch",
        "address"   : "SD Road, Begumpet, Hyderabad - 500016",
        "area"      : "Begumpet",
        "zone"      : "Hyderabad Central",
        "phone"     : "040-23456791",
        "timings"   : "Mon-Fri: 9:30 AM - 3:30 PM | Sat: 9:30 AM - 1:00 PM",
        "closed_on" : "Sunday & Public Holidays",
        "services"  : ["Account Opening", "Loans", "Locker", "Forex"],
        "latitude"  : 17.4432,
        "longitude" : 78.4637,
        "manager"   : "Ms. Sunita Rao"
    },
    {
        "branch_id" : "HYD-004",
        "name"      : "Madhapur Branch",
        "address"   : "Plot 12, HITEC City Main Road, Madhapur, Hyderabad - 500081",
        "area"      : "Madhapur",
        "zone"      : "Hyderabad West",
        "phone"     : "040-23456792",
        "timings"   : "Mon-Fri: 9:30 AM - 3:30 PM | Sat: 9:30 AM - 1:00 PM",
        "closed_on" : "Sunday & Public Holidays",
        "services"  : ["Account Opening", "Loans", "Forex", "NRI Services"],
        "latitude"  : 17.4489,
        "longitude" : 78.3785,
        "manager"   : "Mr. Venkat Prasad"
    },
    {
        "branch_id" : "HYD-005",
        "name"      : "Secunderabad Branch",
        "address"   : "MG Road, Secunderabad, Hyderabad - 500003",
        "area"      : "Secunderabad",
        "zone"      : "Hyderabad Central",
        "phone"     : "040-23456793",
        "timings"   : "Mon-Fri: 9:30 AM - 3:30 PM | Sat: 9:30 AM - 1:00 PM",
        "closed_on" : "Sunday & Public Holidays",
        "services"  : ["Account Opening", "Loans", "Locker", "Forex", "NRI Services"],
        "latitude"  : 17.4399,
        "longitude" : 78.4983,
        "manager"   : "Mr. Rajesh Kumar"
    }
]

MOCK_ATMS = [
    {
        "atm_id"      : "ATM-HYD-001",
        "area"        : "Ameerpet",
        "address"     : "Near Metro Station, Ameerpet, Hyderabad - 500016",
        "timings"     : "24/7",
        "type"        : "Cash Withdrawal + Deposit",
        "operational" : True,
        "latitude"    : 17.4380,
        "longitude"   : 78.4490
    },
    {
        "atm_id"      : "ATM-HYD-002",
        "area"        : "Kukatpally",
        "address"     : "Near JNTU Metro Station, Kukatpally, Hyderabad - 500072",
        "timings"     : "24/7",
        "type"        : "Cash Withdrawal + Deposit",
        "operational" : True,
        "latitude"    : 17.4855,
        "longitude"   : 78.4001
    },
    {
        "atm_id"      : "ATM-HYD-003",
        "area"        : "Madhapur",
        "address"     : "Cyber Towers, HITEC City, Madhapur, Hyderabad - 500081",
        "timings"     : "24/7",
        "type"        : "Cash Withdrawal only",
        "operational" : False,      # edge case — non-operational
        "latitude"    : 17.4486,
        "longitude"   : 78.3908
    },
    {
        "atm_id"      : "ATM-HYD-004",
        "area"        : "Begumpet",
        "address"     : "Raj Bhavan Road, Begumpet, Hyderabad - 500016",
        "timings"     : "24/7",
        "type"        : "Cash Withdrawal + Deposit",
        "operational" : True,
        "latitude"    : 17.4440,
        "longitude"   : 78.4640
    },
    {
        "atm_id"      : "ATM-HYD-005",
        "area"        : "Secunderabad",
        "address"     : "Paradise Circle, Secunderabad, Hyderabad - 500003",
        "timings"     : "8:00 AM - 10:00 PM",   # edge case — not 24/7
        "type"        : "Cash Withdrawal only",
        "operational" : True,
        "latitude"    : 17.4405,
        "longitude"   : 78.4990
    }
]

# Locality coordinates for Haversine fallback
LOCALITY_COORDINATES = {
    "ameerpet"      : (17.4375, 78.4483),
    "kukatpally"    : (17.4849, 78.3996),
    "kphb"          : (17.4932, 78.3927),
    "madhapur"      : (17.4489, 78.3785),
    "hitec city"    : (17.4486, 78.3908),
    "gachibowli"    : (17.4401, 78.3489),
    "banjara hills" : (17.4156, 78.4347),
    "jubilee hills" : (17.4239, 78.4082),
    "begumpet"      : (17.4432, 78.4637),
    "secunderabad"  : (17.4399, 78.4983),
    "mehdipatnam"   : (17.3956, 78.4339),
    "lb nagar"      : (17.3474, 78.5529),
    "uppal"         : (17.4054, 78.5592),
    "dilsukhnagar"  : (17.3687, 78.5247),
    "kompally"      : (17.5403, 78.4861),
    "alwal"         : (17.4932, 78.5156),
    "miyapur"       : (17.4963, 78.3559),
    "kondapur"      : (17.4600, 78.3800),
    "tolichowki"    : (17.4043, 78.4167),
    "attapur"       : (17.3843, 78.4156)
}
