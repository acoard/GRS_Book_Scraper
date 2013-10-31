import sys
sys.path.append("/Users/acoard/scrapy") #allows us to import Scrapy on school computers.
sys.path.append("/Users/acoard/beautifulsoup")
sys.path.append("/Users/acoard/pdfminer")
from bs4 import BeautifulSoup
#import scrapy
import urllib
import urllib2
import re
import datetime
import mechanize
import json
import time

from api_keys import *


from cStringIO import StringIO
from pdfminer.pdfinterp import PDFResourceManager, process_pdf
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams


#ISBN http://stackoverflow.com/questions/4893908/how-to-get-isbn-number-from-a-book-title-and-author-programmatically

regex_ISBN = re.compile('978(?:-?\d){10}')

def get_soup(url):
	html = urllib2.urlopen(url).read()
	return BeautifulSoup(html)

def to_txt(pdf_path):
    input_ = file(pdf_path, 'rb')
    output = StringIO()

    manager = PDFResourceManager()
    converter = TextConverter(manager, output, laparams=LAParams())
    process_pdf(manager, converter, input_)

    return output.getvalue() 

def get_PDF(pdf_path, pdf_name):
	print "Downloading PDF."
	u = urllib2.urlopen(pdf_path)
	f = open(pdf_name, 'w+b')
	f.write(u.read())

def lookup_ISBN(isbn):
	url = 'https://www.googleapis.com/books/v1/volumes?q=isbn:'
	url += isbn
	key =  "&key=" + Google_API_Key
	url += key

	data = urllib2.urlopen(url).read()
	data = json.loads(data)

	if data["totalItems"] >= 1:
		d = {}
		volumeInfo = data["items"][0]["volumeInfo"]
		if "title" in volumeInfo:
			d["title"] = volumeInfo["title"]
		if "authors" in volumeInfo:
			d["authors"] = volumeInfo["authors"]
		if "webReaderLink" in ["webReaderLink"]:
			d["link"] = data["items"][0]["accessInfo"]["webReaderLink"]
		d["isbn"] = isbn
		return d
	else: #if no info from google, just return the isbn.
		return False


def scrape_Blegen():
	"""
	This function properly scrapes the website, but there is a problem.  I can only get it to search the first and second pages.  
	The URLs I'm going to each time are different, but the Blegen URL system is as byzantine as it gets.

	As of now, the code is set to only get the first two pages, which will hopefully be adequate on a monthly run.

	"""


	Blegen_URL = 'http://ambrosia.ascsa.edu.gr:8991/F/?func=find-b&request=blg1013+or+gen1013+or+bsa1013&find_code=WRD&adjacent=N'
	html = urllib2.urlopen(Blegen_URL).read()
	soup = BeautifulSoup( html )
	tables = soup.find_all('table')
	data = scrape_Blegen_sub(soup)
	is_another_page = bool(soup.find("img", {"alt":"Next Page"}))

	#THE BELOW CODE IS PARTIALLY WORKING, APPEARS TO GO TO THE SECOND PAGE AND THEN JUST REPEAT.
	#data[19] is the same as data[60]
	i = 1
	while is_another_page and (data[-1]["date"] >= datetime.date.today().year):
		# print "Page : " + str(i)
		new_page_link = tables[3].a.get('href')
		# print "Link : " + str(new_page_link)
		new_page = urllib2.urlopen(new_page_link).read()
		soup = BeautifulSoup ( new_page )
		tables = soup.find_all('table')
		is_another_page = bool(soup.find("img", {"alt":"Next Page"}))
		data += scrape_Blegen_sub(soup)
		i += 1
		if i == 2: break

	return data

def scrape_Blegen_sub(soup):
	#Only to be called by scrape_Blegen.
	tables = soup.find_all('table')
	table = tables[4] #Tables 0-3 are all navbar layout, [4] is content.
	output = []
	for tr in table.find_all('tr'):
		d = {}
		tr = tr.text.split('\n')
		author = tr[3].split(u'\xa0')[0].strip()
		title = tr[4].strip()#.split(u'\xa0')[0]
		year = tr[6].strip()
		d["author"] = author
		d["title"] = title
		d["date"] = year
		output.append(d)
	if output[0] == {'title' : 'Title', 'author' : 'Author', 'date' : 'Year'}: #technical debt
		del output[0]
	return output

def scrape_JRA(amazonLookup=False):
	"""Returns a dictionary that contains both ISBNs, 
	and if the item exists on amazon a search to that item.

	This function takes a LONG time to call mostly because of 
	all the calls to create_amazon_search().
	With 137 calls to c_a_s, it took 4 minutes 18 seconds.  Approx 2 seconds a call.
	"""
	#Returns a list of ISBNs.
	#TODO: Transform ISBNs to Author/Book info.
	JRA = 'http://www.journalofromanarch.com/booksreceived.html'
	JRA_base = 'http://www.journalofromanarch.com/'
	#First, must find links on page to the PDFs.  Find the most recent one, download it.
	html = urllib2.urlopen(JRA).read()
	soup = BeautifulSoup(html)
	links = soup.find(id="content").find_all('a')
	
	#Check that each link ends with .pdf
	links_to_pdf = []
	for link in links:
		is_pdf = bool(link.get('href')[-3:] == 'pdf')
		if is_pdf:
			links_to_pdf.append(link.get('href'))
	
	#The first item in the list is the most recent, so disregard the others.
	first_link = links_to_pdf[0]
	recent_pdf = JRA_base + first_link #affix pdf extension to domain name.
	u = urllib2.urlopen(recent_pdf)
	
	#PDFminer can't work off in memory files.  So, download the file then parse with to_txt()
	f = open(str(first_link), 'r+b') #taking str removes the u' unicode
	f.write(u.read())

	text = to_txt(str(first_link))
	text = text.split('USA\n')[1] #skips header
	regex = re.compile('978(?:-?\d){10}') #ISBN
	
	list_of_isbns = regex_ISBN.findall(text)
	isbns_without_dashes = [] #To search Google ISBNs must be just digits.
	for isbn in list_of_isbns:
		isbns_without_dashes.append(isbn.replace('-', ''))


	#return regex_ISBN.findall(text)	 #IF this isn't working return to regex.findall(text)
	if amazonLookup:
		output = []
		for isbn in isbns_without_dashes:
			d = {}
			d["isbn"] = isbn
			amazon = create_amazon_search(isbn)
			if amazon: 
				d["amazon"] = amazon
			output.append(d)
		return output
	else:
		return isbns_without_dashes

