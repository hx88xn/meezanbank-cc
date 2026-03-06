#!/usr/bin/env python3
"""
Remove pages/ files not needed for call center RAG.
Keeps: products, services, contact, complaints, policies, calculators, branch info.
Removes: press releases, careers, investor relations, AGM/shareholder notices, IPOs.
"""
import os
import re
import sys

PAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "pages")

KEEP_PATTERNS = [
    r"^-account\.txt$",
    r"^ur-.*-account\.txt$",
    r"-debit-card\.txt$",
    r"-calculator\.txt$",
    r"^about-us",
    r"^why-meezan",
    r"^contact-us",
    r"^branch-banking",
    r"^branch-locator",
    r"^branches-open",
    r"^atm\.txt$",
    r"^internet-banking",
    r"^Internet_banking",
    r"^whatsapp-banking",
    r"^ways-to-bank",
    r"^complaint-form",
    r"^grievances-commissioner",
    r"^consumer-ease",
    r"^consumer-financial-protection",
    r"^Policies",
    r"^blow-the-whistle",
    r"^deposit-protection",
    r"^Disclaimer",
    r"^call-centre",
    r"^car-ijarah",
    r"^easy-home",
    r"^apni-bike",
    r"^solar-panel",
    r"^commercial-banking",
    r"^commercial-vehicles",
    r"^corporate-banking",
    r"^sme-banking",
    r"^cash-management",
    r"^certificate-of",
    r"^term-certificates",
    r"^calculators\.txt$",
    r"^digital-",
    r"^freelancer-accounts",
    r"^home-remittance",
    r"^free-services",
    r"^glossary",
    r"^unclaimed",
    r"^dormant-account",
    r"^iban-generator",
    r"^foreign-exchange",
    r"^historical-profit",
    r"^feedback-form",
    r"^quickpay",
    r"^card-banking",
    r"^card-discounts",
    r"^debit-card-higher",
    r"^bank-accounts",
    r"^business-bank-accounts",
    r"^business-term",
    r"^roshan-",
    r"^labbaik-",
    r"^meezan-amdaan",
    r"^meezan-kafalah",
    r"^meezan-ebiz",
    r"^meezan-women",
    r"^naya-pakistan-certificate",
    r"^senior-citizen",
    r"^express-",
    r"^rupee-",
    r"^dollar-",
    r"^euro-",
    r"^pound-",
    r"^payroll-partner",
    r"^export-financing",
    r"^agricultural-finance",
    r"^financial-institutions",
    r"^islamic-institutions",
    r"^karobari-munafa",
    r"^kids-club",
    r"^teens-club",
    r"^plus-account",
    r"^world-debit",
    r"^visa-",
    r"^paypak-debit",
    r"^titanium-debit",
    r"^fcy-debit",
    r"^student-debit",
    r"^women-account",
    r"^asaan-",
    r"^bachat-account",
    r"^treasury\.txt$",
    r"^invest-in-psx",
    r"^eipo\.txt$",
    r"^governance\.txt$",
    r"^Governance",
    r"^zakat-donations",
    r"^customer-notice\.txt$",
    r"^customer-notice-ramadan",
    r"^customer-notice-atm",
    r"^customer-notice-biometric",
    r"^customer-notice-revised",
    r"^customer-notice-acquisition",
    r"^customer-notice-branch-merger",
    r"^customer-notice-branch-relocation\.txt$",
    r"^public-notice\.txt$",
    r"^public-notice-timings",
    r"^public-notice-system-maintenance",
    r"^public-notice-ramadan",
    r"^public-notice-property",
    r"^public-notice-release",
    r"^public-notice-donations",
    r"^public-notice-eid",
    r"^public-holidays\.txt$",
    r"^public-holiday\.txt$",
    r"^public-holiday-kashmir-day\.txt$",
    r"^public-holiday-ashura\.txt$",
    r"^public-holiday-pakistan",
    r"^public-holiday-quaid",
    r"^public-holiday-on-independence",
    r"^public-holiday-general",
    r"^regulatory-announcements",
    r"^security-alert",
    r"^system-maintenance",
    r"^core-banking-system",
    r"^important-information-for-meezan-bachat",
    r"^discontinuation-of-free-takaful",
    r"^exchangeability-of-demonetized",
    r"^guidelines-for-overseas",
    r"^consumer-protection-department",
    r"^state-bank-customer-facilitation",
    r"^list-of-e-branches",
    r"^meezan-banking\.txt$",
    r"^meezan-bachat-account-change",
    r"^meezan-bank-1link-guarantee",
    r"^meezan-bank-introduces-",
    r"^meezan-bank-shariah-board-approves",
    r"^google-wallet-available",
    r"^strategic-partnership-with-visa",
    r"^blue-card-conversion",
    r"^branch-premises-required",
    r"^aof-tncs",
    r"^safe-deposit-lockers",
    r"^Deposit-Protection-Mechanism",
]

