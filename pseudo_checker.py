import random
import string
import time
import os
import sys
import threading
import requests

RESET  = "\033[0m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
GRAY   = "\033[90m"
BOLD   = "\033[1m"
HIDE   = "\033[?25l"
SHOW   = "\033[?25h"

PALETTE = [
    ( 15,  8,  5),( 60, 30, 18),(120, 75, 45),(190,140,100),(225,195,155),
    (205,140, 90),(185, 75, 42),(155, 30, 18),( 85, 12,  8),
]

def lerp(c1, c2, t):
    return (int(c1[0]+(c2[0]-c1[0])*t),int(c1[1]+(c2[1]-c1[1])*t),int(c1[2]+(c2[2]-c1[2])*t))

def wave(pos, off):
    w = (pos + off) % 1.0
    f = w * len(PALETTE)
    i = int(f) % len(PALETTE)
    j = (i+1) % len(PALETTE)
    r,g,b = lerp(PALETTE[i], PALETTE[j], f-int(f))
    return max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b))

def rgb(r,g,b,t):
    return f"\033[38;2;{r};{g};{b}m{t}{RESET}"

BANNER = [
    " _    ___   ___ _____ _      _   _  _ ___  ___ ",
    "| |  / _ \\ / _ \\_   _| |    /_\\ | \\| |   \\/ __|",
    "| |_| (_) | (_) || | | |__ / _ \\| .` | |) \\__ \\",
    "|____\\___/ \\___/ |_| |____/_/ \\_\\_|\\_|___/|___/",
]

def draw_banner(off):
    out = []
    for line in BANNER:
        s = " "
        n = len(line)
        for i, ch in enumerate(line):
            r,g,b = wave(i/max(n-1,1), off)
            s += f"\033[38;2;{r};{g};{b}m{ch}"
        out.append(s + RESET)
    r2,g2,b2 = wave(0.4, off)
    out.append("")
    out.append(f" \033[38;2;{r2};{g2};{b2}m{BOLD}Username Checker{RESET}  {GRAY}lootlands.gg/lootlands{RESET}")
    out.append(f" {GRAY}{'─'*48}{RESET}")
    return out

BANNER_H = len(BANNER) + 3
_anim_stop = threading.Event()

def anim_loop():
    off = 0.0
    while not _anim_stop.is_set():
        lines = draw_banner(off)
        sys.stdout.write("\0337")
        sys.stdout.write("\033[1;1H")
        for l in lines:
            sys.stdout.write("\033[2K" + l + "\n")
        sys.stdout.write("\0338")
        sys.stdout.flush()
        off = (off + 0.02) % 1.0
        time.sleep(0.08)

def build_charset(l, d, dot, un):
    c = ""
    if l:   c += string.ascii_lowercase
    if d:   c += string.digits
    if dot: c += "."
    if un:  c += "_"
    return c or (string.ascii_lowercase + string.digits)

def randname(n, c):
    return "".join(random.choice(c) for _ in range(n))

def get_proxy(proxies):
    if not proxies: return None
    p = random.choice(proxies).strip()
    parts = p.split(":")
    if len(parts) == 2:
        return {"http": f"http://{p}", "https": f"http://{p}"}
    if len(parts) == 4:
        ip, port, u, pw = parts
        url = f"http://{u}:{pw}@{ip}:{port}"
        return {"http": url, "https": url}
    return None

stats      = {"total":0, "avail":0, "taken":0, "err":0}
stats_lock = threading.Lock()
print_lock = threading.Lock()
stop_flag  = threading.Event()
rate_lock  = threading.Lock()
next_slot  = [0.0]

def rate_limiter(delay):
    with rate_lock:
        now = time.time()
        if next_slot[0] < now:
            next_slot[0] = now
        wait = next_slot[0] - now
        next_slot[0] += delay
    if wait > 0:
        time.sleep(wait)

