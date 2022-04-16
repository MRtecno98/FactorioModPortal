import requests, json, os, sys, shutil, traceback, hashlib, platform
from packaging import version
from pathlib import Path
from rich.console import Console
from rich.table import Table

MAX_RELEASES_DISPLAYED = 6
MAX_WORDS_PER_LINE = 7

cli = Console()

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
	query = "https://mods.factorio.com/api/mods/" + name.replace(" ", "%20") + ("/full" if detailed else "")
	request = requests.get(query)

	result = json.loads(request.text)
	return result

def isErrorPacket(modpacket) :
	return "message" in modpacket.keys()

def login():
	global username, token

	cli.print("Insert below your Factorio account data [bold red](NOT NECESSARALY PREMIUM)[/bold red]")

	cli.print("[bold green]Insert username: [/bold green]", end="")
	usr = input()
	cli.print("\nYou can get the token by going to [bold blue]https://www.factorio.com/profile[/bold blue]")
	cli.print("[bold green]Insert token: [/bold green]", end="")
	tk = input().strip()

	username = usr
	token = tk

	saveUserdata()

	cli.print("[bold green]\nCredentials Saved![/bold green]")

def setFactorioPath() :
	global factorio_path

	path = ""
	while True :
		cli.print("[bold green]Inser Factorio path: [/bold green]", end="")
		path = input().strip()
		if not os.path.isdir(path) :
			continue

		if not ("mods" and "bin" and "player-data.json" in os.listdir(path)) :
			cli.print("[bold red]!!! Invalid Factorio path !!![/bold red]")
			continue
		break

	factorio_path = path
	saveUserdata()
	cli.print("[bold green]Path changed![/bold green]")

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
	cli.print(f"[bold green]Name:[/bold green] [bold white]{packet['title']}[/bold white]")
	cli.print(f"[bold green]Owner:[/bold green] [bold white]{packet['owner']}[/bold white]")
	cli.print(f"[bold green]Downloads:[/bold green] [bold white]{str(packet['downloads_count'])}[/bold white]")
	cli.print(f"[bold green]ID:[/bold green] [bold white]{packet['name']}[/bold white]")
	cli.print(f"\nDescription: ")
	cli.print(f"\n".join(splitWordLines(packet['summary'])))
	print()

	releases = packet["releases"]
	releases.reverse()
	if max_releases == -1 :
		max_releases = len(releases)

	releases_table = Table(title="[bold green]Releases[/bold green]")

	releases_table.add_column("[green]File name[green]")
	releases_table.add_column("[green]Mod Version[green]")
	releases_table.add_column("[green]Game Version[green]")

	tab = " "*4
	i = 0
	for x in releases :
		if i == max_releases :
			releases_table.add_row("", "", "")
			releases_table.add_row(f"[bold red]{str(len(releases) - i)} more...[/bold red]", "", "")
			cli.print(releases_table)
			break

		releases_table.add_row(x["file_name"], x["version"], x["info_json"]["factorio_version"])
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

def downloadMod(packet, ver, filter=None) :
	global username, token

	release = [r for r in packet["releases"] if r["version"] == ver][0]

	url = "http://mods.factorio.com" + release["download_url"] + "?username=" + username + "&token=" + token
	output_path = "mod_cache" + os.sep + release["file_name"]

	if os.path.isfile(output_path):
		sha1 = release["sha1"]

		if sha1 == hash_file(output_path):
			cli.print("[bold yellow]Using cached version[/bold yellow]")
			return release

	request = requests.get(url)
	request.raise_for_status()

	with open(output_path, "wb") as file:
		for chunk in request.iter_content(4096) :
			file.write(chunk)

	cli.print("[bold green]Success[/bold green]")
	return release

def parse_dep_code(code):
	res = {"required": True, "conflict": False}

	code = code.strip()

	for i in range(len(code)):
		if code[i].isalnum():
			if i > 0 and code[i-1] != " ":
				code = code[:i] + " " + code[i:]
			break

	if not code[0].isalnum():
		code = code.split(" ", 1)
		part = code[0].strip("(").strip(")")

		res["conflict"] = part== "!"
		if part in ("?", "!"):
			res["required"] = False
		code = code[1]

	for i in range(len(code)):
		if not (code[i].isalnum() or code[i] in "-_ "):
			res["name"] = code[:i].strip()
			code = code[i:]
			break

	if "name" not in res.keys():
		res["name"] = code
		code = ""
	
	sign = str()
	for c in code:
		if c in "<>=":
			sign += c
			code = code[1:]
		else:
			break
	code = code.strip()

	if len(code) > 0:
		ver = version.parse(code)

		res["filter"] = (lambda v: v > ver) if sign == ">" \
					else (lambda v: v >= ver) if sign == ">=" \
					else (lambda v: v < ver )if sign == "<" \
					else (lambda v: v <= ver) if sign == "<=" \
					else None
	
	return res

