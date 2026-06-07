import sys


def confirm_before_send(contacts: list[dict]) -> bool:
    """
    Print a summary of who will be emailed and ask Y/N.
    Returns True only if the user explicitly types 'y' or 'yes'.
    """
    divider = "─" * 54

    print(f"\n{divider}")
    print(f"  SAFETY CHECKPOINT — {len(contacts)} email(s) queued")
    print(divider)

    # Show first 5 contacts as a preview
    preview = contacts[:5]
    for i, c in enumerate(preview, 1):
        name    = c.get("name", "Unknown")
        email   = c.get("email", "—")
        company = c.get("company", "—")
        title   = c.get("title", "")
        print(f"  {i}. {name} <{email}>")
        print(f"     {title} @ {company}")

    if len(contacts) > 5:
        print(f"\n  ... and {len(contacts) - 5} more contact(s)")

    print(divider)
    print("  Review data/stage3_enriched.csv for the full list.")
    print(divider)

    try:
        answer = input("\n  Proceed and send all emails? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  Aborted.")
        sys.exit(0)

    return answer in {"y", "yes"}
