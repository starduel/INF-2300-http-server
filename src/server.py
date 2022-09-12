#!/usr/bin/env python3
import socketserver
from datetime import datetime
import json
from traceback import print_tb

"""
Written by: Raymon Skjørten Hansen
Email: raymon.s.hansen@uit.no
Course: INF-2300 - Networking
UiT - The Arctic University of Norway
May 9th, 2019
"""

server_name = b"My server"
valid_req = [b"GET", b"OPTION", b"HEAD", b"POST", b"PUT", 
             b"DELETE", b"TRACE", b"CONNECT"]
max_msgs = 256


class MyTCPHandler(socketserver.StreamRequestHandler):
    """
    This class is responsible for handling a request. The whole class is
    handed over as a parameter to the server instance so that it is capable
    of processing request. The server will use the handle-method to do this.
    It is instantiated once for each request!
    Since it inherits from the StreamRequestHandler class, it has two very
    usefull attributes you can use:

    rfile - This is the whole content of the request, displayed as a python
    file-like object. This means we can do readline(), readlines() on it!

    wfile - This is a file-like object which represents the response. We can
    write to it with write(). When we do wfile.close(), the response is
    automatically sent.

    The class has three important methods:
    handle() - is called to handle each request.
    setup() - Does nothing by default, but can be used to do any initial
    tasks before handling a request. Is automatically called before handle().
    finish() - Does nothing by default, but is called after handle() to do any
    necessary clean up after a request is handled.
    """   

    def handle(self):
        """
        This method is responsible for handling an http-request. You can, and should(!),
        make additional methods to organize the flow with which a request is handled by
        this method. But it all starts here!
        """

        #get the request line
        request_line = self.rfile.readline().split(b" ")
        if len(request_line) != 3:
            self.respond(b"HTTP/1.1 400 Bad Request\r\n")
            return

        else:
            met = request_line[0]
            uri = request_line[1]
            version = request_line[2][0:-2]

        #avoid potencial errors
        if uri == b'':
            self.respond(b"HTTP/1.1 400 Bad Request\r\n")
        
        #get path from uri even if it starts with '/'
        list = uri.split(b'/', 1)
        path = list[0] if list[0] != b'' else list[1]   

        #get the request content lenght and type
        c_lenght, c_type = self.read_headers()

        #get the request body
        body = self.rfile.read(c_lenght)

        #print(request_line)

        #handle request
        if met == b"GET":
            self.handle_get(uri, path)
            
        elif met == b"POST":
            self.handle_post(uri, path, body)
    
        elif met == b"PUT":
            self.handle_put(uri, path, body)

        elif met == b"DELETE":
            self.handle_delete(uri, path, body)

        elif met in valid_req:
            self.respond(b"HTTP/1.1 501 Method not implemented\r\n")

        else:
            self.respond(b"HTTP/1.1 400 Invalid Method\r\n")

    def respond(self, status:bytes, header:bytes = b"", body:bytes = b""):
        """Combine status and optionally header and body, then respond."""

        if header == b"":
            header = self.make_head()

        self.wfile.write(status + header + b"\r\n" + body)
        self.wfile.close()

    def ret_index(self):
        """Respond with the index as the body."""

        with open("src/index.html", "rb") as file:
            body = file.read()

        header = self.make_head(b"text/html", str(len(body)))
        self.respond(b"HTTP/1.1 200 OK\r\n" , header, body)

    def read_headers(self, max_read = 30):
        """Read up to max_read headers and return the content-lenght and content-type."""
        i = 0
        lenght = b"0"
        type = b"none"

        #read the header line, then convert it to lowercase and
        #split the header name from the header value
        header = self.rfile.readline().lower().split(b":")
        while header[0] != b"\r\n" and i < max_read:
            if header[0] == b"content-length":
                lenght = header[1]
            
            elif header[0] == b"content-type":
                type = header[1]

            header = self.rfile.readline().lower().split(b":")
            i+=1

        try:
            lenght = int(lenght.decode())

        except:
            lenght = 0

        return lenght, type

    def make_head(self, type:bytes = b'None', lenght:str ="0"):
        """"Makes a header with the date, server name, content lenght and content type."""

        #Takes the currect UTC time and convertes it into 
        # string and a compliant format, then convertes that into bytes
        binary_time = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT").encode()
        
        return (b"Date:" + binary_time + b" \r\n" 
              + b"Server:" + server_name + b" \r\n" 
              + b"Content-Type:" + type + b"\r\n"
              + b"Content-Length:" + lenght.encode() + b"\r\n")

    def handle_get(self, uri:bytes, path:bytes):
        """Handles GET request based on the URI."""

        if uri == b"/" or path == b"index" or path == b"index.html":
            self.ret_index()

        elif path == b"messages":
            self.get_all()

        elif uri == b"server.py" or b"../" in uri:
            self.respond(b"HTTP/1.1 403 Forbidden\r\n")

        else:
            self.respond(b"HTTP/1.1 404 Not Found\r\n")

    def handle_post(self, uri:bytes, path:bytes, body:bytes):
        """Handles POST request based on the URI."""

        if path == b"test.txt":
            self.post_test(body)

        elif path == b'messages':
            self.add_msg(body)

        else:
            self.respond(b"HTTP/1.1 403 Forbidden\r\n")

    def handle_put(self, uri:bytes, path:bytes, body:bytes):
        """Handles PUT request based on the URI."""

        if path == b"messages":
            self.replace_msg(uri, body)

        else:
            self.respond(b"HTTP/1.1 403 Forbidden\r\n")

    def handle_delete(self, uri:bytes, path:bytes, body:bytes):
        """Handles DELETE request based on the URI."""

        if path == b"messages":
            self.delete(uri, body)

        else:
            self.respond(b"HTTP/1.1 403 Forbidden\r\n")

    def add_msg(self, body:bytes):
        """Assigns an id to the message in the input body and saves it in messages.txt"""

        #check for valid message body
        if not self.valid_body(body):
            self.respond(b"HTTP/1.1 400 - Bad Body\r\n")
            return

        #find unsused ID
        used_id = self.used_id(integer=True)
        for x in range(max_msgs):
            if x not in used_id:
                id = str(x).encode()
                break

        new_body = self.make_body(id, body)

        with open("messages.txt", "ab") as file:
            file.write(new_body)

        header = self.make_head(b"text/json", str(len(new_body)))
        self.respond(b"HTTP/1.1 201 - Created\r\n", header, new_body)

    def post_test(self, body:bytes):
        """Saves the input body in text.txt and returns the content of text.txt"""

        with open("test.txt", "ab") as file:
            file.write(body)
            
        with open("test.txt", "rb") as file:
            new_body = file.read(-1)

        header = self.make_head(b"text", str(len(new_body)))
        self.respond(b"HTTP/1.1 200 OK\r\n", header, new_body)

    def replace_msg(self, uri:bytes, body:bytes):
        """Replace the message with the given ID, with the text in body. 
        Send response with the new message."""

        #check for valid message body
        if not self.valid_body(body):
            self.respond(b"HTTP/1.1 400 - Bad Body\r\n")
            return

        #get ID and check if it is in use
        id = self.get_id(uri, body)
        if id == b'':
            self.respond(b"HTTP/1.1 400 - Bad Message ID\r\n")
            return

        elif id not in self.used_id():
            self.respond(b"HTTP/1.1 404 - Could Not Find Message With Given ID\r\n")
            return

        self.delete_msg(id)

        #add replacement message
        new_body = self.make_body(id, body)
        with open("messages.txt", "ab") as file:
            file.write(new_body)
        header = self.make_head(b"text/json", str(len(new_body)))
        self.respond(b"HTTP/1.1 200 - OK\r\n", header, new_body)

    def delete(self, uri:bytes, body:bytes):
        """Remove the message with the given ID."""

        id = self.get_id(uri, body)
        if id == b'':
            self.respond(b"HTTP/1.1 400 - Bad Message ID\r\n")
            return

        if id in self.used_id():
            self.delete_msg(id)

        self.respond(b"HTTP/1.1 200 - OK\r\n")

    def valid_body(self, body:bytes):
        """
        Check if the body has a valid json format. Then check for illegal
        characters ( "{" and "}" ). Lastly check if there is a text field.
        Return true if all conditions are fulfilled.
        """

        try:
            json.loads(body)

        except:
            return False

        if b'{' in body[1:] or b'}' in body[:-2]:
            return False

        elif b'"text": ' not in body:
            return False

        return True

    def used_id(self, integer=False):
        """
        Return a list of the IDs in message.txt. If Integer is True, then
        the IDs in the returned list are integers, otherwise they are bytes.
        If there are no messages or if message.txt does not exist, then the
        returned list is empty.
        """

        try:
            with open("messages.txt", "rb") as file:
                messages = file.read(-1)
        except:
            return []

        if messages:
            parts = messages.split(b'{"id": ')[1:]
            if integer:
                return [int(x.split(b',')[0]) for x in parts]
            else:
                return [x.split(b',')[0] for x in parts]
        else:
            return []

    def get_all(self):
        """
        Return a json formated list of the messages and their ids, return an
        empty list if there are no messages.
        """
        
        try:
            with open("messages.txt", "rb") as file:
                messages = file.read(-1)

            body = b"[" + messages[1:] + b"]"   #ignore first ','

        except:
            body = b"[]"

        lenght = len(body)
        if lenght <= 2:
            status = b"HTTP/1.1 200 - No Messages Found\r\n"
        
        else:
            status = b"HTTP/1.1 200 - OK\r\n"

        header = self.make_head(b"text/json", str(lenght))
        self.respond(status, header, body)

    def delete_msg(self, id:bytes):
        """DELETE the message with the given ID"""

        try:
            with open("messages.txt", "rb") as file:
                messages = file.read(-1)

        except:
            return  #no messages to delete

        index = messages.find(b',{"id": ' + id + b',')  #start deleting from
        end = messages.find(b'}',index) + 1     #end of message to be deleted

        if end == -1:   #if the message cannot be found
            return

        #overwrite message with the rest of the file
        with open("messages.txt", "wb") as file:
            file.seek(index)
            file.write(messages[end:])

    def make_body(self, id:bytes, body:bytes):
        """Return a message with the input ID and body"""

        new_body = body.split(b'"text": ',1)[-1]    #get the text
        return b',{"id": ' + id + b',"text": ' + new_body

    def get_id(self, uri:bytes, body:bytes):
        """Return ID either from the URI or from the body """

        #check for id in uri
        if b"messages/" in uri:
            id = uri.split(b"messages/")[-1]

        #get id from body
        else:
            part = body.split(b'{"id": ',1)[-1]
            part = part.split(b'}',1)[0]
            id = part.split(b',',1)[0]

        #check if id is a number
        try:
            int(id)
            return id

        except:
            return b''

if __name__ == "__main__":
    HOST, PORT = "localhost", 8080
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:
        print("Serving at: http://{}:{}".format(HOST, PORT))
        server.serve_forever()
