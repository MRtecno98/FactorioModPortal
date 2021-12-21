import requests, json, os, sys, shutil, traceback, hashlib, platform
from pathlib import Path
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

def getModInfo(name,detailed=False) :
	query = "https://mods.factorio.com/api/mods/" + name.replace(" ", "%20")
	if detailed: query+='/full'
	request = requests.get(query)
	
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
def checkFactorioPath(path):
	return os.path.isdir(path) and  ("mods" and "player-data.json" in os.listdir(path))
			
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
	if not checkFactorioPathSet():
		auto_path = "."
		if platform.system() == 'Darwin':
			auto_path = os.path.join(Path.home(),"Library/Application Support/factorio")
		elif platform.system() == "Linux":
			auto_path = os.path.join(Path.home(),"factorio")
		elif platform.system() == 'Windows':
			auto_path = os.path.join(Path.home(),"AppData/Roaming/Factorio")
		if checkFactorioPath(auto_path):
			factorio_path = auto_path
			
		


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
def hash_file(filename):
   """"This function returns the SHA-1 hash
   of the file passed into it"""

   # make a hash object
   h = hashlib.sha1()

   # open file for reading in binary mode
   with open(filename,'rb') as file:

       # loop till the end of the file
       chunk = 0
       while chunk != b'':
           # read only 1024 bytes at a time
           chunk = file.read(1024)
           h.update(chunk)

   # return the hex representation of digest
   return h.hexdigest()

def downloadMod(packet,latest=False) :
	global username, token

	vers = ""
	if not latest:
		while True :
			check = False
			vers = input("\nSelect release to download: ").strip()
			for rl in packet["releases"] :
				if rl["version"] == vers :
					check = True
			if check :
				break
			print("Version not released")
	else:
		versions = [rl["version"] for rl in packet["releases"]]
		versions.sort()
		vers = versions[-1]

	release = None
	for rl in  packet["releases"] :
		if rl["version"] == vers :
				release = dict(rl)
		
	url = "http://mods.factorio.com" + release["download_url"] + "?username=" + username + "&token=" + token
	output_path = "mod_cache" + os.sep + release["file_name"]
	if os.path.isfile(output_path):
		sha1 = release['sha1']
		if sha1==hash_file(output_path):
			print('Using cached version')
			return release["file_name"]
		
	request = requests.get(url)
	request.raise_for_status()
	with open(output_path, "wb") as file:
		
		for chunk in request.iter_content(4096) :
			file.write(chunk)


	print("Mod downloaded successfully")
	return release["file_name"]
def download_recursive_mod(mod_name,install_mod=False,visited_set=None):
    if visited_set is None:
        visited_set = set()
    if mod_name in visited_set:
        return
    visited_set.add(mod_name)
    
    mod_info = getModInfo(mod_name,detailed=True)
    print(f"Downloading {mod_name}...")
    try:
        file_name = downloadMod(mod_info,latest=True)
        if install_mod:
            installMod(file_name)
    except Exception as e:
        print("#"*33)
        print(f"Error in downloading {mod_name}")
        print(e)
        print("#"*33)
        return

    versions_idx = list(range(len(mod_info["releases"])))
    versions_idx.sort(key=lambda x: mod_info["releases"][x]["version"],reverse=True)
    rel = mod_info["releases"][versions_idx[0]]
    mod_rel_info = rel['info_json']
    if 'dependencies' in mod_rel_info:
        for dep_code in mod_rel_info['dependencies']:

            for dep in dep_code.split(" "):

                if dep.isalnum() and dep!='base':
                    download_recursive_mod(dep,visited_set=visited_set,install_mod=install_mod)
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

	if opt == 1 or opt ==2:
		if not checkCredentialsSet() :
			print("You need to set the credentials in order to download a mod!")
			return
		if opt == 1 :
			if not checkFactorioPathSet() :
				print("You need to set the factorio path in order to install a mod!")
				return
			install_mod = True
		elif opt == 2:
			install_mod = False
			
		try :
			packet = askModName()
			print()
		except KeyboardInterrupt :
			return

		# downloadMod(packet)		
		download_recursive_mod(packet['name'],install_mod=install_mod)
		
	
		
	
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
