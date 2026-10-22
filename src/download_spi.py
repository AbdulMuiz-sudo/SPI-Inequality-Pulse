
from pathlib import Path
from datetime import datetime
import re
import time

from playwright.sync_api import sync_playwright

# PBS Weekly SPI (Index) page
URL = "https://www.pbs.gov.pk/price-statistics/"

# Output folders
BASE_DIR = Path("pbs_spi_backfill")
ANNEXURE_DIR = BASE_DIR / "annexure"
REPORT_DIR = BASE_DIR / "report"

ANNEXURE_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Be polite to the PBS website
DELAY_SECONDS = 0.5


def clean_filename(text):
    """Convert a date such as 08-10-2026 to a filename-safe string."""
    return re.sub(r"[^a-zA-Z0-9_-]", "-", text.strip())


def save_download(request_context, url, destination):
    """Download a file only if it has not already been saved."""
    if destination.exists() and destination.stat().st_size > 0:
        print(f"SKIP: {destination.name} (already exists)")
        return True

    try:
        response = request_context.get(
            url,
            timeout=60000
        )

        if not response.ok:
            print(f"FAILED: HTTP {response.status} - {url}")
            return False

        content = response.body()

        # XLSX files are ZIP containers and begin with PK.
        if not content.startswith(b"PK"):
            print(f"FAILED: Response is not an XLSX file - {url}")
            return False

        destination.write_bytes(content)
        print(f"DOWNLOADED: {destination}")
        return True

    except Exception as exc:
        print(f"FAILED: {url}\n  Reason: {exc}")
        return False


def get_spi_table(page):
    """Find the Weekly SPI (Index) table by its column headings."""
    for table in page.locator("table").all():
        text = " ".join(table.inner_text().split()).lower()

        if (
            "week ended on" in text
            and "annexure" in text
            and "report" in text
        ):
            return table

    return None


def get_header_indexes(table):
    """Identify the date and Excel download columns."""
    for row in table.locator("tr").all():
        headers = row.locator("th").all()

        if not headers:
            continue

        names = [
            " ".join(h.inner_text().split()).lower()
            for h in headers
        ]

        date_index = next(
            (i for i, name in enumerate(names)
             if "week ended on" in name),
            None
        )

        annexure_index = next(
            (i for i, name in enumerate(names)
             if "annexure" in name and "excel" in name),
            None
        )

        report_index = next(
            (i for i, name in enumerate(names)
             if "report" in name and "excel" in name),
            None
        )

        if (
            date_index is not None
            and annexure_index is not None
            and report_index is not None
        ):
            return date_index, annexure_index, report_index

    raise RuntimeError(
        "Could not identify the Excel columns. "
        "Inspect the table headings on the PBS page."
    )


