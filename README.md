# PriceWatch 🛒

PriceWatch is a web application that helps users track Amazon product prices and receive email notifications when a product's price reaches or falls below their target price. By automating price checks, PriceWatch makes it easier to monitor products and identify potential savings without manually checking Amazon every day.

## Features

- **Product price tracking:** Submit an Amazon product URL and specify a target price.
- **Automated price checks:** Retrieve current product prices using the Scrapingdog API.
- **Email notifications:** Receive an email when a product's price reaches or drops below the specified target.
- **One-time price alerts:** Send only one alert per tracking request, preventing repeated notifications for the same target price.
- **Persistent storage:** Store product details, target prices, current prices, and alert statuses in a PostgreSQL database.
- **Daily monitoring:** Automatically check tracked products through a scheduled job on Render.
- **Web interface:** Submit and track products through a Flask-powered web application.

## How It Works

1. A user submits an Amazon product URL, email address, and target price through the web interface.
2. PriceWatch extracts the product's ASIN from the URL and requests its current price and title through Scrapingdog.
3. The tracking request and initial product information are saved in Supabase.
4. A daily scheduled job retrieves active products that have daily monitoring enabled.
5. PriceWatch checks each product's current price and updates the database.
6. If the current price is at or below the target price and an alert has not already been sent, PriceWatch sends an email through Resend.
7. The database records that the alert was sent, preventing subsequent monitoring runs from sending duplicate alerts for that tracking request.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core application logic and price monitoring |
| Flask | Web application and HTTP request handling |
| HTML and Jinja2 | Web interface and dynamic page rendering |
| CSS | Styling and responsive presentation |
| Scrapingdog API | Retrieving Amazon product information and prices |
| Supabase PostgreSQL | Storing product tracking requests and monitoring state |
| Psycopg | Connecting Python to PostgreSQL |
| Resend | Sending email notifications |
| Requests | Making HTTP requests to external APIs |
| python-dotenv | Loading environment variables during local development |
| Gunicorn | Production WSGI server for Flask |
| Render Web Services | Hosting the web application |
| Render Cron Jobs | Running automated daily price monitoring |
| Git and GitHub | Version control and source code hosting |

## Project Structure

```text
amazon-price-tracker/
├── app.py
├── requirements.txt
├── .gitignore
├── templates/
│   └── index.html
└── static/
    └── style.css
```

- `app.py` — Contains the Flask application, product price lookup, database operations, email notifications, and monitoring functions.
- `requirements.txt` — Lists the Python dependencies required to run the application.
- `.gitignore` — Excludes sensitive configuration files and local development artifacts.
- `templates/index.html` — Defines the web interface using HTML and Jinja2.
- `static/style.css` — Contains the application's styling.

## Getting Started

### Prerequisites

Before running PriceWatch locally, make sure you have:

- Python 3 installed.
- Git installed.
- A Supabase project with PostgreSQL access.
- A Scrapingdog API key.
- A Resend account and verified sender email address.

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd amazon-price-tracker
```

Replace the placeholder with your GitHub repository URL.

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate the environment.

**Linux/macOS:**

```bash
source .venv/bin/activate
```

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=your_supabase_postgresql_connection_string
SCRAPINGDOG_API_KEY=your_scrapingdog_api_key
RESEND_API_KEY=your_resend_api_key
MY_EMAIL=your_verified_resend_sender_email
```

Replace the placeholder values with your actual credentials.

**Security:** Never commit `.env` to GitHub or expose your API keys in public repositories. Configure the same variables in your deployment environment when hosting the application.

### 5. Set Up the Database

Create the `public.tracked_products` table in your Supabase SQL Editor:

```sql
CREATE TABLE public.tracked_products (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL,
    product_url TEXT NOT NULL,
    product_name TEXT,
    target_price NUMERIC(10, 2) NOT NULL
        CHECK (target_price > 0),
    last_price NUMERIC(10, 2),
    last_checked TIMESTAMPTZ,
    daily_monitoring BOOLEAN NOT NULL DEFAULT TRUE,
    alert_sent BOOLEAN NOT NULL DEFAULT FALSE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tracked_products_active
ON public.tracked_products (active, daily_monitoring);

ALTER TABLE public.tracked_products
ENABLE ROW LEVEL SECURITY;
```

The application connects directly to PostgreSQL using Psycopg. Keep database credentials private and ensure the database connection uses appropriate security settings.

### 6. Run the Application Locally

Start the Flask development server:

```bash
python app.py
```

Open the local address displayed in your terminal, typically:

```text
http://127.0.0.1:5000
```

Submit an Amazon product URL, your email address, and a target price to test product tracking.

## Daily Price Monitoring

PriceWatch uses the `monitor_prices()` function to check tracked products and send eligible alerts.

You can manually trigger a monitoring run from the project directory:

```bash
python -c "from app import monitor_prices; monitor_prices()"
```

The function:

- Retrieves products with `active = TRUE` and `daily_monitoring = TRUE`.
- Requests each product's current price through Scrapingdog.
- Updates `last_price` and `last_checked` in Supabase.
- Sends an email when the current price is at or below the target and `alert_sent` is `FALSE`.
- Sets `alert_sent` to `TRUE` after a successful alert.

Individual product failures are logged so that one unsuccessful request does not prevent the application from attempting to process other products.

## Deployment

PriceWatch is designed to run on Render.

### Web Service

The Flask application can be deployed as a Render Web Service connected to the GitHub repository.

Typical build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app
```

Configure the required environment variables in the Render dashboard.

### Scheduled Cron Job

A separate Render Cron Job runs the monitoring function automatically.

Command:

```bash
python -c "from app import monitor_prices; monitor_prices()"
```

Configure the desired daily schedule in Render. Cron schedules use UTC, so choose the schedule with the intended local time in mind.

The Cron Job requires the same database and API environment variables as the web service.

## Database Fields

| Column | Description |
|---|---|
| `id` | Unique tracking request identifier |
| `email` | Email address for price notifications |
| `product_url` | Amazon product URL |
| `product_name` | Retrieved product title |
| `target_price` | Price threshold specified by the user |
| `last_price` | Most recently retrieved price |
| `last_checked` | Timestamp of the most recent successful price check |
| `daily_monitoring` | Whether daily price monitoring is enabled |
| `alert_sent` | Whether the one-time alert has been sent successfully |
| `active` | Whether the request is included in monitoring |
| `created_at` | Timestamp when the tracking request was created |

## Limitations and Considerations

- Price availability and accuracy depend on the data returned by Scrapingdog.
- API quotas, service availability, and request limits may affect monitoring.
- Email delivery depends on Resend and the validity of the recipient address.
- PriceWatch currently sends one alert per tracking request rather than repeated alerts for subsequent price drops.
- The application requires valid API credentials and an accessible PostgreSQL database.
- Hosting, API usage, and email services may incur costs depending on the selected plans and usage.

## Future Improvements

Potential enhancements include:

- A dashboard for viewing and managing tracked products.
- The ability to deactivate or delete tracking requests.
- Product price history and historical price charts.
- Support for additional retailers.
- Improved retry handling and monitoring failure notifications.
- User authentication and account-based product management.
- More advanced price trends and savings analysis.

## License

Choose a license before distributing or accepting contributions to this project. If no license has been added, all rights remain reserved by the copyright holder by default.

---

**PriceWatch** — Track prices automatically. Get notified when the price is right.
