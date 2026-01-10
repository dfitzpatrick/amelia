from __future__ import annotations
from typing import TYPE_CHECKING
from pydantic import BaseModel, field_validator, ValidationError
from bs4 import BeautifulSoup
from decimal import Decimal, InvalidOperation
from io import BytesIO
import aiohttp
from urllib.parse import urlsplit, unquote
import posixpath
import re

LOCATION_REGEX = re.compile(r'(?<=located ).*')

if TYPE_CHECKING:
	from bs4.element import Tag

MINIMUM_PRICE = 3000

class Classified(BaseModel):
	data_id: int
	title: str 
	body: str 
	url: str 
	price: Decimal | None = None
	location: str | None = None
	excerpt: str | None = None
	thumbnails: list[str] = []

	@field_validator("price", mode="before")
	def clean_price_and_check_above_minimum_price(cls, value: str) -> Decimal:
		if isinstance(value, str):
			cleaned = value.replace("$", "").replace(",", "")
			try:
				cleaned = Decimal(cleaned)
				if cleaned < MINIMUM_PRICE:
					raise ValueError(f"Below minimum price of {MINIMUM_PRICE}")
				return cleaned
			except InvalidOperation:
				raise ValueError("Not a properly formatted price")
		else:
			raise ValueError("Not the expected type")
		
	@property
	def price_string(self) -> str:
		if self.price:
			return f"${self.price:,.0f}"
		return "No Price Listed"

	@property
	def images(self) -> list[str]:
		return [t.replace('thumbnail', 'medium') for t in self.thumbnails]
	
	@property
	def image_filenames(self) -> list[str]:
		container = []
		for img in self.images:
			path = urlsplit(img).path
			decoded = unquote(path)
			filename = posixpath.basename(decoded)
			container.append(filename)
		return container

async def download_images(img_urls: list[str]) -> list[tuple[str, BytesIO]]:
	container = []
	for img in img_urls:
		path = urlsplit(img).path
		decoded = unquote(path)
		filename = posixpath.basename(decoded)

		async with aiohttp.ClientSession() as session:
			async with session.get(img) as response:
				data = await response.read()
				data = BytesIO(data)
				container.append((filename, data))
	return container

def get_image_urls(html: str) -> list[str]:
	container = []
	soup = BeautifulSoup(html, "html.parser")
	images = soup.find_all("img", {"class": "t-li"})
	for img in images:
		container.append(img['src'])
	return container

def get_classifieds(html: str) -> list[Classified]:
	container = []
	soup = BeautifulSoup(html, "html.parser")
	listings = soup.find_all("div", {"class": "classified_single"})
	for result in listings:
		data_id = result.get("data-adid")
		header = result.find("a", class_="listing_header")
		link = "https://www.barnstormers.com" + header['href']
		title = header.text
		body = result.find("span", class_="body").text
		price = result.find("span", class_="price")
		price = price.text if price else None
		location = None
		loc = result.find("span", class_="contact")
		if loc:
			loc = loc.text
			match = re.search(LOCATION_REGEX, loc)
			if match:
				location = match.group(0).strip()

		thumbnails = [t['src'] for t in result.find_all("img", {"class": "thumbnail"})]

		try:
			o = Classified(
				data_id=data_id,
				title=title,
				body=body,
				url=link,
				location=location,
				price=price,
				thumbnails=thumbnails
			)
			container.append(o)
		except ValidationError as e:
			# Not well formed or doesn't meet business rules
			continue

	return container


