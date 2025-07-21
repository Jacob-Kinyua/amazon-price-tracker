from bs4 import BeautifulSoup
from dotenv import load_dotenv
import smtplib
import requests
import os

load_dotenv()

headers = {
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "X-Amzn-Trace-Id": os.getenv("AMZN_ID")
}

endpoint = os.getenv("ENDPOINT")

response = requests.get(url=endpoint, headers=headers)
context = response.text
safe_price = 1050

soup = BeautifulSoup(context, "html.parser")
whole_num_price = soup.find("span", class_="a-price-whole")
decimal_price = soup.find("span", class_="a-price-fraction")
whole_num_price = int(whole_num_price.getText().split(".")[0])
decimal_price = int(decimal_price.getText()) / 100

product_name = soup.find("span", id="productTitle")
product_name = product_name.getText()
total_price = whole_num_price + decimal_price

message = f"Subject:Low Price Alwer\n\nLow Price alert for {product_name}:{total_price}.Buy Now!"

if total_price < safe_price:
    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(user=os.getenv("MY_EMAIL"), password=os.getenv("MY_PASSWORD"))
        connection.sendmail(
            from_addr= os.getenv("MY_EMAIL"),
            to_addrs= "muskins18@gmail.com",
            msg=message.encode("utf-8")
        )
