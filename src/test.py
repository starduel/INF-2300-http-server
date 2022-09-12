
uri = b'/text.txt/'

list = uri.split(b'/')
path = list[0] if list[0] != b'' else list[1]

print(path)