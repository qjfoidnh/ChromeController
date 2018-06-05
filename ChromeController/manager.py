
import distutils.spawn
import os.path
import sys
import subprocess
import pprint
import json
import base64
import signal
import pprint
import time
import http.cookiejar
import urllib.parse
import ChromeController.filter_funcs as filter_funcs

from ChromeController.cr_exceptions import ChromeNavigateTimedOut
from ChromeController.cr_exceptions import ChromeError
from ChromeController.resources import js


try:
	# Try to import the aparatus for generating the wrapper class, and
	# import it, if possible.
	from .Generator import gen
	gen.update_generated_class()
	ChromeRemoteDebugInterface_base = gen.get_class_def()
except ImportError:
	# If that failed, use the pre-generated version
	try:
		from ChromeController.Generator.Generated import ChromeRemoteDebugInterface as \
			ChromeRemoteDebugInterface_base
	except ImportError:
		raise RuntimeError("Generated class wrapper doesn't exist, and couldn't be created!")




DEFAULT_TIMEOUT_SECS = 10

class ChromeRemoteDebugInterface(ChromeRemoteDebugInterface_base):
	'''
	Remote control class for Chromium.
	'''

	def __init__(self,
		binary                = None,
		dbg_port              = None,
		use_execution_manager = None,
		visible_size          = None,
		disable_page          = False,
		disable_dom           = False,
		disable_network       = False,
		*args,
		**kwargs):
		super().__init__(
			binary                = binary,
			dbg_port              = dbg_port,
			use_execution_manager = use_execution_manager,
			*args, **kwargs)

		if disable_page:
			self.log.debug("Not enabling page debug interface")
		else:
			self.Page_enable()
		if disable_dom:
			self.log.debug("Not enabling DOM debug interface")
		else:
			self.DOM_enable()
		if disable_network:
			self.log.debug("Not enabling Network debug interface")
		else:
			self.Network_enable()

		if visible_size:
			assert isinstance(visible_size, tuple), "visible_size must be a 2-tuple containing 2 integers"
			assert len(visible_size) == 2, "visible_size must be a 2-tuple containing 2 integers"
			assert all([isinstance(val, int) for val in visible_size]), "visible_size must be a 2-tuple containing 2 integers"
			self.log.debug("Visible size overridden to %sx%s" % visible_size)
			self.Emulation_setVisibleSize(*visible_size)
		else:
			self.Emulation_setVisibleSize(1024, 1366)

		# cr_ver = self.Browser_getVersion()
		# self.log.debug("Remote browser version info:")
		# self.log.debug(str(cr_ver))
		# 'protocolVersion'
		# 'product'
		# 'revision'
		# 'userAgent'
		# 'jsVersion'


	def update_headers(self, header_args):
		'''
		Given a set of headers, update both the user-agent
		and additional headers for the remote browser.

		header_args must be a dict. Keys are the names of
		the corresponding HTTP header.

		return value is a 2-tuple of the results of the user-agent
		update, as well as the extra headers update.
		If no 'User-Agent' key is present in the new headers,
		the first item in the tuple will be None

		'''
		assert isinstance(header_args, dict), "header_args must be a dict, passed type was %s" \
			% (type(header_args), )

		ua = header_args.pop('User-Agent', None)
		ret_1 = None
		if ua:
			ret_1 = self.Network_setUserAgentOverride(userAgent=ua)


		ret_2 = self.Network_setExtraHTTPHeaders(headers = header_args)

		return (ret_1, ret_2)


	def __exec_js(self, script, args=None, **extra_params):
		'''

		Execute the passed javascript statement, optionally with passed
		arguments.

		Note that if `script` is not a function, it must be a single statement.
		The presence of semicolons not enclosed in a bracket scope will produce
		an error.

		'''

		if args is None:
			args = {}

		# How chromedriver does this:

		#  std::unique_ptr<base::Value>* result) {
		#   std::string json;
		#   base::JSONWriter::Write(args, &json);
		#   // TODO(zachconrad): Second null should be array of shadow host ids.
		#   std::string expression = base::StringPrintf(
		#       "(%s).apply(null, [null, %s, %s])",
		#       kCallFunctionScript,
		#       function.c_str(),
		#       json.c_str());

		expression = "({}).apply(null, [null, {}, {}])".format(
				js.kCallFunctionScript,
				script,
				json.dumps(args)
			)

		resp3 = self.Runtime_evaluate(expression=expression, **extra_params)

		return resp3




	# Interact with http.cookiejar.Cookie() instances
	def get_cookies(self):
		'''
		Retreive the cookies from the remote browser.

		Return value is a list of http.cookiejar.Cookie() instances.
		These can be directly used with the various http.cookiejar.XXXCookieJar
		cookie management classes.
		'''
		ret = self.Network_getAllCookies()

		assert 'result' in ret, "No return value in function response!"
		assert 'cookies' in ret['result'], "No 'cookies' key in function response"

		cookies = []
		for raw_cookie in ret['result']['cookies']:

			# Chromium seems to support the following key values for the cookie dict:
			# 	"name"
			# 	"value"
			# 	"domain"
			# 	"path"
			# 	"expires"
			# 	"httpOnly"
			# 	"session"
			# 	"secure"
			#
			#  This seems supported by the fact that the underlying chromium cookie implementation has
			#  the following members:
			#        std::string name_;
			#        std::string value_;
			#        std::string domain_;
			#        std::string path_;
			#        base::Time creation_date_;
			#        base::Time expiry_date_;
			#        base::Time last_access_date_;
			#        bool secure_;
			#        bool httponly_;
			#        CookieSameSite same_site_;
			#        CookiePriority priority_;
			#
			# See chromium/net/cookies/canonical_cookie.h for more.
			#
			# I suspect the python cookie implementation is derived exactly from the standard, while the
			# chromium implementation is more of a practically derived structure.

			# Network.setCookie

			baked_cookie = http.cookiejar.Cookie(
					# We assume V0 cookies, principally because I don't think I've /ever/ actually encountered a V1 cookie.
					# Chromium doesn't seem to specify it.
					version            = 0,

					name               = raw_cookie['name'],
					value              = raw_cookie['value'],
					port               = None,
					port_specified     = False,
					domain             = raw_cookie['domain'],
					domain_specified   = True,
					domain_initial_dot = False,
					path               = raw_cookie['path'],
					path_specified     = False,
					secure             = raw_cookie['secure'],
					expires            = raw_cookie['expires'],
					discard            = raw_cookie['session'],
					comment            = None,
					comment_url        = None,
					rest               = {"httponly":"%s" % raw_cookie['httpOnly']},
					rfc2109            = False
				)
			cookies.append(baked_cookie)

		return cookies

	def set_cookie(self, cookie):
		'''
		Add a cookie to the remote chromium instance.

		Passed value `cookie` must be an instance of `http.cookiejar.Cookie()`.
		'''

		# Function path: Network.setCookie
		# Domain: Network
		# Method name: setCookie
		# WARNING: This function is marked 'Experimental'!
		# Parameters:
		#         Required arguments:
		#                 'url' (type: string) -> The request-URI to associate with the setting of the cookie. This value can affect the default domain and path values of the created cookie.
		#                 'name' (type: string) -> The name of the cookie.
		#                 'value' (type: string) -> The value of the cookie.
		#         Optional arguments:
		#                 'domain' (type: string) -> If omitted, the cookie becomes a host-only cookie.
		#                 'path' (type: string) -> Defaults to the path portion of the url parameter.
		#                 'secure' (type: boolean) -> Defaults ot false.
		#                 'httpOnly' (type: boolean) -> Defaults to false.
		#                 'sameSite' (type: CookieSameSite) -> Defaults to browser default behavior.
		#                 'expirationDate' (type: Timestamp) -> If omitted, the cookie becomes a session cookie.
		# Returns:
		#         'success' (type: boolean) -> True if successfully set cookie.

		# Description: Sets a cookie with the given cookie data; may overwrite equivalent cookies if they exist.

		assert isinstance(cookie, http.cookiejar.Cookie), 'The value passed to `set_cookie` must be an instance of http.cookiejar.Cookie().' + \
			' Passed: %s ("%s").' % (type(cookie), cookie)

		# Yeah, the cookielib stores this attribute as a string, despite it containing a
		# boolean value. No idea why.
		is_http_only = str(cookie.get_nonstandard_attr('httponly', 'False')).lower() == "true"


		# I'm unclear what the "url" field is actually for. A cookie only needs the domain and
		# path component to be fully defined. Considering the API apparently allows the domain and
		# path parameters to be unset, I think it forms a partially redundant, with some
		# strange interactions with mode-changing between host-only and more general
		# cookies depending on what's set where.
		# Anyways, given we need a URL for the API to work properly, we produce a fake
		# host url by building it out of the relevant cookie properties.
		fake_url = urllib.parse.urlunsplit((
				"http" if is_http_only else "https",  # Scheme
				cookie.domain,                        # netloc
				cookie.path,                          # path
				'',                                   # query
				'',                                   # fragment
			))

		params = {
				'url'      : fake_url,

				'name'     : cookie.name,
				'value'    : cookie.value if cookie.value else "",
				'domain'   : cookie.domain,
				'path'     : cookie.path,
				'secure'   : cookie.secure,
				'expires'  : float(cookie.expires) if cookie.expires else float(2**32),

				'httpOnly' : is_http_only,

				# The "sameSite" flag appears to be a chromium-only extension for controlling
				# cookie sending in non-first-party contexts. See:
				# https://bugs.chromium.org/p/chromium/issues/detail?id=459154
				# Anyways, we just use the default here, whatever that is.
				# sameSite       = cookie.xxx
			}

		ret = self.Network_setCookie(**params)

		return ret

	def clear_cookies(self):
		'''
		At this point, this is just a thin shim around the Network_clearBrowserCookies() operation.

		That function postdates the clear_cookies() call here.
		'''
		self.Network_clearBrowserCookies()



	def navigate_to(self, url):
		'''
		Trigger a page navigation to url `url`.

		Note that this is done via javascript injection, and as such results in
		the `referer` header being sent with the url of the network location.

		This is useful when a page's navigation is stateful, or for simple
		cases of referrer spoofing.

		'''

		assert "'" not in url
		return self.__exec_js("window.location.href = '{}'".format(url))

	def get_current_url(self):
		'''
		Probe the remote session for the current window URL.

		This is primarily used to do things like unwrap redirects,
		or circumvent outbound url wrappers.

		'''
		res = self.Page_getNavigationHistory()
		assert 'result' in res
		assert 'currentIndex' in res['result']
		assert 'entries' in res['result']

		return res['result']['entries'][res['result']['currentIndex']]['url']

	def get_page_url_title(self):
		'''
		Get the title and current url from the remote session.

		Return is a 2-tuple: (page_title, page_url).

		'''

		cr_tab_id = self.transport._get_cr_tab_meta_for_key(self.tab_id)['id']
		targets = self.Target_getTargets()

		assert 'result' in targets
		assert 'targetInfos' in targets['result']

		for tgt in targets['result']['targetInfos']:
			if tgt['targetId'] == cr_tab_id:
				# {
				# 	'title': 'Page Title 1',
				# 	'targetId': '9d2c503c-e39e-42cc-b950-96db073918ee',
				# 	'attached': True,
				# 	'url': 'http://localhost:47181/with_title_1',
				# 	'type': 'page'
				# }

				title   = tgt['title']
				cur_url = tgt['url']
				return title, cur_url




	def click_link_containing_url(self, url):
		'''
		TODO

		'''

		# exec_func =

		self.__exec_js("window.location.href = '/test'")

		# js.kCallFunctionScript

		# "window.history.back();"

		# elem = self.find_element("//a".format(url))
		# print(elem)

	def execute_javascript(self, *args, **kwargs):
		'''
		Execute a javascript string in the context of the browser tab.
		'''

		ret = self.__exec_js(*args, **kwargs)
		return ret

	def find_element(self, search):

		'''
		DOM_performSearch(self, query, includeUserAgentShadowDOM)
		Python Function: DOM_performSearch
		        Domain: DOM
		        Method name: performSearch

		        WARNING: This function is marked 'Experimental'!

		        Parameters:
		                'query' (type: string) -> Plain text or query selector or XPath search query.
		                'includeUserAgentShadowDOM' (type: boolean) -> True to search in user agent shadow DOM.
		        Returns:
		                'searchId' (type: string) -> Unique search session identifier.
		                'resultCount' (type: integer) -> Number of search results.
		        Description: Searches for a given string in the DOM tree. Use <code>getSearchResults</code> to access search results or <code>cancelSearch</code> to end this search session.

		Python Function: DOM_getSearchResults
		        Domain: DOM
		        Method name: getSearchResults

		        WARNING: This function is marked 'Experimental'!

		        Parameters:
		                'searchId' (type: string) -> Unique search session identifier.
		                'fromIndex' (type: integer) -> Start index of the search result to be returned.
		                'toIndex' (type: integer) -> End index of the search result to be returned.
		        Returns:
		                'nodeIds' (type: array) -> Ids of the search result nodes.
		        Description: Returns search results from given <code>fromIndex</code> to given <code>toIndex</code> from the sarch with the given identifier.

		DOM_discardSearchResults(self, searchId)
		Python Function: DOM_discardSearchResults
		        Domain: DOM
		        Method name: discardSearchResults

		        WARNING: This function is marked 'Experimental'!

		        Parameters:
		                'searchId' (type: string) -> Unique search session identifier.
		        No return value.
		        Description: Discards search results from the session with the given id. <code>getSearchResults</code> should no longer be called for that search.
		'''

		res = self.DOM_performSearch(search, includeUserAgentShadowDOM=False)
		assert 'result' in res
		assert 'searchId' in res['result']
		searchid = res['result']['searchId']
		res_cnt  = res['result']['resultCount']
		self.log.debug("%s", res)
		self.log.debug("%s", searchid)

		if res_cnt == 0:
			return None

		items = self.DOM_getSearchResults(searchId=searchid, fromIndex=0, toIndex=res_cnt)

		self.log.debug("Results:")
		self.log.debug("%s", items)

		# DOM_getSearchResults


	def click_element(self, contains_url):
		'''

		TODO


		ChromeDriver source for how to click an element:

		Status ExecuteClickElement(Session* session,
		                           WebView* web_view,
		                           const std::string& element_id,
		                           const base::DictionaryValue& params,
		                           std::unique_ptr<base::Value>* value) {
		  std::string tag_name;
		  Status status = GetElementTagName(session, web_view, element_id, &tag_name);
		  if (status.IsError())
		    return status;
		  if (tag_name == "option") {
		    bool is_toggleable;
		    status = IsOptionElementTogglable(
		        session, web_view, element_id, &is_toggleable);
		    if (status.IsError())
		      return status;
		    if (is_toggleable)
		      return ToggleOptionElement(session, web_view, element_id);
		    else
		      return SetOptionElementSelected(session, web_view, element_id, true);
		  } else {
		    WebPoint location;
		    status = GetElementClickableLocation(
		        session, web_view, element_id, &location);
		    if (status.IsError())
		      return status;

		    std::list<MouseEvent> events;
		    events.push_back(
		        MouseEvent(kMovedMouseEventType, kNoneMouseButton,
		                   location.x, location.y, session->sticky_modifiers, 0));
		    events.push_back(
		        MouseEvent(kPressedMouseEventType, kLeftMouseButton,
		                   location.x, location.y, session->sticky_modifiers, 1));
		    events.push_back(
		        MouseEvent(kReleasedMouseEventType, kLeftMouseButton,
		                   location.x, location.y, session->sticky_modifiers, 1));
		    status =
		        web_view->DispatchMouseEvents(events, session->GetCurrentFrameId());
		    if (status.IsOk())
		      session->mouse_position = location;
		    return status;
		  }
		}
		'''

		pass



	def __try_handle_redirect(self, timeout):
		self.log.debug("We may have redirected. Checking.")


		# print("Did we redirect?")
		messages = self.transport.recv_all_filtered(filter_funcs.capture_loading_events, tab_key=self.tab_id)
		# print("Filtered messages:")
		# pprint.pprint(messages)
		if not messages:
			raise ChromeError("Couldn't track redirect! No idea what to do!")

		last_message = messages[-1]
		# print("Last Message")
		# pprint.pprint(last_message)
		self.log.info("Probably a redirect! New content url: '%s'", last_message['params']['documentURL'])

		resp = self.transport.recv_filtered(filter_funcs.network_response_recieved_for_url(last_message['params']['documentURL'], last_message['params']['frameId']), tab_key=self.tab_id)
		resp = resp['params']
		# print("Resp")
		# pprint.pprint(resp)

		ctype = 'application/unknown'

		resp_response = resp['response']

		if 'mimeType' in resp_response:
			ctype = resp_response['mimeType']
		if 'headers' in resp_response and 'content-type' in resp_response['headers']:
			ctype = resp_response['headers']['content-type'].split(";")[0]

		# We assume the last document request was the redirect.
		# This is /probably/ kind of a poor practice, but what the hell.
		content = self.Network_getResponseBody(last_message['params']['requestId'])
		return ctype, content
		# return messages[-1][]

	def blocking_navigate_and_get_source(self, url, timeout=DEFAULT_TIMEOUT_SECS):
		'''
		Do a blocking navigate to url `url`, and then extract the
		response body and return that.

		This effectively returns the *unrendered* page content that's sent over the wire. As such,
		if the page does any modification of the contained markup during rendering (via javascript), this
		function will not reflect the changes made by the javascript.

		The rendered page content can be retreived by calling `get_rendered_page_source()`.

		Due to the remote api structure, accessing the raw content after the content has been loaded
		is not possible, so any task requiring the raw content must be careful to request it
		before it actually navigates to said content.

		Return value is a dictionary with two keys:
		{
			'binary' : (boolean, true if content is binary, false if not)
			'content' : (string of bytestring, depending on whether `binary` is true or not)
		}

		'''


		resp = self.blocking_navigate(url, timeout)
		assert 'requestId' in resp
		assert 'response' in resp
		# self.log.debug('blocking_navigate Response %s', pprint.pformat(resp))

		ctype = 'application/unknown'

		resp_response = resp['response']

		if 'mimeType' in resp_response:
			ctype = resp_response['mimeType']
		if 'headers' in resp_response and 'content-type' in resp_response['headers']:
			ctype = resp_response['headers']['content-type'].split(";")[0]

		try:
			content = self.Network_getResponseBody(resp['requestId'])
		except ChromeError:
			ctype, content = self.__try_handle_redirect(timeout)

		assert 'result' in content
		result = content['result']

		assert 'base64Encoded' in result
		assert 'body' in result

		if result['base64Encoded']:
			content = base64.b64decode(result['body'])
		else:
			content = result['body']

		self.log.info("Navigate complete. Received %s byte response with type %s.", len(content), ctype)

		return {'binary' : result['base64Encoded'],  'mimetype' : ctype, 'content' : content}


	def get_rendered_page_source(self):
		'''
		Get the HTML markup for the current page.

		This is done by looking up the root DOM node, and then requesting the outer HTML
		for that node ID.

		This calls return will reflect any modifications made by javascript to the
		page. For unmodified content, use `blocking_navigate_and_get_source()`
		'''

		# We have to find the DOM root node ID
		dom_attr = self.DOM_getDocument(depth=-1, pierce=False)
		assert 'result' in dom_attr
		assert 'root' in dom_attr['result']
		assert 'nodeId' in dom_attr['result']['root']

		# Now, we have the root node ID.
		root_node_id = dom_attr['result']['root']['nodeId']

		# Use that to get the HTML for the specified node
		response = self.DOM_getOuterHTML(nodeId=root_node_id)

		assert 'result' in response
		assert 'outerHTML' in response['result']
		return response['result']['outerHTML']


	def take_screeshot(self):
		'''
		Take a screenshot of the virtual viewport content.

		Return value is a png image as a bytestring.
		'''
		resp = self.Page_captureScreenshot()
		assert 'result' in resp
		assert 'data' in resp['result']
		imgdat = base64.b64decode(resp['result']['data'])
		return imgdat


	def blocking_navigate(self, url, timeout=DEFAULT_TIMEOUT_SECS):
		'''
		Do a blocking navigate to url `url`.

		This function triggers a navigation, and then waits for the browser
		to claim the page has finished loading.

		Roughly, this corresponds to the javascript `DOMContentLoaded` event,
		meaning the dom for the page is ready.


		Internals:

		A navigation command results in a sequence of events:

		 - Page.frameStartedLoading" (with frameid)
		 - Page.frameStoppedLoading" (with frameid)
		 - Page.loadEventFired" (not attached to an ID)

		Therefore, this call triggers a navigation option,
		and then waits for the expected set of response event messages.

		'''

		self.transport.flush(tab_key=self.tab_id)

		ret = self.Page_navigate(url = url)

		assert("result" in ret), "Missing return content"
		assert("frameId" in ret['result']), "Missing 'frameId' in return content"

		expected_id = ret['result']['frameId']

		self.transport.recv_filtered(filter_funcs.check_frame_navigated_command(expected_id), tab_key=self.tab_id)

		self.transport.recv_filtered(filter_funcs.check_frame_load_command("Page.frameStartedLoading"), tab_key=self.tab_id)
		self.transport.recv_filtered(filter_funcs.check_frame_load_command("Page.frameStoppedLoading"), tab_key=self.tab_id)
		# self.transport.recv_filtered(check_load_event_fired, tab_key=self.tab_id)

		resp = self.transport.recv_filtered(filter_funcs.network_response_recieved_for_url(url=None, expected_id=expected_id), tab_key=self.tab_id)

		if resp is None:
			raise ChromeNavigateTimedOut("Blocking navigate timed out!")

		return resp['params']

