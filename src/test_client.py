from io import SEEK_END
from pydoc import cli
import socketserver
import threading
from server import MyTCPHandler as HTTPHandler
from http import HTTPStatus
from http.client import HTTPConnection, BadStatusLine
import os
from random import shuffle

"""
Written by: Raymon Skjørten Hansen
Email: raymon.s.hansen@uit.no
Course: INF-2300 - Networking
UiT - The Arctic University of Norway
May 9th, 2019
"""


RANDOM_TESTING_ORDER = True

HOST = "localhost"
PORT = 8080

with open("src/index.html", "rb") as infile:
    EXPECTED_BODY = infile.read()

with open("src/server.py", "rb") as infile:
    FORBIDDEN_BODY = infile.read()


class MockServer(socketserver.TCPServer):
    allow_reuse_address = True


server = MockServer((HOST, PORT), HTTPHandler)
server_thread = threading.Thread(target=server.serve_forever)
server_thread.start()
client = HTTPConnection(HOST, PORT)


def server_returns_valid_response_code():
    """Server returns a valid http-response code."""
    client.request("GET", "/")
    try:
        response = client.getresponse()
        client.close()
        return response.status in [status.value for status in HTTPStatus]
    except BadStatusLine:
        client.close()
        return False


def test_index():
    """GET-request to root returns 'index.html'."""
    client.request("GET", "/")
    body = client.getresponse().read()
    client.close()
    return EXPECTED_BODY == body


def test_content_length():
    """Content-Length header is present."""
    client.request("GET", "/")
    headers = [k.lower() for k in client.getresponse().headers.keys()]
    client.close()
    return "content-length" in headers


def test_valid_content_length():
    """Content-Length is correct."""
    client.request("GET", "/")
    headers = {k.lower(): v for k, v in client.getresponse().headers.items()}
    expected_length = len(EXPECTED_BODY)
    try:
        length = int(headers.get("content-length"))
        return expected_length == length
    except (KeyError, TypeError):
        return False
    finally:
        client.close()


def test_content_type():
    """Content-Type is present."""
    client.request("GET", "/")
    headers = [k.lower() for k in client.getresponse().headers.keys()]
    client.close()
    return "content-type" in headers


def test_valid_content_type():
    """Content type is correct."""
    client.request("GET", "/")
    headers = {k.lower(): v for k, v in client.getresponse().headers.items()}
    expected_type = "text/html"
    try:
        actual_type = headers.get("content-type")
        # Type-field could contain character encoding too.
        # So we just check that the basic type is correct.
        return actual_type.startswith(expected_type)
    except (KeyError, TypeError):
        return False
    finally:
        client.close()


def test_nonexistent_resource_status_code():
    """Server returns 404 on non-existing resource."""
    client.request("GET", "did_not_find_this_file.not")
    response = client.getresponse()
    client.close()
    return response.status == HTTPStatus.NOT_FOUND


def test_forbidden_resource_status_code():
    """Server returns 403 on forbidden resource."""
    client.request("GET", "server.py")
    response = client.getresponse()
    client.close()
    return response.status == HTTPStatus.FORBIDDEN


def test_directory_traversal_exploit():
    """Directory traversal attack returns 403 status code."""
    client.request("GET", "../README.md")
    response = client.getresponse()
    client.close()
    return response.status == HTTPStatus.FORBIDDEN


def test_post_to_non_existing_file_should_create_file():
    """POST-request to non-existing file, should create that file."""
    testfile = "test.txt"
    msg = b'Simple test'
    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg),
    }
    if(os.path.exists(testfile)):
        os.remove(testfile)
    client.request("POST", testfile, body=msg, headers=headers)
    client.getresponse()
    client.close()
    return os.path.exists(testfile)