def download_recursive_mod(mod_name, ver="latest", filter=lambda v: True, visited_set=None):
	visited_set = visited_set if visited_set else dict()

	if mod_name in visited_set.keys():
		return visited_set
	visited_set[mod_name] = None

	mod_info = getModInfo(mod_name, detailed=True)

	if "message" in mod_info.keys():
		cli.print(f"Could not download [bold red]{mod_name}[/bold red]: error: [bold red]{mod_info['message']}[/bold red]")
		return

	releases = [release for release in mod_info["releases"] if (not filter) or filter(version.parse(release["version"]))]

	if not ver:
		# Inform the user about available releases
		# when going interactive mode
		displayModInfo(mod_info)
		print()

		while True :
			check = False
			cli.print("[bold green]Select release to download: [/bold green]", end="")
			ver = input().strip()
			print()
			for rl in releases :
				if rl["version"] == ver :
					check = True
			if check :
				break
			cli.print("[bold red]!!! Version not released !!![/bold red]")
	elif ver == "latest":
		releases.sort(key=(lambda release: version.parse(release["version"])))
		ver = releases[-1]["version"]

	print(f"Downloading {mod_name}... ", end="", flush=True)
	target = downloadMod(mod_info, ver=ver)
	visited_set[mod_name] = target["file_name"]

	if "dependencies" in target["info_json"]:
		for dep_code in target["info_json"]["dependencies"]:
			dep = parse_dep_code(dep_code)

			if dep["required"] and dep["name"] != "base":
					visited_set.update(
						download_recursive_mod(dep["name"],
							filter=dep.get("filter", None),
							visited_set=visited_set))

	return visited_set

def installMod(filename):
	global factorio_path

	target = factorio_path + os.sep + "mods"
	os.makedirs(target, exist_ok=True)

	cli.print(f"[green]Installing {filename}... [/green]", end='')
	sys.stdout.flush()

	shutil.copy("mod_cache" + os.sep + filename, target)

	cli.print("[bold green]Done[/bold green]")

def install_set(visited_set):
	for path in [val for val in visited_set.values() if val is not None]:
		installMod(path)

def askModName(message="[bold green]Insert mod name: [/bold green]", error_message="[bold red]!!! Not found, try again !!! [/bold red]") :
	packet = {}
	while True :
		cli.print(message, end="")
		name = input()
		packet = getModInfo(name)
		if isErrorPacket(packet) :
			cli.print(error_message)
			continue
		break
	return packet

def help():
	print("\n")
	cli.print("[bold yellow]1)[/bold yellow] Install mod from mod portal")
	cli.print("[bold yellow]2)[/bold yellow] Download mod from mod portal")
	cli.print("[bold yellow]3)[/bold yellow] View mod info")
	cli.print("[bold yellow]4)[/bold yellow] Select Factorio installation")
	cli.print("[bold yellow]5)[/bold yellow] Set user data")
	cli.print("[bold yellow]6)[/bold yellow] Clear cache")
	cli.print("[bold yellow]0)[/bold yellow] Exit")
	cli.print("\n[bold yellow]Enter nothing to print this help again[/bold yellow]")

def start() :
	global username, token, factorio_path

	opt = 0
	while True :
		try :
			cli.print("\n[bold green]-> [/bold green]", end="")
			opt = int(input())
			break
		except KeyboardInterrupt :
			sys.exit(0)
		except :
			help()
			continue

	if opt == 0 :
		sys.exit(0)

	if opt in (1, 2):
		if not checkCredentialsSet() :
			cli.print("[bold red]!!! You need to set the credentials in order to download a mod !!![/bold red]")
			return

		if opt == 1 :
			if not checkFactorioPathSet() :
				cli.print("[bold red]!!! You need to set the factorio path in order to install a mod !!![/bold red]")
				return

		try :
			packet = askModName()
			print()
		except KeyboardInterrupt :
			return

		visited = download_recursive_mod(packet['name'], ver=None)
		if opt == 1:
			print()
			install_set(visited)

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
			cli.print("[bold red]\nIMPORTANT:[/bold red] You'll overwrite the previous path")
			while True:
				cli.print("Continue? [bold green]Y[/bold green]/[bold red]n[/bold red]: ", end="")
				c = input().lower()
				if c == "" or c == "y" :
					break
				if c == "n" :
					return

		cli.print("Setting a factorio path will able you to [bold red]automatic[/bold red] install mods after download, " + \
			  "insert here the [bold red]ABSOLUTE[/bold red] path for the Factorio Game Folder\n")

		setFactorioPath()

	elif opt == 5:
		if checkCredentialsSet() :
			cli.print("[bold red]\nIMPORTANT:[/bold red] You'll overwrite the previous credentials")
			while True:
				cli.print("Continue? [bold green]Y[/bold green]/[bold red]n[/bold red]: ", end="")
				c = input().lower()
				if c == "" or c == "y" :
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

		help()
		while True :
			start()
except KeyboardInterrupt:
	sys.exit(1)
except Exception as exc:
	cli.print(f"\nAn error has occurred while executing the script [bold red]{exc}[/bold red]")
	print("Dumping traceback below\n")

	traceback.print_tb(exc.__traceback__)
	print('  ' + repr(exc))

	input("\nPress enter to terminate\n")
	sys.exit(1)