def create_amazon_search(isbn):
	"""Takes an ISBN and generates an amazon query.
	TODO: If the search exists, follow the link and get the price."""
	print "c_a_s Being called."
	url = 'http://www.amazon.ca/gp/search?index=books&linkCode=qs&keywords='
	url += isbn
	soup = get_soup(url)
	#Check to see if a 'no results found' message is displayed.
	if "noResultsTitle" in str(soup.findAll("h1")):
		return False
	else:
		return url

def scrape_Sackler():
	#As this bot will run monthly, the bot must go through EACH of the 4 weekly pages and add them to the list.
	URL = 'http://www.bodleian.ox.ac.uk/sackler/collections/accessions/monograph-accessions'
	html = urllib2.urlopen(URL).read()
	soup = BeautifulSoup( html )
	content_div = BeautifulSoup(str(soup.find_all(attrs={'class':'content'}))) #parse by BeautifulSoup again in order to search it next step.
	
	#Pair links to PDFs with their weeks
	linksInTable = []
	for link in content_div.find_all('a'):
		linksInTable.append((link.text, link.get('href'))) #('wk xx', 'url.') nb: some wks are malformed.
	
	#Download last 4 links.	
	download_urls = []
	for i in [1,2,3,4]: 
		download_urls.append(linksInTable[len(linksInTable) - i][1])

	pdfs_to_scrape = []
	for i in xrange(len(download_urls)):
		pdf_name = download_urls[i].split('=')[1] + '.pdf'
		get_PDF(download_urls[i], pdf_name)

		pdfs_to_scrape.append(pdf_name)
		
		#PDF downloaded, begin scraping:
		text = to_txt(pdf_name)
		
		#REALLY MALFORMED.  EXPERIMENT WITH pdf2txt.py - properly setup via setup.py
	
	#After using pdf2txt.py - 
	#f = open('output.html')
	#html =  f.read()
	#soup = BeautifulSoup( html ) #spaces seem necssary?

	#divs = soup.find_all('div')
	#author_style = 'position:absolute; border: textbox 1px solid; writing-mode:lr-tb; left:181px'
	#book_style = 'position:absolute; border: textbox 1px solid; writing-mode:lr-tb; left:263px' #double check
	#list_of_authors = []
	#for div in divs:
		#if author_style in div.attrs['style']:
			#list_of_authors.append(div)

	#Problem: This would create two lists, of authors and books, and since I'm not sure the two line up perfectly (or will later)...
	#Maybe grab books off of something like 30 characters after author?
		
	return pdfs_to_scrape
	
def scrape_Prop():
	"""Function is fully operational."""
	url = 'http://www.propylaeum.de/en/altertumswissenschaften/new-acquisitions/'
	br = mechanize.Browser()
	br.open(url)
	br.select_form(nr=1)
	#Form values
	br["EPOCHE"] = [".*"] #all time periods
	br["RAUM"] = ["G_rr"]  # Region: Roman Empire
	form_response = br.submit()
	
	soup = BeautifulSoup(form_response)
	output = scrape_Prop_sub(soup)

	#Check to see if there is another page of results:
	there_is_another_page = bool(soup.find_all('a')[-1].text.strip() == 'Anzeige weiterer Titel')
	while there_is_another_page:
		#follow link, repeat scraping, add to output
		base_url = 'http://mdz1.bib-bvb.de/'
		page_link = soup.find_all('a')[-1].get('href')
		url = base_url + page_link
		response = br.open(url)
		soup = BeautifulSoup(response)
		output += scrape_Prop_sub(soup)
		there_is_another_page = bool(soup.find_all('a')[-1].text.strip() == 'Anzeige weiterer Titel')
	return output

def scrape_Prop_sub(soup):
	#Function to be called in scrape_Prop() ONLY.  
	p_tags = soup.body.find_all('p')
	#Lots of malformed <p> tags, so check to make sure they aren't empty. 
	#NB: len(<p></p>) == 0, I think this is BeautifulSoup doing this.
	paras = [p for p in p_tags if len(p) > 1]
	#Create a list of dictionaries of author:title and return it.
	output = []
	for i in paras:
		d = {}
		d["author"] = i.b.text
		d["title"] = i.b.next_sibling.b.text
		d["ISBN"] = regex_ISBN.findall(str(i))
		output.append(d)
	return output

def scraped_results():
	#Amalgamtes all the results into one function.
	#Prop's website is 404ing, I think it's their end - uncomment when it's back up.
	output = scrape_Blegen() + scrape_Prop()
	return output

def query_google():
	#Limits calls to google to stop 403ing.
	output = []
	for isbn in isbns:
		x = lookup_ISBN(isbn)
		if x: 
			output.append(lookup_ISBN(isbn))
		time.sleep(1)
	return output
