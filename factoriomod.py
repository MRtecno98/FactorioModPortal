import requests, json, os, sys, shutil, traceback

MAX_RELEASES_DISPLAYED = 3
MAX_WORDS_PER_LINE = 6

title = """
  _____          _             _         __  __           _   ____            _        _ 
 |  ___|_ _  ___| |_ ___  _ __(_) ___   |  \/  | ___   __| | |  _ \ ___  _ __| |_ __ _| |
 | |_ / _` |/ __| __/ _ \| '__| |/ _ \  | |\/| |/ _ \ / _` | | |_) / _ \| '__| __/ _` | |
 |  _| (_| | (__| || (_) | |  | | (_) | | |  | | (_) | (_| | |  __/ (_) | |  | || (_| | |
 |_|  \__,_|\___|\__\___/|_|  |_|\___/  |_|  |_|\___/ \__,_| |_|   \___/|_|   \__\__,_|_|
"""

username = ""
token = ""

factorio_path = ""

def getModInfo(name) :
	request = requests.get("https://mods.factorio.com/api/mods/" + name.replace(" ", "%20"))
	result = json.loads(request.text)
	return result

def isErrorPacket(modpacket) :
	return "message" in modpacket.keys()

def login() :
	global username, token
	
	print("Insert below your Factorio account data (NOT NECESSARALY PREMIUM)")
	usr = input("Insert username: ")
	print("\nYou can get the token by going to https://www.factorio.com/profile")
	tk = input("Insert token: ").strip()

	username = usr
	token = tk

	saveUserdata()
	
	print("\nCredentials Saved!")

def setFactorioPath() :
	global factorio_path
	
	path = ""
	while True :
		path = input("Insert Factorio path: ").strip()
		if not os.path.isdir(path) :
			continue

		if not ("mods" and "bin" and "player-data.json" in os.listdir(path)) :
			print("Invalid Factorio path")
			continue
		break

	factorio_path = path
	saveUserdata()
	print("Path changed!")

def saveUserdata() :
	global username, token, factorio_path
	
	data = {}
	data["username"] = username
	data["token"] = token
	data["path"] = factorio_path
	
	with open("userdata.json", "w") as file :
		file.write(json.dumps(data))

def loadUserdata() :
	global username, token, factorio_path

	data = {}
	if os.path.isfile("userdata.json") :
		with open("userdata.json") as file :
			data = json.loads(file.read())
		username = data.get("username", "")
		token = data.get("token", "")
		factorio_path = data.get("path", "")

def checkCredentialsSet() :
	global username, token
	return username != "" and token != ""

def checkFactorioPathSet() :
	global factorio_path
	return factorio_path != ""
	
def splitWordLines(text, words_per_line=MAX_WORDS_PER_LINE) :
	words = text.split(" ")
	splitted = list()
	
	c = 0
	temp = list()
	for word in words :
		if c == words_per_line :
			splitted.append(" ".join(temp))
			temp = list()
			c = 0
		temp.append(word)
		c+=1
		
	splitted.append(" ".join(temp))
		
	return splitted

def displayModInfo(packet, max_releases=MAX_RELEASES_DISPLAYED) :
	print("Name: " + packet["title"])
	print("Owner: " + packet["owner"])
	print("Downloads: " + str(packet["downloads_count"]))
	print("ID: " + packet["name"])
	print("\nDescription: ")
	print("\n".join(splitWordLines(packet["summary"])))
	
	print("\nReleases:")

	releases = packet["releases"]
	releases.reverse()
	if max_releases == -1 :
		max_releases = len(releases)
	
	tab = " "*4
	i = 0
	for x in releases :
		if i == max_releases :
			print(tab + "[" + str(len(releases) - i) + " more...]")
			break
		
		print(tab + "Version: " + x["version"])
		print(tab + "Game Version: " + x["info_json"]["factorio_version"])
		print(tab + "File name: " + x["file_name"])
		print()
		i+=1

def checkDirs() :
	os.makedirs("mod_cache", exist_ok=True)
	
