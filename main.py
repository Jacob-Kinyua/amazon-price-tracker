from bs4 import BeautifulSoup
from dotenv import load_dotenv
import smtplib
import requests
import os

load_dotenv()

test_api = "https://appbrewery.github.io/instant_pot/"

response = requests.get(url=test_api)
context = response.text

soup = BeautifulSoup(context, "html.parser")

whole_num_price = soup.find("span", class_="a-price-whole")
decimal_price = soup.find("span", class_="a-price-fraction")
whole_num_price = int(whole_num_price.getText().split(".")[0])
decimal_price = int(decimal_price.getText()) / 100

product_name = soup.find("span", id="productTitle")
product_name = product_name.getText()
total_price = whole_num_price + decimal_price

message = f"Subject:Low Price Alwer\n\nLow Price alert for {product_name}:{total_price}.Buy Now!"

if total_price < 100:
    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(user=os.getenv("MY_EMAIL"), password=os.getenv("MY_PASSWORD"))
        connection.sendmail(
            from_addr= os.getenv("MY_EMAIL"),
            to_addrs= "muskins18@gmail.com",
            msg=message.encode("utf-8")
        )