REMOVE_PATTERNS = [
    r"^meezan-bank-(awarded|wins|receives|recognized|ranked|selected|named|announces|signs|partners|launches|joins|hosts|conducts|celebrates|donates|supports|arranges|participates|collaborates|enters|inks|executes|expands|establishes|opens|closes|offers|provides|selects|topped|distributes|holds|facilitates|completes|restores|takes|surpasses|records|delivers|disburses|issues|becomes|achieves|acquires|acts|addresses|advised|agrees|anchors|arranges|awards|closes|collaborates|conducts|continues|declares|delivers|disburses|donates|donatesfor|engages|enters|establishes|executes|expands|extends|facilitates|goes|has|honored|honors|holds|hosts|initiates|inks|introduces|issues|joins|launched|launches|leads|limited-holds|limited-launches|limited-to-|makes|named|offers|opens|participates|partners|posts|provides|ranks|receives|recognizes|records|restores|selects|signs|sponsors|starts|successfully|supports|surpasses|takes|to-|topped|transactions|unveils|webinar)",
    r"^mbl-",
    r"^career-opportunit",
    r"^careers\.txt$",
    r"^investor-relations",
    r"^financial-information\.txt$",
    r"^info-for-investors",
    r"^analyst-presentation",
    r"^annualreport",
    r"^media-centre",
    r"^awards-and-recognition",
    r"^publications\.txt$",
    r"^life-at-meezan",
    r"^index(_1)?\.txt$",
    r"^sitemap\.txt$",
    r"^ur\.txt$",
    r"delegation-identifies",
    r"acquisition-of-hsbc",
    r"^addendum-to-notice",
    r"^close-notice-of-.*agm",
    r"^notice-of-(board-meeting|election|extraordinary|book-closure)",
    r"^credit-of-(final|interim|unpaid|shares)",
    r"^placement-of-financial",
    r"^publication-of-credit",
    r"^vehicle-for-sale",
    r"^awwal-modaraba.*ipo",
    r"^synthetic-products.*ipo",
    r"^banker-to-issue",
    r"^archive-calendars",
    r"^certificate-on-payment",
    r"^credit-delivery-of-share",
    r"^credit-of-shares-into",
    r"^e-rights-shares",
    r"^interim-cash-dividend",
    r"^letter-to-psel",
    r"^change-in-address-of-registered",
    r"^disclosure-of-material",
    r"^discontinuation-of-meezan-atmdebit",
    r"^22-country-delegation",
    r"^afghan-bankers-delegation",
    r"^1link-onboards",
    r"^acting-governor-sbp",
    r"^administrator-karachi",
    r"^aaoifi-meezanbank",
    r"^agreement-to-standardize",
    r"^al-meezan-investments-and-karachi",
    r"^alliance-between-meezan",
    r"^approves-guidelines-at-pakistan",
    r"^arshad-nadeem",
    r"^asset-management",
    r"^audio-video",
    r"^best-bank-in-pakistan-by-ehsanulla",
    r"^badaami-bagh-branch",
    r"^center-for-excellence",
    r"^ceif-ims-research",
    r"^daraz-and-meezan",
    r"^deputy-ceo-earns",
    r"^dr-imran-usmani",
    r"^etihad-savings-partnership",
    r"^fatwa-favoring",
    r"^first-bank-in-pakistan",
    r"^first-ever-",
    r"^first-winner-of-meezan-mobile",
    r"^fourth-winner-of-meezan-mobile",
    r"^second-winner-of-meezan-mobile",
    r"^third-winner-of-meezan-mobile",
    r"^freedom-bank-network",
    r"^gong-ceremony",
    r"^government-of-pakistan-nominates",
    r"^grand-opening-of-meezan",
    r"^ifc-signs-advisory",
    r"^iiib",
    r"^inceifs-professor",
    r"^independence-day-celebration",
    r"^interactive-learning-session",
    r"^investment-in-shariah-compliant-shares.*webinar",
    r"^irfan-siddiqui-center",
    r"^islamic-banking-awareness-seminar",
    r"^islamic-banking-seminar",
    r"^islamic-finance-news",
    r"^issuance-of-pkr",
    r"^jazzcash-meezan",
    r"^jcr-vis-",
    r"^justice-r-mufti",
    r"^karachi-stock-exchange",
    r"^kazakhstan-bilateral",
    r"^laptop-ease-stalls",
    r"^lahore-east-region-holds",
    r"^malaysian-delegation",
    r"^meezan-justuju",
    r"^meezanbank-embarks",
    r"^meezanbank-mou",
    r"^meezanbank-nayapay",
    r"^Public-Awareness-videos",
    r"^shalimar-link-road-branch",
    r"^saddar-area-karachi",
    r"^dal-bazar-branch",
    r"^secp-sbp-launch",
    r"^shaukat-khanum-memorial",
    r"^stylers-shariah",
    r"^supreme-court-diamer",
    r"^syed-amir-ali-meezan",
    r"^uk-financing-the-production",
    r"^unconventional",
    r"^vavacars-and-meezan",
    r"^vis-reaffirms",
    r"^visa-mbl-partner",
    r"^wisaaq-dawlance-expansion",
]

