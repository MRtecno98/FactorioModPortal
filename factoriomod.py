import requests, json, os, sys, shutil, traceback, hashlib, platform, difflib, time, re
from concurrent.futures import ThreadPoolExecutor
from packaging import version
from pathlib import Path
from rich.console import Console
from rich.table import Table

MAX_RELEASES_DISPLAYED = 6
MAX_WORDS_PER_LINE = 7

USER_AGENT = "python-factoriomod"

FALLBACK_MIRRORS = [
    # ["https://factorio-launcher-mods.storage.googleapis.com", 0], # Dead
    # Kindly mirrored by @radioegor146
    ["https://official-factorio-mirror.re146.dev/", 0],
    ["https://mods-storage.re146.dev/", 0],
]

cli = Console()

title = r"""
  _____          _             _         __  __           _   ____            _        _
 |  ___|_ _  ___| |_ ___  _ __(_) ___   |  \/  | ___   __| | |  _ \ ___  _ __| |_ __ _| |
 | |_ / _` |/ __| __/ _ \| '__| |/ _ \  | |\/| |/ _ \ / _` | | |_) / _ \| '__| __/ _` | |
 |  _| (_| | (__| || (_) | |  | | (_) | | |  | | (_) | (_| | |  __/ (_) | |  | || (_| | |
 |_|  \__,_|\___|\__\___/|_|  |_|\___/  |_|  |_|\___/ \__,_| |_|   \___/|_|   \__\__,_|_|
"""

username = ""
token = ""
paid = False

factorio_path = ""

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

data_cache = None
checksums = None


def get_mod_info(name, detailed=False):
    if not detailed:
        cache = get_data_cache()
        return cache.get(name)

    query = (
        "https://mods.factorio.com/api/mods/"
        + name.replace(" ", "%20")
        + ("/full" if detailed else "")
    )
    request = session.get(query)

    result = json.loads(request.text)
    return result


def build_data_cache(force_rebuild=False):
    global data_cache
    if data_cache is None or force_rebuild:

        def fetch_and_index():
            raw = session.get("https://mods.factorio.com/api/mods?page_size=max").json()
            return {mod["name"]: mod for mod in raw["results"]}

        data_cache = executor.submit(fetch_and_index)


def get_data_cache():
    return data_cache.result()


def is_error_packet(modpacket):
    return modpacket is None or "message" in modpacket.keys()


