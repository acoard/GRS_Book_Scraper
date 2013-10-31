import gspread
from book_scraper import scraped_results

data = scraped_results()

def populate_Sheet():
	pw = raw_input("Security up in here!\n")
	gc = gspread.login('arcoard@gmail.com', pw)
	worksheet = gc.open_by_key('0AjGzKpQAiIfGdHJpX05VZGp3Q19KVUNoN19BNjAtQnc').sheet1
	worksheet.update_acell('B1', "AUTHOR")
	worksheet.update_acell('D1', "TITLE")

	for index, val in enumerate(data):
		row = str(index + 2)
		worksheet.update_acell('B'+row, val["author"])
		worksheet.update_acell('C'+row, " ~~~ ")
		worksheet.update_acell('D'+row, val["title"])