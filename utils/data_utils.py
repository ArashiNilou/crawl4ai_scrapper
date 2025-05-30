import csv

from models.exposant import exposant


def is_duplicate_exposant(exposant_name: str, seen_names: set) -> bool:
    return exposant_name in seen_names


def is_complete_exposant(exposant: dict, required_keys: list) -> bool:
    return all(key in exposant for key in required_keys)


def save_exposants_to_csv(exposants: list, filename: str):
    if not exposants:
        print("No exposants to save.")
        return

    # Use field names from the exposant model
    fieldnames = exposant.model_fields.keys()

    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(exposants)
    print(f"Saved {len(exposants)} exposants to '{filename}'.")