def should_keep(basename: str) -> bool:
    for pat in KEEP_PATTERNS:
        if re.search(pat, basename, re.I):
            return True
    for pat in REMOVE_PATTERNS:
        if re.search(pat, basename, re.I):
            return False
    if basename.startswith("ur-") and "-account" in basename or "debit-card" in basename or "current" in basename or "savings" in basename:
        return True
    if "meezan-bank-" in basename or "mbl-" in basename:
        return False
    return True

def main():
    dry_run = "--dry-run" in sys.argv
    force = "--yes" in sys.argv or "-y" in sys.argv
    for x in ["--dry-run", "--yes", "-y"]:
        if x in sys.argv:
            sys.argv.remove(x)

    if not os.path.isdir(PAGES_DIR):
        print(f"❌ Pages dir not found: {PAGES_DIR}")
        return 1

    to_delete = []
    to_keep = []
    for f in os.listdir(PAGES_DIR):
        if not f.endswith(".txt"):
            continue
        if should_keep(f):
            to_keep.append(f)
        else:
            to_delete.append(f)

    print(f"Keeping: {len(to_keep)} files")
    print(f"Removing: {len(to_delete)} files\n")
    if to_delete:
        for f in sorted(to_delete)[:30]:
            print(f"  - {f}")
        if len(to_delete) > 30:
            print(f"  ... and {len(to_delete) - 30} more")

    if not dry_run and to_delete:
        if force:
            for f in to_delete:
                os.remove(os.path.join(PAGES_DIR, f))
            print(f"\n✅ Deleted {len(to_delete)} files.")
        else:
            confirm = input("\nDelete these files? [y/N]: ").strip().lower()
            if confirm == "y":
                for f in to_delete:
                    os.remove(os.path.join(PAGES_DIR, f))
                print(f"✅ Deleted {len(to_delete)} files.")
            else:
                print("Cancelled.")
    elif dry_run:
        print("\n(Use without --dry-run to delete)")

    return 0

if __name__ == "__main__":
    sys.exit(main())