def test_post_to_test_file_should_return_file_content():
    """POST to test-file should append to file and return the file-content."""
    testfile = "test.txt"
    msg = b'text=Simple test'
    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg),
    }
    if(os.path.exists(testfile)):
        os.remove(testfile)
    client.request("POST", testfile, body=msg, headers=headers)
    response_body = client.getresponse().read()
    with open(testfile, "rb") as infile:
        filecontent = infile.read()
    client.close()
    return response_body == filecontent


def test_post_to_test_file_should_return_correct_content_length():
    """POST to test-file should respond with correct content_length."""
    testfile = "test.txt"
    msg = b'text=Simple test'
    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg),
    }
    if(os.path.exists(testfile)):
        os.remove(testfile)
    client.request("POST", testfile, body=msg, headers=headers)
    expected_content_length = len(client.getresponse().read())
    with open(testfile, "rb") as infile:
        actual_length = len(infile.read())
    client.close()
    return expected_content_length == actual_length


def RESTful_post_test():
    """POST to messages should create messages file and add msg content to it."""

    testfile = "messages.txt"
    msg = b'{"text": "Example text1"}'
    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg),
    }
    if(os.path.exists(testfile)):
        os.remove(testfile)
    client.request("POST", "messages", body=msg, headers=headers)
    response_body = client.getresponse().read()
    try:
        with open(testfile, "rb") as infile:
            filecontent = infile.read()

    except:
        filecontent = b''

    client.close()
    return response_body == filecontent

def RESTful_post_and_get_test():
    """POST and GET to messages should add the message and return all previous messages."""



    uri = "messages"
    testfile = "messages.txt"

    if(os.path.exists(testfile)):
        os.remove(testfile)

    msg1 = b'{"text": "Example text1"}'
    headers1 = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg1),
    }
    client.request("POST", url=uri, body=msg1, headers=headers1)
    client.close()

    msg2 = b'{"text": "Example text2"}'
    headers2 = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg2),
    }
    client.request("POST", url=uri, body=msg2, headers=headers2)
    client.close()

    client.request("GET", url=uri)
    response_body = client.getresponse().read()

    client.close()
    return response_body == b'[{"id": 0,"text": "Example text1"},{"id": 1,"text": "Example text2"}]'

def RESTful_post_and_put_id_test():
    """POST and PUT with ID in the body and ID in uri should replace the message."""

    uri = "messages"
    testfile = "messages.txt"
    msg1 = b'{"text": "First message"}'
    headers1 = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg1),
    }

    if(os.path.exists(testfile)):
        os.remove(testfile)

    client.request("POST", url=uri, body=msg1, headers=headers1)
    client.getresponse().read()     #wait for server
    client.close()
    msg2 = b'{"id": 0,"text": "Second message"}'

    headers2 = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg2),
    }
    client.request("PUT", url=uri, body=msg2, headers=headers2)
    client.getresponse().read()     #wait for server
    client.close()

    with open(testfile, "rb") as infile:
        filecontent2 = infile.read()
    first_test = filecontent2 == b',' + msg2

    if not first_test:
        print("failed first test:")
        print(filecontent2)

    msg3 = b'{"text": "Third message"}'
    uri3 = "messages/0"
    headers3 = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg3),
    }
    client.request("PUT", url=uri3, body=msg3, headers=headers3)
    client.getresponse().read()     #wait for server
    client.close()

    with open(testfile, "rb") as infile:
        filecontent3 = infile.read()
    second_test = filecontent3 == b',{"id": 0,"text": "Third message"}'

    if not second_test:
        print("failed second test:")
        print(filecontent3)

    return first_test & second_test

def RESTful_post_invalid_delete_test():
    """DELETE with no id should return 400 Bad Request and with wrong id should return 200 OK."""

    uri = "messages"
    testfile = "messages.txt"

    if(os.path.exists(testfile)):
        os.remove(testfile)

    client.request("DELETE", url=uri)
    response = client.getresponse()
    first_test = response.status == HTTPStatus.BAD_REQUEST
    client.close()

    msg = b'{"id": 0}'
    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg),
    }
    client.request("DELETE", url=uri, body=msg, headers=headers)
    response = client.getresponse()
    second_test = response.status == HTTPStatus.OK
    client.close()

    return first_test and second_test

