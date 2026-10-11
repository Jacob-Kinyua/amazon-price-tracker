import os
import re
from decimal import Decimal, InvalidOperation
from html import escape
from urllib.parse import urlparse

import psycopg
import requests
import resend
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, render_template, request

load_dotenv()

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

HEADERS = {
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "User-Agent": os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36",
    ),
}


def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured.")

    return psycopg.connect(DATABASE_URL)


def send_price_alert(
    email, product_name, price, target_price, product_url
):
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("MY_EMAIL")

    if not api_key or not sender:
        raise RuntimeError("Resend email settings are missing.")

    resend.api_key = api_key

    safe_name = escape(product_name)
    safe_url = escape(product_url, quote=True)

    return resend.Emails.send({
        "from": sender,
        "to": [email],
        "subject": f"Price alert: {product_name}",
        "html": f"""
            <h2>Amazon Price Alert</h2>
            <p>The price of <strong>{safe_name}</strong>
            is now <strong>${price:.2f}</strong>.</p>
            <p>Your target price is ${target_price:.2f}.</p>
            <p>You could save ${target_price - price:.2f}
            compared with your target.</p>
            <p><a href="{safe_url}">View product on Amazon</a></p>
        """,
    })



def check_price(product_url):
    # Extract the ASIN from the Amazon product URL.
    parsed = urlparse(product_url)

    match = re.search(
        r"/(?:dp|gp/product)/([A-Z0-9]{10})",
        parsed.path,
        re.IGNORECASE
    )

    if not match:
        raise ValueError(
            "Could not find an ASIN in the Amazon product URL."
        )

    asin = match.group(1).upper()

    # Read the API key from the environment.
    api_key = os.getenv("SCRAPINGDOG_API_KEY")

    if not api_key:
        raise RuntimeError(
            "SCRAPINGDOG_API_KEY is not configured."
        )

    # Request product data from Scrapingdog.
    api_url = "https://api.scrapingdog.com/amazon/product"

    params = {
        "api_key": api_key,
        "asin": asin,
        "domain": "com",
        "country": "us",
    }

    response = requests.get(
        api_url,
        params=params,
        timeout=60
    )

    if response.status_code != 200:
        raise ValueError(
            f"Scrapingdog request failed with status "
            f"{response.status_code}."
        )

    data = response.json()

    # Extract the product title and price.
    product_name = data.get("title")
    price_text = data.get("price")

    if not product_name:
        raise ValueError(
            "Scrapingdog did not return a product title."
        )

    if not price_text:
        raise ValueError(
            "Scrapingdog did not return a product price."
        )

    # Convert a price such as "$1,849.99" into a Decimal.
    price_match = re.search(
        r"\d[\d,]*(?:\.\d{1,2})?",
        str(price_text)
    )

    if not price_match:
        raise ValueError(
            f"Could not parse the returned price: {price_text}"
        )

    current_price = Decimal(
        price_match.group().replace(",", "")
    )

    return {
        "product_name": product_name,
        "current_price": current_price,
        "product_url": product_url,
    }



def save_tracking_request(
    email, product_url, target_price, daily_monitoring, result
):
    with get_db_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO public.tracked_products (
                email,
                product_url,
                product_name,
                target_price,
                last_price,
                last_checked,
                daily_monitoring,
                alert_sent,
                active
            )
            VALUES (%s, %s, %s, %s, %s, NOW(), %s, FALSE, %s)
            RETURNING id
            """,
            (
                email,
                product_url,
                result["product_name"],
                target_price,
                result["current_price"],
                daily_monitoring,
                daily_monitoring,
            ),
        ).fetchone()

    return row[0]


def mark_alert_sent(product_id):
    """Record that the one-time price alert was sent."""
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE public.tracked_products
            SET alert_sent = TRUE
            WHERE id = %s
            """,
            (product_id,),
        )