def build_headers(token):
    h = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9163 Chrome/120.0.6099.291 Electron/28.2.10 Safari/537.36",
        "Origin": "https://discord.com",
        "Referer": "https://discord.com/channels/@me",
        "X-Discord-Locale": "fr",
        "X-Debug-Options": "bugReporterEnabled",
    }
    if token:
        h["Authorization"] = token
    return h

def test_token(token):
    """Teste le token directement sur l'endpoint de check."""
    try:
        r = requests.post(
            "https://discord.com/api/v9/unique-username/batch-validate",
            json={"usernames": ["zzztest999"]},
            headers=build_headers(token),
            timeout=10
        )
        if r.status_code == 200:
            return True, "OK"
        if r.status_code == 401:
            return False, "401 token rejete"
        if r.status_code == 403:
            return False, "403 acces refuse"
        if r.status_code == 429:
            return True, "OK (rate limit, mais token accepte)"
        return None, f"HTTP {r.status_code} (on tente quand meme)"
    except Exception as e:
        return None, str(e)[:40]

def check(name, session, token, proxies):
    try:
        r = session.post(
            "https://discord.com/api/v9/unique-username/batch-validate",
            json={"usernames": [name]},
            headers=build_headers(token),
            proxies=get_proxy(proxies),
            timeout=10
        )
        if r.status_code == 429:
            w = float(r.headers.get("Retry-After", 5))
            with print_lock:
                print(f" {YELLOW}Rate limit {w}s{RESET}", flush=True)
            time.sleep(w)
            return "rl"
        if r.status_code == 401:
            with print_lock:
                print(f" {RED}Token invalide.{RESET}")
            stop_flag.set()
            return "dead"
        if r.status_code == 200:
            taken = r.json().get("taken_usernames", [])
            return "taken" if name in taken else "available"
        return f"e{r.status_code}"
    except requests.Timeout:
        return "timeout"
    except Exception:
        return "error"

def worker(token, proxies, length, chars, delay, seen, seen_lock, start):
    session = requests.Session()
    max_possible = len(chars) ** length
    while not stop_flag.is_set():
        with seen_lock:
            if len(seen) >= max_possible:
                with print_lock:
                    print(f" {YELLOW}Toutes les combinaisons ont ete testees.{RESET}")
                stop_flag.set()
                return
            for _ in range(50):
                name = randname(length, chars)
                if name not in seen:
                    seen.add(name)
                    break
            else:
                continue
        rate_limiter(delay)
        if stop_flag.is_set():
            return
        status = check(name, session, token, proxies)
        if status == "dead":
            continue
        if status == "rl":
            # Retenter le meme pseudo apres le rate limit
            while not stop_flag.is_set():
                rate_limiter(delay)
                status = check(name, session, token, proxies)
                if status != "rl":
                    break
            if status == "dead" or stop_flag.is_set():
                continue
        with stats_lock:
            stats["total"] += 1
            if status == "available": stats["avail"] += 1
            elif status == "taken":   stats["taken"] += 1
            else:                     stats["err"]   += 1
            n = stats["total"]
        if status == "available":
            tag = f"{GREEN}{BOLD}AVAILABLE{RESET}"
            with print_lock:
                with open("available.txt", "a") as f:
                    f.write(name + "\n")
        elif status == "taken":
            tag = f"{RED}taken    {RESET}"
        else:
            tag = f"{YELLOW}{status:<9}{RESET}"
        el  = max(time.time() - start, 0.01)
        spd = n / el
        r2,g2,b2 = wave((n % 40)/40, 0)
        with print_lock:
            print(f" \033[38;2;{r2};{g2};{b2}m[{n}]{RESET} {BOLD}{name:<11}{RESET} {tag} {GRAY}{spd:.1f}/s{RESET}")

def clean_input(s):
    """Enleve les caracteres de controle (Ctrl+X etc)."""
    return "".join(ch for ch in s if ch.isprintable()).strip()

