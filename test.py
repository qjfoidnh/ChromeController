
import logging
import os.path
import sys
import pprint
import time

import astor
import WebRequest

import ChromeController.manager as mgr
import ChromeController

if 'win' in sys.platform:
	crbin = "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"
else:
	crbin = "google-chrome"

def test_creation():
	cr = ChromeController.ChromeRemoteDebugInterface(
		crbin,
		dbg_port=9232,
		enable_gpu=True)

	return

def test_delete_cookies():
	cr = ChromeController.ChromeRemoteDebugInterface(crbin, dbg_port=9232)


	canClear = cr.Network_canClearBrowserCookies()
	print("Can clear cookies: ", canClear)
	assert canClear['result']['result'] == True


	# print(cr)
	resp = cr.Emulation_setVisibleSize(1500, 1000)
	# print("Viewport size", resp)

	print("Navigating to whatarecookies.com")

	try:
		resp = cr.blocking_navigate_and_get_source("http://www.whatarecookies.com/cookietest.asp", timeout=10)
	except Exception as e:
		raise e

	print("Sampling cookies #1")
	cooks1 = cr.Network_getAllCookies()['result']['cookies']
	print("Doing cookie clear")
	res = cr.Network_clearBrowserCookies()
	print("Cookie clear result: ", res)

	print("Sampling cookies #2")
	cooks2 = cr.Network_getAllCookies()['result']['cookies']
	print("Navigating to goat.com")

	try:
		resp = cr.blocking_navigate_and_get_source("http://goat.com", timeout=10)
	except Exception as e:
		raise e

	cooks6 = cr.get_cookies()

	print("Cookies: ", cooks6)
	for cook in cooks6:
		cr.set_cookie(cook)

	print("Set cookies")
	# print("Doing cookie clear")
	# res = cr.Network_clearBrowserCookies()
	# print("Cookie clear result: ", res)
	# print("sleeping 15")
	# time.sleep(15)
	# print("Sampling cookies #3")
	# cooks3 = cr.Network_getAllCookies()['result']['cookies']
	# print("Doing cookie clear")
	# res = cr.Network_clearBrowserCookies()
	# print("Cookie clear result: ", res)
	# print("sleeping 15")
	# time.sleep(15)
	# print("Sampling cookies #4")
	# cooks4 = cr.Network_getAllCookies()['result']['cookies']


	# print("Doing cookie clear")
	# res = cr.clear_cookies()
	# print("Cookie clear result: ", res)
	# print("sleeping 15")
	# time.sleep(15)
	# print("Sampling cookies #4")
	# cooks5 = cr.Network_getAllCookies()['result']['cookies']


	# print()
	# print("Uncleared Cookies (#1):")
	# for cookie1 in cooks1:
	# 	print("	", cookie1)

	# print()
	# print("Cleared cookies (#2):")
	# for cookie2 in cooks2:
	# 	print("	", cookie2)

	# print()
	# print("Navigated and cleared cookies after delay (#3):")
	# for cookie3 in cooks3:
	# 	print("	", cookie3)
	# print()
	# print("Navigated and cleared cookies after another delay (#4):")
	# for cookie4 in cooks3:
	# 	print("	", cookie4)


def test():
	print("Starting!")

	ua = dict(WebRequest.getUserAgent())
	# print(ua)

	crbin = os.path.abspath("./vendored/headless_shell")
	cr = ChromeController.ChromeRemoteDebugInterface(crbin, dbg_port=9232)

	cooks1 = cr.get_cookies()

	resp = cr.update_headers(ua)
	print("Set user agent: ", resp)
	# print("Set extra headers: ", resp)


	# print(cr)
	resp = cr.Emulation_setVisibleSize(1500, 1000)
	# print("Viewport size", resp)
	print("Doing first navigation...")

	try:
		resp = cr.blocking_navigate_and_get_source("http://www.whatarecookies.com/cookietest.asp", timeout=10)

	except Exception as e:
		have = cr.drain_transport()
		for msg in have:
			pprint.pprint(msg)
		raise e


	# resp = cr.blocking_navigate_and_get_source("http://10.1.1.8:33507/index")
	# resp = cr.blocking_navigate_and_get_source("http://10.1.1.8:33507/index")

	cr.click_link_containing_url("/test")
	# print("Page.navigate", resp['content'])
	img = cr.take_screeshot()
	with open("screenshot.png", "wb") as fp:
		fp.write(img)
	# resp = cr.synchronous_command("Page.captureScreenshot", {})
	# print("Page.captureScreenshot", resp)


	ctnt = cr.get_rendered_page_source()
	# print("Source:")
	# print(ctnt)

	cooks1 = cr.get_cookies()

	print("Doing second navigation...")
	resp = cr.blocking_navigate_and_get_source("http://goat.com", timeout=10)
	# cr.Network_clearBrowserCookies()
	print("Getting cookies!")

	cooks2 = cr.get_cookies()
	cooks3 = cr.get_cookies(all_cookies=False)

	cr.Network_clearBrowserCookies()

	cooks4 = cr.get_cookies()
	print()
	print("Pre-clearing cookies:")
	for cookie in cooks1:
		print(cookie)
		print(cookie._rest)

	print()
	print("Global Cookies:")
	for cookie in cooks2:
		print(cookie)
		print(cookie._rest)

	print()
	print("Local only cookies:")
	for cookie in cooks3:
		print(cookie)
		print(cookie._rest)

	print()
	print("Cleared cookies:")
	for cookie in cooks4:
		print(cookie)
		print(cookie._rest)

	# for cook in cooks1:
	# 	ret = cr.set_cookie(cook)
	# 	print(ret)

	# print()
	# print("Reinstated cookies:")
	# cooks3 = cr.get_cookies()
	# for cookie in cooks3:
	# 	print(cookie)
	# 	print(cookie._rest)

	wait_time = 5
	for x in range(wait_time):
		data = cr.drain_transport()
		# pprint.pprint(data)
		print("Sleeping: ", wait_time - x)

	# print("Draining!")
	# pprint.pprint(cr.drain_transport())

