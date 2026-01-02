import time
from playwright.sync_api import sync_playwright

def verify_game():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Start the frontend dev server if not running?
        # I assume the environment has a running server or I need to start one.
        # Usually I should visit localhost:3000.
        try:
            page.goto("http://localhost:3000")
        except:
            print("Could not connect to localhost:3000")
            return

        print("Page loaded")

        # Check for title text
        if page.get_by_text("It's Fast. It's Simple.").is_visible():
            print("Title visible")
        else:
            print("Title NOT visible")

        # Check for bugs (Green cells)
        # We look for divs with background-color containing the green rgba
        # Green: rgba(34, 197, 94, 0.8)

        print("Waiting for bugs...")
        # Poll for 5 seconds
        found_bug = False
        found_rocket = False

        for _ in range(20):
            time.sleep(0.5)
            # Check for styles directly
            # We iterate over all grid cells (divs with inline style background-color)
            # This might be slow if we query all, let's execute js

            result = page.evaluate("""() => {
                const cells = document.querySelectorAll('div[style*="background-color"]');
                let bug = false;
                let rocket = false;
                for (const cell of cells) {
                    const bg = cell.style.backgroundColor;
                    if (bg.includes('34, 197, 94')) bug = true; // Green
                    if (bg.includes('249, 115, 22') && !bg.includes('0.5')) rocket = true; // Orange (full opacity, approx)
                    // Note: Rocket opacity is 1, but existing cells are orange with variable opacity.
                    // Existing cells: rgba(249, 115, 22, X) where X <= 0.5
                    // Rocket: rgba(249, 115, 22, 1)
                }
                return { bug, rocket };
            }""")

            if result['bug']: found_bug = True
            if result['rocket']: found_rocket = True

            if found_bug and found_rocket:
                break

        if found_bug:
            print("SUCCESS: Bugs detected.")
        else:
            print("FAILURE: No bugs detected.")

        if found_rocket:
            print("SUCCESS: Rockets detected.")
        else:
            print("FAILURE: No rockets detected (might be random chance or logic issue).")

        # Check Mobile Padding Class
        # The section should have pt-32
        # We find the section containing the text
        # section = page.locator("section").first
        # classes = section.get_attribute("class")
        # if "pt-32" in classes:
        #    print("Mobile padding pt-32 detected.")

        browser.close()

if __name__ == "__main__":
    verify_game()
