"""
Synthetic contact details (name / address / phone) for candidates.

The bundled datasets contain no personal contact data, so to make anonymisation *real* (something
that can be withheld server-side) each user gets deterministic, obviously fake PII generated here.
It is only ever released by `GET /lender/candidates/{ref}` after the candidate has accepted a
lender's offer. Nothing in this module is real personal data.
"""
import hashlib
import random

_FIRST = ["Aarav", "Diya", "Kabir", "Meera", "Rohan", "Isha", "Vikram", "Ananya", "Arjun", "Sneha"]
_LAST = ["Sharma", "Iyer", "Reddy", "Nair", "Gupta", "Patel", "Menon", "Das", "Rao", "Kulkarni"]
_STREET = ["MG Road", "Park Street", "Lake View Lane", "Station Road", "Temple Street", "Hill Crest Avenue"]
_CITY = ["Bengaluru", "Pune", "Hyderabad", "Chennai", "Kolkata", "Mumbai"]


def get_pii(user_id: str) -> dict:
    seed = int(hashlib.sha256(f"pii:{user_id}".encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    return {
        "name": f"{rng.choice(_FIRST)} {rng.choice(_LAST)}",
        "address": f"{rng.randint(1, 250)}, {rng.choice(_STREET)}, {rng.choice(_CITY)}",
        "phone": f"+91-9{rng.randint(100000000, 999999999)}",
    }