def main():
    downloaded = 0
    skipped_or_failed = 0
    seen_dates = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            accept_downloads=True
        )
        page = context.new_page()

        print("Opening PBS Weekly SPI page...")
        page.goto(URL, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(3000)

        # The table may be lower down the page.
        # Give the page time to finish rendering.
        page.wait_for_timeout(5000)

        # Do not require the Weekly SPI tab text to be visible.
        # The next step will inspect the page's actual tables.
        print("Page title:", page.title())
        print("Page URL:", page.url)
        print("Tables found:", page.locator("table").count())
        print("SPI tab text found:",
            page.get_by_text("Weekly SPI", exact=False).count())

        page_number = 1

        while True:
            table = get_spi_table(page)

            if table is None:
                print(
                    "Could not find the Weekly SPI table. "
                    "The website layout may have changed."
                )
                break

            date_idx, annexure_idx, report_idx = (
                get_header_indexes(table)
            )

            rows = table.locator("tr").all()
            new_dates_on_page = 0

            for row in rows:
                cells = row.locator("td").all()

                if not cells or len(cells) <= max(
                    date_idx, annexure_idx, report_idx
                ):
                    continue

                date_text = cells[date_idx].inner_text().strip()

                # Accept dates in DD-MM-YYYY format.
                if not re.fullmatch(
                    r"\d{2}-\d{2}-\d{4}", date_text
                ):
                    continue

                if date_text in seen_dates:
                    continue

                seen_dates.add(date_text)
                new_dates_on_page += 1

                date_file = clean_filename(date_text)

                print(f"\nWeek ending: {date_text}")

                files_to_download = [
                    (
                        cells[annexure_idx],
                        ANNEXURE_DIR / f"SPI_Annexure_{date_file}.xlsx",
                    ),
                    (
                        cells[report_idx],
                        REPORT_DIR / f"SPI_Report_{date_file}.xlsx",
                    ),
                ]

                for cell, destination in files_to_download:
                    link = cell.locator("a").first

                    if link.count() == 0:
                        print(f"FAILED: No download link for {destination.name}")
                        skipped_or_failed += 1
                        continue

                    href = link.get_attribute("href")

                    if not href:
                        print(f"FAILED: Empty link for {destination.name}")
                        skipped_or_failed += 1
                        continue

                    # Resolve relative URLs using the current page.
                    from urllib.parse import urljoin
                    file_url = urljoin(page.url, href)

                    if save_download(context.request, file_url, destination):
                        downloaded += 1
                    else:
                        skipped_or_failed += 1

                    time.sleep(DELAY_SECONDS)

            print(
                f"Page {page_number}: "
                f"{new_dates_on_page} new weekly records found."
            )

            
            # PBS uses a custom JavaScript pagination button.
            next_button = page.locator("#nextPage")

            print("Next button count:", next_button.count())

            if next_button.count() == 0:
                print("The Next button is absent from the current page DOM.")

                print(
                    "Report table found:",
                    page.locator("#reportTable").count()
                )

                print(
                    "Page label found:",
                    page.locator("#pageNumber").count()
                )

                break

            print("Next button visible:", next_button.is_visible())
            print("Next button HTML:", next_button.evaluate("(el) => el.outerHTML"))

            # Stop if the website marks the button as disabled.
            button_class = next_button.get_attribute("class") or ""

            if (
                next_button.is_disabled()
                or "disabled" in button_class.lower().split()
                or (
                    next_button.get_attribute("aria-disabled") or ""
                ).lower() == "true"
            ):
                print("Reached the last page.")
                break

            # Record the current page number before clicking.
            page_label = page.locator("#pageNumber")
            old_page_label = page_label.inner_text().strip()

            print(f"Moving from {old_page_label} to the next page...")

            # Trigger the custom JavaScript handler without requiring
            # the button to be visually displayed.
            next_button.evaluate("(el) => el.click()")

            # Wait until the website's JavaScript updates pagination.
            try:
                page.wait_for_function(
                    """(oldLabel) => {
                        const label = document.querySelector('#pageNumber');
                        return label && label.innerText.trim() !== oldLabel;
                    }""",
                    arg=old_page_label,
                    timeout=15000,
                )
            except Exception:
                print("Page number did not change after clicking Next.")
                break

            # Allow the table rows to finish updating.
            page.wait_for_timeout(500)

            page_number += 1


        
        browser.close()

    print("\n========== SUMMARY ==========")
    print(f"Files downloaded or already present: {downloaded}")
    print(f"Failed or missing links: {skipped_or_failed}")
    print(f"Output folder: {BASE_DIR.resolve()}")


def await_disabled(locator):
    """Return True if a pagination button is disabled."""
    try:
        if locator.is_disabled():
            return True
    except Exception:
        pass

    try:
        if (locator.get_attribute("aria-disabled") or "").lower() == "true":
            return True
        if "disabled" in (locator.get_attribute("class") or "").lower():
            return True
    except Exception:
        pass

    return False


if __name__ == "__main__":
    main()
