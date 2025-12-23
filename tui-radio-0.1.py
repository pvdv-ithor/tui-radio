#!/usr/bin/env python3
import curses
import subprocess
import threading
import queue
import time

STATIONS = [
    ("Aardschok (Pinguin Radio)", "https://streams.pinguinradio.com/Aardschok192.mp3"),
    ("Bob Radio Metal", "https://streams.radiobob.de/bob-metal/mp3-192/streams.radiobob.de/play.m3u"),
    ("Classic21 Metal (RTBF)", "http://radio.rtbf.be/c21-metal/mp3-128/radio.rtbf.be/play.pls"),
    ("Kink Distortion", "https://www.mp3streams.nl/zender/kink-distortion/stream/99-aac-128"),
    ("Studio Brussel Bruut ", "https://vrt.streamabc.net/vrt-studiobrusselbruut-mp3-128-7838034"),
]

mpv_process = None
output_queue = queue.Queue()


def stop_mpv():
    global mpv_process
    if mpv_process and mpv_process.poll() is None:
        mpv_process.terminate()
        mpv_process.wait()
    mpv_process = None


def run_mpv(url):
    global mpv_process
    cmd = [
        "mpv",
        "--quiet",
        "--term-status-msg=",
        "--msg-level=icy=info",
        url,
    ]

    mpv_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    for line in mpv_process.stdout:
        line = line.strip()
        if line.startswith("icy-title:"):
            title = line.split("icy-title:", 1)[1].strip()
            if title:
                output_queue.put(title)

    mpv_process = None


def draw_menu(menu_win, selected):
    menu_win.clear()
    menu_win.box()
    menu_win.addstr(0, 2, " Stations ", curses.A_BOLD)
    for i, (name, _) in enumerate(STATIONS):
        attr = curses.A_REVERSE if i == selected else curses.A_NORMAL
        menu_win.addstr(2 + i, 2, name[:menu_win.getmaxyx()[1] - 4], attr)
    menu_win.refresh()


def draw_playback(play_win, station_name, titles):
    play_win.clear()
    play_win.box()
    play_win.addstr(0, 2, " Now Playing ", curses.A_BOLD)
    play_win.addstr(1, 2, station_name, curses.A_BOLD)
    play_win.addstr(2, 2, "-" * (play_win.getmaxyx()[1] - 4))

    max_lines = play_win.getmaxyx()[0] - 5
    visible_titles = titles[-max_lines:]
    for idx, title in enumerate(visible_titles):
        prefix = "▶ " if idx == len(visible_titles) - 1 else "  "
        play_win.addstr(3 + idx, 2, f"{prefix}{title[:play_win.getmaxyx()[1]-4]}")

    play_win.addstr(play_win.getmaxyx()[0]-2, 2, "q = back to menu")
    play_win.refresh()

def playback_screen(stdscr, station_name, url):
    stop_mpv()
    output_queue.queue.clear()
    threading.Thread(target=run_mpv, args=(url,), daemon=True).start()

    stdscr.nodelay(True)
    curses.curs_set(0)

    titles = []

    menu_width = 30
    play_win = None

    def recreate_windows():
        nonlocal play_win
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        # Prevent tiny terminals from crashing curses
        if w < menu_width + 10 or h < 6:
            return None, None, None

        play_width = w - menu_width - 1
        play_win = stdscr.subwin(h, play_width, 0, menu_width + 1)
        play_win.nodelay(True)

        # Draw static UI
        play_win.clear()
        play_win.box()
        play_win.addstr(0, 2, " Now Playing ", curses.A_BOLD)
        play_win.addstr(1, 2, station_name, curses.A_BOLD)
        play_win.addstr(2, 2, "-" * (play_width - 4))
        play_win.addstr(h - 2, 2, "q = back to menu")
        play_win.refresh()

        return h, w, play_width

    h, w, play_width = recreate_windows()
    if play_win is None:
        return

    while True:
        # Read new ICY titles
        while not output_queue.empty():
            titles.append(output_queue.get())

        # Redraw titles (newest at top)
        max_lines = h - 5
        visible = titles[-max_lines:]

        for i in range(min(max_lines, len(visible))):
            y = 3 + i
            if y >= h - 2:
                break

            title = visible[-1 - i]
            prefix = "▶ " if i == 0 else "  "
            line = f"{prefix}{title}"

            play_win.addstr(y, 2, " " * max(0, play_width - 4))
            play_win.addstr(y, 2, line[: max(0, play_width - 4)])

        play_win.refresh()

        try:
            key = play_win.getch()
            if key == ord("q"):
                stop_mpv()
                return
            elif key == curses.KEY_RESIZE:
                h, w, play_width = recreate_windows()
                if play_win is None:
                    return
        except curses.error:
            pass

        time.sleep(0.1)

def main(stdscr):
    curses.curs_set(0)
    stdscr.clear()
    stdscr.refresh()
    stdscr.keypad(True)

    h, w = stdscr.getmaxyx()
    menu_width = 30
    selected = 0

    menu_win = stdscr.subwin(h, menu_width, 0, 0)
    menu_win.keypad(True)

    while True:
        draw_menu(menu_win, selected)
        key = menu_win.getch()

        if key == curses.KEY_UP:
            selected = (selected - 1) % len(STATIONS)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(STATIONS)
        elif key in (10, 13):
            name, url = STATIONS[selected]
            playback_screen(stdscr, name, url)
        elif key == ord("q"):
            stop_mpv()
            break


if __name__ == "__main__":
    curses.wrapper(main)