def clearCache() :
	if os.path.isdir("mod_cache") :
		shutil.rmtree("mod_cache")
		checkDirs()

def downloadMod(packet) :
	global username, token
	
	displayModInfo(packet)
	vers = ""
	while True :
		check = False
		vers = input("\nSelect release to download: ").strip()
		for rl in packet["releases"] :
			if rl["version"] == vers :
				check = True
		if check :
			break
		print("Version not released")
		
	release = None
	for rl in  packet["releases"] :
		if rl["version"] == vers :
				release = dict(rl)
		
	url = "http://mods.factorio.com" + release["download_url"] + "?username=" + username + "&token=" + token
	
	request = requests.get(url)
	request.raise_for_status()
	with open("mod_cache" + os.sep + release["file_name"], "wb") as file:
		for chunk in request.iter_content(4096) :
			file.write(chunk)

	print("Mod downloaded successfully")
	return release["file_name"]

def installMod(filename) :
	global factorio_path
	
	print("Installing mod...")
	shutil.copy("mod_cache" + os.sep + filename, factorio_path + os.sep + "mods")
	print("Mod installed")
	
def askModName(message="Insert mod name: ", error_message="Not found, try again") :
	packet = {}
	while True :
		name = input(message)
		packet = getModInfo(name)
		if isErrorPacket(packet) :
			print(error_message)
			continue
		break
	return packet
		

def start() :
	global username, token, factorio_path

	print("\n")
	print("1) Install mod from mod portal")
	print("2) Download mod from mod portal")
	print("3) View mod info")
	print("4) Select Factorio installation")
	print("5) Set user data")
	print("6) Clear cache")
	print("0) Exit")

	opt = 0
	while True :
		try :
			opt = int(input("-> "))
			break
		except KeyboardInterrupt :
			sys.exit(0)
		except :
			continue

	if opt == 0 :
		sys.exit(0)

	elif opt == 1 :
		if (not checkCredentialsSet()) or (not checkFactorioPathSet()) :
			print("You need to set the credentials and the factorio path in order to install a mod!")
			return
		
		try :
			packet = askModName()
			print()
		except KeyboardInterrupt :
			return
		
		installMod(downloadMod(packet))
		
	elif opt == 2:
		if not checkCredentialsSet() :
			print("You need to set the credentials in order to download a mod!")
			return
		
		try :
			packet = askModName()
			print()
		except KeyboardInterrupt :
			return

		downloadMod(packet)
	
	elif opt == 3:
		try :
			packet = askModName()
			
			while True:
				try :
					rels = input(f"Releases to print(-1 for all, default {MAX_RELEASES_DISPLAYED}): ")
					rels = -1 if rels == "" else int(rels)
					break
				except ValueError:
					continue
		
			print()
		except KeyboardInterrupt :
			return

		   
						
		displayModInfo(packet)
	
	elif opt == 4:
		if checkFactorioPathSet() :
			print("\nIMPORTANT: You'll overwrite the previous path")
			while True:
				c = input("Continue? S/n: ").lower()
				if c == "" or c == "s" :
					break
				if c == "n" :
					return
		
		print("Setting a factorio path will able you to automatic install mods after download, " + \
			  "insert here the ABSOLUTE path for the Factorio Game Folder\n")
		
		setFactorioPath()
	
	elif opt == 5:
		if checkCredentialsSet() :
			print("\nIMPORTANT: You'll overwrite the previous credentials")
			while True:
				c = input("Continue? S/n: ").lower()
				if c == "" or c == "s" :
					break
				if c == "n" :
					return

		login()
		
	elif opt == 6:
		print("Clearing mod cache...")
		clearCache()
		print("Done")

try :   
	if __name__ == "__main__" :
		print(title)
		checkDirs()
		loadUserdata()
		while True :
			start()
except KeyboardInterrupt:
	sys.exit(1)
except Exception as exc:
	print("\nAn error has occurred while executing the script")
	print("Dumping traceback below\n")
	
	traceback.print_tb(exc.__traceback__)
	
	input("\nPress enter to terminate\n")
	sys.exit(1)