def test_cycle():
	for x in range(30):
		print("Starting loop %s" % x)
		with ChromeController.ChromeContext(crbin) as cr:
			print("Looping:", x)
			print(cr)
			cr.blocking_navigate('http://www.google.com')
			print("Deleted")
			print("Ending loop %s" % x)

def test_tabs():
	for x in range(30):

		with ChromeController.ChromeContext(crbin) as cr:
			print("Context manager entered")
			tabl = [cr.new_tab(), cr.new_tab(), cr]

			print("Tabs:", tabl)
			print("Transport:")
			print(tabl[0].transport)
			# cr.blocking_navigate("http://www.google.com", timeout=10)
			print("Loop")
			for idx, tab in enumerate(tabl):
				print("Fetching using tab %s -> %s" % (idx, tab))
				tab.blocking_navigate("http://www.google.com", timeout=10)
			print("Complete")

def test_tabs_conf():
	for x in range(30):

		with ChromeController.ChromeContext(crbin) as cr:
			print("Context manager entered")
			tabl = [
				cr.new_tab(visible_size=(500,800), disable_page=True,  disable_dom=True,  disable_network=True ),
				cr.new_tab(visible_size=(501,801), disable_page=True,  disable_dom=True,  disable_network=False),
				cr.new_tab(visible_size=(502,802), disable_page=True,  disable_dom=False, disable_network=True ),
				cr.new_tab(visible_size=(503,803), disable_page=True,  disable_dom=False, disable_network=False),
				cr.new_tab(visible_size=(504,804), disable_page=False, disable_dom=True,  disable_network=True ),
				cr.new_tab(visible_size=(505,805), disable_page=False, disable_dom=True,  disable_network=False),
				cr.new_tab(visible_size=(506,806), disable_page=False, disable_dom=False, disable_network=True ),
				cr.new_tab(visible_size=(507,807), disable_page=False, disable_dom=False, disable_network=False),

				]

			print("Tabs:", tabl)
			print("Transport:")
			print(tabl[0].transport)
			# cr.blocking_navigate("http://www.google.com", timeout=10)
			print("Loop")
			for idx, tab in enumerate(tabl):
				print("Fetching using tab %s -> %s" % (idx, tab))
				ret = tab.Page_navigate(url = "http://www.google.com")
			print("Complete")

def test_url():

	with ChromeController.ChromeContext(crbin) as cr:
		cr.blocking_navigate("http://www.google.com", timeout=10)
		print("Current URL:", cr.get_current_url())
		# cr.close()

def test_title():

	with ChromeController.ChromeContext(crbin) as cr:
		cr.blocking_navigate("http://www.google.com", timeout=10)
		print("Current URL:", cr.get_current_url())
		print("Response: ", cr.get_page_url_title())
		# cr.close()

def test_rendered_fetch():

	cr = ChromeController.ChromeRemoteDebugInterface(crbin)

	resp = cr.blocking_navigate("https://www.catatopatch.com/appraise-chapter-15", timeout=10)
	print("Current URL:", cr.get_current_url())
	rcnt = cr.get_rendered_page_source()
	print("content:", type(rcnt))
	# cr.close()

def test_tab_cache():
	tp = ChromeController.TabPooledChromium(crbin)

	url = "https://www.catatopatch.com/appraise-chapter-15"

	with tp.tab(url=url) as cr:
		resp = cr.blocking_navigate("https://www.catatopatch.com/appraise-chapter-15", timeout=10)
		print("Current URL:", cr.get_current_url())
		at_url = cr.get_current_url()
		rcnt = cr.get_rendered_page_source()
		print("content:", type(rcnt))

	print("Creating tab again!")
	with tp.tab(url=url) as cr:
		assert at_url == cr.get_current_url()

	print("3rd tab context!")
	with tp.tab(url=url) as cr:
		title, cur_url = cr.get_page_url_title()
		print("title, cur_url", title, cur_url)
		assert at_url == cur_url

	# cr.close()

def test_redirect():
	tp = ChromeController.TabPooledChromium(crbin)

	url = "http://127.0.0.1:8000/redir_from.html"
	# url = "https://yurikatrans.wordpress.com/feed/"

	print("3rd tab context!")
	with tp.tab(url=url) as cr:
		resp = cr.blocking_navigate_and_get_source(url, timeout=10)
		# print(resp)
		# title, cur_url = cr.get_page_url_title()
		# print("title, cur_url", title, cur_url)


if __name__ == '__main__':
	import logSetup
	logSetup.initLogging(1)
	# test_creation()
	# test()
	# test_delete_cookies()
	test_title()
	# test_tabs_conf()
	# test_redirect()
	# test_cycle()
	# test_rendered_fetch()

	# test_url()
	# docstring_dbg()