def get_products_to_monitor():
    """Retrieve active products that have daily monitoring enabled."""
    with get_db_connection() as conn:
        products = conn.execute(
            """
            SELECT
                id,
                email,
                product_url,
                product_name,
                target_price,
                alert_sent
            FROM public.tracked_products
            WHERE active = TRUE
              AND daily_monitoring = TRUE
            ORDER BY id
            """
        ).fetchall()

    return products


def update_product_price(product_id, current_price):
    """Update a product's latest price and check timestamp."""
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE public.tracked_products
            SET last_price = %s,
                last_checked = NOW()
            WHERE id = %s
            """,
            (current_price, product_id),
        )



def monitor_prices():
    """Check prices and send one alert per tracking request."""
    products = get_products_to_monitor()

    print(f"Found {len(products)} products to monitor.")

    for product in products:
        product_id = product[0]
        email = product[1]
        product_url = product[2]
        product_name = product[3]
        target_price = product[4]
        alert_sent = product[5]

        try:
            result = check_price(product_url)
            current_price = result["current_price"]

            update_product_price(product_id, current_price)

            print(
                f"Product {product_id}: "
                f"${current_price:.2f} — price updated."
            )

            if current_price <= target_price and not alert_sent:
                send_price_alert(
                    email,
                    product_name or result["product_name"],
                    current_price,
                    target_price,
                    product_url,
                )

                mark_alert_sent(product_id)
                print(f"Product {product_id}: price alert sent.")

        except Exception as error:
            print(f"Product {product_id}: monitoring failed — {error}")



def send_initial_alert_if_needed(email, target_price, result, tracking_id):
    current_price = result["current_price"]

    if current_price <= target_price:
        send_price_alert(
            email=email,
            product_name=result["product_name"],
            price=current_price,
            target_price=target_price,
            product_url=result["product_url"],
        )

        result["alert_sent"] = True
        mark_alert_sent(tracking_id)
        return True

    result["alert_sent"] = False
    return False


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    success = None

    email = ""
    product_url = ""
    target_price = "1050.00"

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        product_url = request.form.get("product_url", "").strip()
        target_price = request.form.get("target_price", "").strip()

        daily_monitoring = (
            request.form.get("daily_monitoring") == "yes"
        )

        try:
            if not re.fullmatch(
                r"[^@\s]+@[^@\s]+\.[^@\s]+", email
            ):
                raise ValueError("Enter a valid email address.")

            parsed = urlparse(product_url)

            allowed_hosts = {
                "amazon.com",
                "www.amazon.com",
                "smile.amazon.com",
            }

            if (
                parsed.scheme != "https"
                or parsed.hostname not in allowed_hosts
                or not parsed.path
                or parsed.username
                or parsed.password
            ):
                raise ValueError(
                    "Enter a valid HTTPS Amazon.com product URL."
                )

            try:
                target = Decimal(target_price)
            except InvalidOperation:
                raise ValueError(
                    "Enter a valid target price."
                ) from None

            if not target.is_finite() or target <= 0:
                raise ValueError(
                    "Target price must be greater than zero."
                )

            # Check the current price.
            result = check_price(product_url)
            result["target_price"] = target
            result["difference"] = (
                target - result["current_price"]
            )
            result["alert_sent"] = False

            # Save the tracking request.
            tracking_id = save_tracking_request(
                email,
                product_url,
                target_price,
                daily_monitoring,
                result,
            )

            # Send an immediate alert if the target is already met.
            send_initial_alert_if_needed(
                email=email,
                target_price=target,
                result=result,
            )

            if daily_monitoring:
                success = (
                    "Your product has been saved for daily monitoring."
                )
            else:
                success = (
                    "Your price check is complete. Daily monitoring "
                    "is disabled for this request."
                )

        except (
            ValueError,
            requests.RequestException,
        ) as exc:
            error = str(exc)

        except Exception:
            app.logger.exception("Price tracking request failed")
            error = (
                "Something went wrong while saving your product "
                "or sending an email. Check your server logs."
            )

    return render_template(
        "index.html",
        result=result,
        error=error,
        success=success,
        email=email,
        product_url=product_url,
        target_price=target_price,
    )


if __name__ == "__main__":
    app.run(debug=True)