def ask(prompt, default=None, cast=str):
    while True:
        try:
            raw = input(f" {rgb(225,195,155,'>')} {prompt} ")
        except (KeyboardInterrupt, EOFError):
            print(); sys.exit(0)
        v = clean_input(raw)
        if v == "":
            if default is not None:
                return default
            return cast("") if cast is str else default
        try:
            return cast(v)
        except (ValueError, TypeError):
            if default is not None:
                print(f" {YELLOW}Entree invalide, valeur par defaut: {default}{RESET}")
                return default
            print(f" {YELLOW}Entree invalide, reessaie.{RESET}")

def yn(prompt, default=True):
    v = ask(f"{prompt} {'[Y/n]' if default else '[y/N]'}").lower()
    return default if v == "" else v in ("y","o","oui","yes")

def load_proxies():
    if not os.path.exists("proxies.txt"):
        return []
    with open("proxies.txt") as f:
        return [l.strip() for l in f if l.strip()]

def main():
    os.system("clear")
    sys.stdout.write(HIDE)

    for l in draw_banner(0.0):
        print(l)
    print()

    sys.stdout.write(f"\033[{BANNER_H+2};r")
    sys.stdout.write(f"\033[{BANNER_H+2};1H")
    sys.stdout.flush()

    threading.Thread(target=anim_loop, daemon=True).start()

    print(f" {BOLD}CONFIG{RESET}\n")

    token = clean_input(ask("Token Discord (Entree=skip):")) or None
    if token:
        print(f" {GRAY}Test du token...{RESET}")
        ok, info = test_token(token)
        if ok is True:
            print(f" {GREEN}Token accepte — {info}{RESET}\n")
        elif ok is None:
            print(f" {YELLOW}Reponse inattendue : {info}{RESET}")
            print(f" {YELLOW}On garde le token et on lance quand meme.{RESET}\n")
        else:
            print(f" {RED}Token refuse : {info}{RESET}")
            print(f" {YELLOW}On tente quand meme au cas ou.{RESET}\n")
    else:
        print(f" {YELLOW}Sans token — l'API bloque souvent (403/404).{RESET}\n")

    proxies = load_proxies()
    print(f" {GREEN}{len(proxies)} proxies{RESET}\n" if proxies else f" {GRAY}IP directe{RESET}\n")

    length  = ask("Longueur [4]:", 4, int)
    speed   = ask("Vitesse /s [2]:", 2.0, float)
    threads = ask("Threads [5]:", 5, int)
    delay   = 1.0 / max(speed, 0.1)

    print()
    chars = build_charset(
        yn("Lettres a-z?", True),
        yn("Chiffres 0-9?", True),
        yn("Points . ?", False),
        yn("Underscores _ ?", False),
    )

    print(f"\n {GRAY}{len(chars)} chars — {threads} threads — {speed}/s{RESET}\n")
    input(f" {rgb(225,195,155,'Entree pour lancer...')}")

    print(f"\n{GRAY} N°   PSEUDO      STATUT      SPEED{RESET}")
    print(f"{GRAY} {'─'*42}{RESET}\n")

    seen, seen_lock = set(), threading.Lock()
    start = time.time()

    for _ in range(max(1, threads)):
        threading.Thread(
            target=worker,
            args=(token, proxies, length, chars, delay, seen, seen_lock, start),
            daemon=True
        ).start()

    try:
        while not stop_flag.is_set():
            time.sleep(0.3)
    except KeyboardInterrupt:
        stop_flag.set()

    el = max(time.time() - start, 0.01)
    print(f"\n{GRAY} {'─'*42}{RESET}")
    print(f" Total {stats['total']}  {GREEN}Dispo {stats['avail']}{RESET}  {RED}Pris {stats['taken']}{RESET}  {YELLOW}Err {stats['err']}{RESET}")
    print(f" Vitesse reelle : {BOLD}{stats['total']/el:.2f}/s{RESET}\n")

def cleanup():
    _anim_stop.set()
    time.sleep(0.15)
    sys.stdout.write("\033[r")
    sys.stdout.write(SHOW)
    sys.stdout.flush()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        stop_flag.set()
        print(f"\n {YELLOW}Arrete.{RESET}")
    finally:
        cleanup()
        print(f" {GRAY}lootlands.gg/lootlands{RESET}\n")