def RESTful_post_delete_test():
    """DELETE with id in uri and in message body should remove the messages."""

    uri = "messages"
    testfile = "messages.txt"

    if(os.path.exists(testfile)):
        os.remove(testfile)

    msg1 = b'{"text": "Example text1"}'
    headers1 = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg1),
    }
    client.request("POST", url=uri, body=msg1, headers=headers1)
    client.getresponse()
    client.close()

    msg2 = b'{"text": "Example text2"}'
    headers2 = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg2),
    }
    client.request("POST", url=uri, body=msg2, headers=headers2)
    client.getresponse()
    client.close()

    msg3 = b'{"id": 0}'
    headers3 = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg3),
    }
    client.request("DELETE", url=uri, body=msg3, headers=headers3)
    client.getresponse()
    client.close()

    uri3 = "messages/1"

    headers4 = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": 0,
    }

    client.request("DELETE", url=uri3, headers=headers4)
    client.getresponse()
    client.close()

    client.request("GET", url=uri)
    response = client.getresponse()
    client.close()

    with open(testfile, "rb") as infile:
        filecontent = infile.read()

    return filecontent == b''

def RESTful_get_empty_test():
    """GET to messages with no messages should return 404 not found."""

    uri = "messages"
    testfile = "messages.txt"

    if(os.path.exists(testfile)):
        os.remove(testfile)

    client.request("GET", url=uri)
    response_body = client.getresponse().read()
    client.close()


    first_test = response_body == b'[]'
    if not first_test:
        print("failed first test")


    msg1 = b'{"text": "Example text"}'
    headers1 = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg1),
    }
    client.request("POST", url=uri, body=msg1, headers=headers1)
    client.getresponse()
    client.close()

    msg2 = b'{"id": 0}'
    headers2 = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
        "Content-Length": len(msg2),
    }
    client.request("DELETE", url=uri, body=msg2, headers=headers2)
    client.getresponse()
    client.close()

    client.request("GET", url=uri)
    response_body = client.getresponse().read()
    client.close()


    second_test = response_body == b'[]'
    if not second_test:
        print("failed second test:")

    return first_test and second_test

test_functions = [
    server_returns_valid_response_code,
    test_index,
    test_content_length,
    test_valid_content_length,
    test_content_type,
    test_valid_content_type,
    test_nonexistent_resource_status_code,
    test_forbidden_resource_status_code,
    test_directory_traversal_exploit,
    test_post_to_non_existing_file_should_create_file,
    test_post_to_test_file_should_return_file_content,
    test_post_to_test_file_should_return_correct_content_length,
    RESTful_post_test,
    RESTful_post_and_get_test,
    RESTful_post_and_put_id_test,
    RESTful_post_invalid_delete_test,
    RESTful_post_delete_test,
    RESTful_get_empty_test
]


def run_tests(all_tests, random=False):
    passed = 0
    num_tests = len(all_tests)
    skip_rest = False
    for test_function in all_tests:
        if not skip_rest:
            result = test_function()
            if result:
                passed += 1
            else:
                skip_rest = True
            print(("FAIL", "PASS")[result] + "\t" + test_function.__doc__)
        else:
            print("SKIP\t" + test_function.__doc__)
    percent = round((passed / num_tests) * 100, 2)
    print(f"\n{passed} of {num_tests}({percent}%) tests PASSED.\n")
    if passed == num_tests:
        return True
    else:
        return False




def run():
    print("Running tests in sequential order...\n")
    sequential_passed = run_tests(test_functions)
    # We only allow random if all tests pass sequentially
    if RANDOM_TESTING_ORDER and sequential_passed:
        print("Running tests in random order...\n")
        shuffle(test_functions)
        run_tests(test_functions, True)
    elif RANDOM_TESTING_ORDER and not sequential_passed:
        print("Tests should run in sequential order first.\n")


run()
server.shutdown()
