#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
selenium ajax_driver allows to wait for ajax-driven page 
(google flights, in this case) to be loaded.
'''
from bs4 import BeautifulSoup
import html2text
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from lxml import html
import json
from csv import DictWriter
import warnings

FAILS = 0 # tickets failed to parse

def _flightRequest(search, maxStops=None):
	''' URL Builder

	http://www.google.com/flights/#search | The website URL
	f=ORD,MDW,MKE | Origin Airport(s) (from)
	t=WAS | Destination Airport(s) (to)
	d=2011-11-14 | Departure Date (depart)
	r=2011-11-17 | Return Date (return)
	a=AA,CO,WN,UA | Air Carrier(s)(airline)
	c=DFW,IAH | Connection Cities (connect)
	s=1 | Maximum Stops (stops)
	olt=0,900 | Outbound Landing Time Range – Min-Max in minutes from 0:00 (outbound landing – rival time range)
	itt=840,1440 | Inbound Takeoff Time Range – Min-Max in minutes from 0:00 (inbound takeoff – departure time range)
	tt=o/m   |one-way/multiway
	'''
	From, To, DateStart = search.values() 

	burl = "https://www.google.com/flights/#search"
	url_template = '{burl};f={From};t={To};d={departure};tt=o'
	
	url = url_template.format(burl=burl, From=';'.join(From), To=';'.join(To),
							  departure=DateStart )
	
	if maxStops:
		url+= ';s={}'.format(maxStops)

	return url


def _parseCard(card):
	'''parse flight card,
	getting company, flight timing and date, etc.
	returns flight info dictionary'''
	global FAILS

	try:
		parse = card.findAll(attrs={'style': "display:none"})
		for p in parse:
			p.decompose()
		print(html2text.html2text(card.get_text()))
		# data = {'link': card.xpath('./@href')[0],
		# 	'price': card.xpath('./div[1]/div/div')[0].text,
		# 	'departure': card.xpath('./div[2]/div/span[1]')[0].text,
		# 	'arrival': card.xpath('./div[2]/div/span[2]')[0].text,
		# 	'duration': card.xpath('./div[3]/div[1]')[0].text,
		# 	'stops': card.xpath('./div[4]/div[1]')[0].text,
		# 	'airline': card.xpath('./div[2]/div[last()]')[0].text_content()
		# 	}

	except Exception as inst:
		print (inst)
		print('Failed to parse card...')
		FAILS+=1
		data = {}
	#return data 
	return {}


def _storeFlights(flights, path='test_search.csv'):
	'''stores flights in csv'''
	with open('test_search.csv', 'w') as csvfile:
		headers = ['link', 'price', 'departure', 'arrival', 'duration', 'airline', 'stops']

		writer = DictWriter(csvfile, fieldnames=headers)
		writer.writeheader()
		
		for f in flights:
			writer.writerow({k:v.encode('utf8') for k,v in f.items()})


class flightCollector():
	'''flight data collector'''

	def __init__(self, path="misc/chromedriver"):
		options = webdriver.ChromeOptions()
		options.add_argument('headless')
		self.browser = webdriver.Chrome(executable_path=path, chrome_options=options)


	def searchAll(self, searches, timeSleep=3, **kwargs):	
		'''search for all flights for all searches
		NOTE: might be useful to add search name

		Args:
			searches(list): list of dictionaries, defininf search
			timeSleep(int): seconds to sleep TODO: need to define/replace/improve

		Returns:
			list: list of flight dictionaries
		'''

		for search in searches:
			url = _flightRequest(search, **kwargs)
			
			wait = WebDriverWait(self.browser, 20)
			self.browser.get(url)

			#click show all
			showmore = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.gws-flights-results__dominated-link')))
			#showmore.find_element_by_partial_link_text('flights')
			if showmore:
				actions = ActionChains(self.browser)
				bad = 1
				while bad!=0:
					bad+=1
					try:
						self.browser.execute_script("arguments[0].scrollIntoView();", showmore)
					except:
						print("Scrolling failed")
					actions.move_to_element(showmore)
					actions.click(showmore)
					actions.perform()
					try:
						self.browser.find_element_by_css_selector('.gws-flights-results__expanded')
						bad = 0
					except:
						print("Not expanded")
					if(bad>200):
						print("Timed Out")
						exit()

				# wait for results to load
				wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.gws-flights-results__expanded')))

			# PARSING
			#dom = html.fromstring(self.browser.page_source)
			soup = BeautifulSoup(self.browser.page_source, 'html.parser')
			flights = soup.find_all('li', class_ = 'gws-flights-results__result-item')
			
			if len(flights)==0:
				warnings.warn('No flights found. Check your search parameters:\n\n{}'.format(search))
			else:
				print ('Flights found: {}'.format(len(flights)))
				#print (flights[0].prettify())

				#yield _parseCard(flights[0])
				for f in flights:
					#print (f.prettify())
					yield _parseCard(f)


	def close(self):
		self.browser.close()

	## To be redefines -- needs for "with" statement
	# def __enter__(self, **kwargs):  
	# 	self.__init__(self, **kwargs)

	# def __exit__(self):
	# 	self.close()


def main():
	'''sample of data collection routine'''
	
	with open('searches.json','r') as fi: # get all searches in the json
		searches = json.load(fi)['searches']

	fs = flightCollector()
	try:
		flights = fs.searchAll(searches)

		_storeFlights(flights)

		# for f in flights:
		# 	print f
		
		print ('Failed to parse {} flights'.format(FAILS))
		
	except:
		pass
		# fs.close()		
	

if __name__ == '__main__':
	main()