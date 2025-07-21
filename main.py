from bs4 import BeautifulSoup
import requests

test_api = "https://appbrewery.github.io/instant_pot/"

response = requests.get(url=test_api)
context = response.text

soup = BeautifulSoup(context, "html.parser")

whole_num_price = soup.find("span", class_="a-price-whole")
decimal_price = soup.find("span", class_="a-price-fraction")
whole_num_price = int(whole_num_price.getText()[:-1])
decimal_price = int(decimal_price.getText()) / 100

total_price = whole_num_price + decimal_price
print(total_price)