def similar(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def login():
    global username, token, paid

    cli.print("Insert below your Factorio account data")

    cli.print("[bold green]Insert username: [/bold green]", end="")
    usr = input()
    cli.print(
        "\nYou can get the token by going to [bold blue]https://www.factorio.com/profile[/bold blue]"
    )
    cli.print("[bold green]Insert token: [/bold green]", end="")
    tk = input().strip()

    cli.print("\nPaid accounts can use better mirrors for downloading mods")
    cli.print(
        "[bold green]Is this a [bold yellow]paid[/bold yellow] account? y[/bold green]/[bold green][bold red]N[/bold red]: [/bold green]",
        end="",
    )
    pd = input().lower() == "y"

    username = usr
    token = tk
    paid = pd

    save_userdata()

    cli.print("[bold green]\nCredentials Saved![/bold green]")


def set_factorio_path():
    global factorio_path

    path = ""
    while True:
        cli.print("[bold green]Insert Factorio path: [/bold green]", end="")
        path = input().strip()

        if not check_factorio_path(path):
            cli.print("[bold red]!!! Invalid Factorio path !!![/bold red]")
            continue
        break

    factorio_path = path
    save_userdata()
    cli.print("[bold green]Path changed![/bold green]")


def check_factorio_path(path):
    if not os.path.isdir(path):
        return False
    contents = os.listdir(path)
    return all(item in contents for item in ["mods", "bin", "player-data.json"])


def save_userdata():
    global username, token, factorio_path

    data = {}
    data["username"] = username
    data["token"] = token
    data["path"] = factorio_path
    data["paid"] = paid

    with open("userdata.json", "w") as file:
        file.write(json.dumps(data))


def load_userdata():
    global username, token, factorio_path, paid

    data = {}
    if os.path.isfile("userdata.json"):
        with open("userdata.json") as file:
            data = json.loads(file.read())
        username = data.get("username", "")
        token = data.get("token", "")
        factorio_path = data.get("path", "")
        paid = data.get("paid", paid)

    if not check_factorio_path_set():
        auto_path = "."
        if platform.system() == "Darwin":
            auto_path = os.path.join(
                Path.home(), "Library/Application Support/factorio"
            )
        elif platform.system() == "Linux":
            auto_path = os.path.join(Path.home(), "factorio")
        elif platform.system() == "Windows":
            auto_path = os.path.join(Path.home(), "AppData/Roaming/Factorio")
        if check_factorio_path(auto_path):
            factorio_path = auto_path


def check_credentials_set():
    global username, token
    return username != "" and token != ""


def check_factorio_path_set():
    global factorio_path
    return factorio_path != ""


def split_word_lines(text, words_per_line=MAX_WORDS_PER_LINE):
    words = text.split(" ")
    splitted = list()

    c = 0
    temp = list()
    for word in words:
        if c == words_per_line:
            splitted.append(" ".join(temp))
            temp = list()
            c = 0
        temp.append(word)
        c += 1

    splitted.append(" ".join(temp))

    return splitted


def display_mod_info(packet, max_releases=MAX_RELEASES_DISPLAYED):
    cli.print(
        f"[bold green]Name:[/bold green] [bold white]{packet['title']}[/bold white]"
    )
    cli.print(
        f"[bold green]Owner:[/bold green] [bold white]{packet['owner']}[/bold white]"
    )
    cli.print(
        f"[bold green]Downloads:[/bold green] [bold white]{str(packet['downloads_count'])}[/bold white]"
    )
    cli.print(f"[bold green]ID:[/bold green] [bold white]{packet['name']}[/bold white]")
    cli.print(f"\nDescription: ")
    cli.print(f"\n".join(split_word_lines(packet["summary"])))
    print()

    releases = packet["releases"]
    releases.reverse()
    if max_releases == -1:
        max_releases = len(releases)

    releases_table = Table(title="[bold green]Releases[/bold green]")

    releases_table.add_column("[green]File name[green]")
    releases_table.add_column("[green]Mod Version[green]")
    releases_table.add_column("[green]Game Version[green]")

    tab = " " * 4
    i = 0
    for x in releases:
        if i == max_releases:
            releases_table.add_row("", "", "")
            releases_table.add_row(
                f"[bold red]{str(len(releases) - i)} more...[/bold red]", "", ""
            )
            cli.print(releases_table)
            break

        releases_table.add_row(
            x["file_name"], x["version"], x["info_json"]["factorio_version"]
        )
        i += 1


def check_dirs():
    os.makedirs("mod_cache", exist_ok=True)


def clear_cache():
    if os.path.isdir("mod_cache"):
        shutil.rmtree("mod_cache")
        check_dirs()


def build_download_urls(packet, release, paid=False, username=None, token=None):
    if paid:
        return [
            (
                "http://mods.factorio.com"
                + release["download_url"]
                + "?username="
                + username
                + "&token="
                + token,
                -1,
            )
        ]
    else:
        return [
            (
                "/".join(
                    (
                        FALLBACK_MIRRORS[i][0],
                        packet["name"],
                        release["version"] + ".zip",
                    )
                ),
                i,
            )
            for i in range(len(FALLBACK_MIRRORS))
        ]


CHECKSUM_FILE = "mod_cache" + os.sep + "checksums.json"


def get_cache_checksums():
    global checksums

    if checksums is None:
        if os.path.isfile(CHECKSUM_FILE):
            with open(CHECKSUM_FILE) as f:
                checksums = json.loads(f.read())
        else:
            checksums = dict()

    return checksums


def save_cache_checksums():
    global checksums

    if checksums is not None:
        with open(CHECKSUM_FILE, "w") as f:
            f.write(json.dumps(checksums, indent=4))


def batch_update_checksums(new_entries):
    global checksums
    get_cache_checksums()
    checksums.update(new_entries)
    save_cache_checksums()


def get_file_hash(file):
    if file not in list(get_cache_checksums().keys()):
        checksums[file] = hash_stream(file)
        save_cache_checksums()
    return checksums[file]


def search(query, max_similar=5):
    cache = get_data_cache()
    matches = [(mod, similar(query, mod["name"].lower())) for mod in cache.values()]
    matches.sort(key=lambda p: p[1], reverse=True)

    return matches[:max_similar]


def hash_stream(file_path):
    """Returns the SHA-1 hash of the file using a larger buffer."""
    h = hashlib.sha1()
    with open(file_path, "rb") as file:
        while chunk := file.read(65536):
            h.update(chunk)
    return h.hexdigest()


def download_mod(packet, ver, filter=None):
    global username, token, paid

    try:
        release = next(r for r in packet["releases"] if r["version"] == ver)
    except StopIteration:
        cli.print(f"[bold red]!!! Version {ver} not found for mod !!![/bold red]")
        return None

    if release is None:
        return None

    urls = build_download_urls(packet, release, paid, username, token)
    output_path = "mod_cache" + os.sep + release["file_name"]

    if os.path.isfile(output_path):
        if release["sha1"] == get_file_hash(output_path):
            cli.print("[bold yellow]Using cached version[/bold yellow]")
            return release

    for i in range(len(urls)):
        url, mirror = urls[i]
        try:
            request = session.get(url, stream=True)
            request.raise_for_status()

            h = hashlib.sha1()
            with open(output_path, "wb") as file:
                for chunk in request.iter_content(65536):
                    file.write(chunk)
                    h.update(chunk)

            file_hash = h.hexdigest()
            batch_update_checksums({output_path: file_hash})
            break
        except (requests.RequestException, IOError) as e:
            cli.print(f"[dim]Mirror {mirror} failed: {e}[/dim]")
            if mirror != -1:
                FALLBACK_MIRRORS[mirror][1] += 1
            if i < len(urls) - 1:
                continue
            else:
                cli.print(f"[bold red]!!! All mirrors failed !!![/bold red]")
                raise

    if i != 0:
        FALLBACK_MIRRORS.sort(key=lambda mirror: mirror[1])

    cli.print("[bold green]Success[/bold green]")
    return release


def parse_dep_code(code):
    res = {"required": True, "conflict": False}

    code = code.strip()

    for i in range(len(code)):
        if code[i].isalnum():
            if i > 0 and code[i - 1] != " ":
                code = code[:i] + " " + code[i:]
            break

    if not code[0].isalnum():
        code = code.split(" ", 1)
        part = code[0].strip("(").strip(")")

        res["conflict"] = part == "!"
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

        res["filter"] = (
            (lambda v: v > ver)
            if sign == ">"
            else (lambda v: v >= ver)
            if sign == ">="
            else (lambda v: v < ver)
            if sign == "<"
            else (lambda v: v <= ver)
            if sign == "<="
            else None
        )

    return res


def download_recursive_mod(
    mod_name, ver="latest", filter=lambda v: True, visited_set=None, min_delay=0.03
):
    visited_set = visited_set if visited_set else dict()
    stamp = time.time()

    if mod_name in visited_set.keys():
        return visited_set
    visited_set[mod_name] = None

    mod_info = get_mod_info(mod_name, detailed=ver != "latest")

    if "message" in mod_info.keys():
        cli.print(
            f"Could not download [bold red]{mod_name}[/bold red]: error: [bold red]{mod_info['message']}[/bold red]"
        )
        return

    releases = [
        release
        for release in mod_info["releases"]
        if (not filter) or filter(version.parse(release["version"]))
    ]

    if not ver:
        # Inform the user about available releases
        # when going interactive mode
        display_mod_info(mod_info)
        print()

        while True:
            check = False
            cli.print(
                "[bold green]Select release to download(default: latest): [/bold green]",
                end="",
            )
            ver = input().strip()
            print()

            if ver == "":
                ver = releases[-1]["version"]

            for rl in releases:
                if rl["version"] == ver:
                    check = True
            if check:
                break
            cli.print("[bold red]!!! Version not released !!![/bold red]")
    elif ver == "latest":
        if not releases:
            cli.print(
                f"[bold red]!!! No compatible releases found for {mod_name} !!![/bold red]"
            )
            return visited_set
        ver = max(releases, key=lambda r: version.parse(r["version"]))["version"]

    print(f"Downloading {mod_name}... ", end="", flush=True)
    target = download_mod(mod_info, ver=ver)
    visited_set[mod_name] = target["file_name"]

    if min_delay - (time.time() - stamp) > 0:
        time.sleep(min_delay - (time.time() - stamp))

    if "dependencies" in target["info_json"]:
        for dep_code in target["info_json"]["dependencies"]:
            dep = parse_dep_code(dep_code)

            if dep["required"] and dep["name"] != "base":
                visited_set.update(
                    download_recursive_mod(
                        dep["name"],
                        filter=dep.get("filter", None),
                        visited_set=visited_set,
                        min_delay=min_delay,
                    )
                )

    return visited_set


def install_mod(filename):
    global factorio_path

    source = "mod_cache" + os.sep + filename
    target = factorio_path + os.sep + "mods" + os.sep + filename
    os.makedirs(os.path.dirname(target), exist_ok=True)

    cli.print(f"[green]Installing {filename}... [/green]", end="")
    sys.stdout.flush()

    if os.path.isfile(target) and hash_stream(source) == hash_stream(target):
        cli.print("[bright_black]Already installed[/bright_black]")
        return

    shutil.copy(source, target)

    cli.print("[bold green]Done[/bold green]")


def install_set(visited_set):
    for path in [val for val in visited_set.values() if val is not None]:
        install_mod(path)


def extract_mod_name_from_url(input_str):
    """Extract mod name from Factorio mod portal URL."""
    if not input_str.startswith("http"):
        return input_str

    patterns = [
        r"mods\.factorio\.com/mod/([^/?]+)",
        r"mods\.factorio\.com/api/mods/([^/?]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, input_str)
        if match:
            return match.group(1)

    return input_str


def ask_mod_name():
    matches = None
    while True:
        cli.print("[bold green]Insert mod name or URL: [/bold green]", end="")
        name = input()

        name = extract_mod_name_from_url(name)

        if matches is not None:
            if name == "":
                name = "0"
            try:
                return matches[int(name)][0]
            except (ValueError, IndexError):
                pass

        packet = get_mod_info(name)
        if is_error_packet(packet):
            matches = search(name)
            if not matches:
                cli.print("[bold red]!!! Not found !!! [/bold red]")
                continue

            longest = max(len(match[0]["name"]) for match in matches)

            cli.print("\nDidn't found exact match, maybe you meant one of these?")
            for i in range(len(matches)):
                match, confid = matches[i]
                cli.print(
                    f"[bold yellow][{i}] [/bold yellow]{match['name']}"
                    f"[bold yellow] {chr(9) * ((longest - len(match['name'])) // 4 + 1)}"
                    f"({int(confid * 100)}% exact)[/bold yellow]"
                )
            print()

            cli.print(
                "[bold red]!!! Not found, try again or select an index above !!! [/bold red]"
            )
            continue
        return packet


def help():
    print("\n")
    cli.print("[bold yellow]1)[/bold yellow] Install mod from mod portal")
    cli.print("[bold yellow]2)[/bold yellow] Download mod from mod portal")
    cli.print("[bold yellow]3)[/bold yellow] Import mod_list file")
    cli.print("[bold yellow]4)[/bold yellow] View mod info")
    cli.print("[bold yellow]5)[/bold yellow] Select Factorio installation")
    cli.print("[bold yellow]6)[/bold yellow] Set user data")
    cli.print("[bold yellow]7)[/bold yellow] Clear cache")
    cli.print("[bold yellow]0)[/bold yellow] Exit")
    cli.print("\n[bold yellow]Enter nothing to print this help again[/bold yellow]")


def start():
    global username, token, factorio_path

    opt = 0
    while True:
        try:
            cli.print("\n[bold green]-> [/bold green]", end="")
            opt = int(input())
            break
        except KeyboardInterrupt:
            sys.exit(0)
        except ValueError:
            help()
            continue

    if opt == 0:
        sys.exit(0)

    if opt in (1, 2):
        if not check_credentials_set():
            cli.print(
                "[bold red]!!! You need to set the credentials in order to download a mod !!![/bold red]"
            )
            return

        if opt == 1:
            if not check_factorio_path_set():
                cli.print(
                    "[bold red]!!! You need to set the factorio path in order to install a mod !!![/bold red]"
                )
                return

        try:
            packet = ask_mod_name()
            print()
        except KeyboardInterrupt:
            return

        visited = download_recursive_mod(packet["name"], ver=None)
        if opt == 1:
            print()
            install_set(visited)

    elif opt == 3:
        cli.print(
            "\n[bold green]Insert file path(default [/bold green]mod-list.json[bold green]): [/bold green]",
            end="",
        )
        path = input()
        if path == "":
            path = "mod-list.json"
        if not os.path.isfile(path):
            cli.print(f"[bold red]!!! Could not find file {path} !!![/bold red]")
            return

        print()

        try:
            with open(path) as f:
                mod_list = json.loads(f.read())
        except json.JSONDecodeError as e:
            cli.print(f"[bold red]!!! Invalid JSON in {path}: {e} !!![/bold red]")
            return

        if "mods" not in mod_list:
            cli.print(
                f"[bold red]!!! Invalid mod-list format: missing 'mods' key !!![/bold red]"
            )
            return

        to_install = dict()
        for mod in [mod["name"] for mod in mod_list["mods"] if mod["name"] != "base"]:
            to_install.update(download_recursive_mod(mod, visited_set=to_install))

        print()

        if check_factorio_path_set():
            install_set(to_install)
            shutil.copy(path, os.path.join(factorio_path, "mods", "mod-list.json"))
        else:
            cli.print(
                "[green]Skipping installation because factorio path is not set[/green]"
            )

    elif opt == 4:
        try:
            packet = ask_mod_name()

            while True:
                try:
                    rels = input(
                        f"Releases to print(-1 for all, default {MAX_RELEASES_DISPLAYED}): "
                    )
                    rels = -1 if rels == "" else int(rels)
                    break
                except ValueError:
                    continue

            print()
        except KeyboardInterrupt:
            return

        display_mod_info(packet, max_releases=rels)

    elif opt == 5:
        if check_factorio_path_set():
            cli.print(
                "[bold red]\nIMPORTANT:[/bold red] You'll overwrite the previous path"
            )
            while True:
                cli.print(
                    "Continue? [bold green]Y[/bold green]/[bold red]n[/bold red]: ",
                    end="",
                )
                c = input().lower()
                if c == "" or c == "y":
                    break
                if c == "n":
                    return

        cli.print(
            "Setting a factorio path will able you to [bold red]automatic[/bold red] install mods after download, "
            + "insert here the [bold red]ABSOLUTE[/bold red] path for the Factorio Game Folder\n"
        )

        set_factorio_path()

    elif opt == 6:
        if check_credentials_set():
            cli.print(
                "[bold red]\nIMPORTANT:[/bold red] You'll overwrite the previous credentials"
            )
            while True:
                cli.print(
                    "Continue? [bold green]Y[/bold green]/[bold red]n[/bold red]: ",
                    end="",
                )
                c = input().lower()
                if c == "" or c == "y":
                    break
                if c == "n":
                    return

        login()

    elif opt == 7:
        print("Clearing mod cache...")
        clear_cache()
        print("Done")


try:
    if __name__ == "__main__":
        with ThreadPoolExecutor(max_workers=5) as executor:
            print(title)
            check_dirs()
            load_userdata()
            build_data_cache()

            help()
            while True:
                start()
except KeyboardInterrupt:
    sys.exit(1)
except Exception as exc:
    cli.print(
        f"\nAn error has occurred while executing the script [bold red]{exc}[/bold red]"
    )
    print("Dumping traceback below\n")

    traceback.print_tb(exc.__traceback__)
    print("  " + repr(exc))

    input("\nPress enter to terminate\n")
    sys.exit(1)
